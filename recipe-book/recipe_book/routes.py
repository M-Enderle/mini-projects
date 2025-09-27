from __future__ import annotations

import os
import re
import uuid
from typing import Optional
from werkzeug.utils import secure_filename

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import func, or_

from .extensions import db
from .gemini import generate_recipe_from_image, generate_recipe_from_text, generate_recipe_from_url
from .models import Recipe
from .services import fetch_sources
from .utils import empty_recipe, ingest_form, parse_json_to_recipe, render_with, save_recipe, validate_recipe


bp = Blueprint("main", __name__)


def handle_image_upload(image_file) -> Optional[str]:
    """Handle image upload and return the relative URL path."""
    if not image_file or not image_file.filename:
        return None
    
    # Check file extension
    filename = secure_filename(image_file.filename)
    if not filename:
        return None
    
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if file_ext not in allowed_extensions:
        flash("Nur PNG, JPG, JPEG, GIF und WebP Dateien sind erlaubt.")
        return None
    
    # Check file size (5MB limit)
    image_file.seek(0, os.SEEK_END)
    file_size = image_file.tell()
    image_file.seek(0)
    if file_size > 5 * 1024 * 1024:  # 5MB
        flash("Bilddatei ist zu groß. Maximum 5MB erlaubt.")
        return None
    
    # Create unique filename
    unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
    
    # Ensure upload directory exists
    upload_dir = os.path.join(current_app.static_folder, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, unique_filename)
    image_file.save(file_path)
    
    # Return relative URL path
    return f"/static/uploads/{unique_filename}"


def prefixed_url_for(endpoint: str, **values) -> str:
    # Map old endpoint names to new blueprint names
    endpoint_mapping = {
        'home': 'main.home',
        'recipe_create': 'main.recipe_create',
        'recipe_detail': 'main.recipe_detail',
        'recipe_edit': 'main.recipe_edit',
        'recipe_delete': 'main.recipe_delete',
    }
    
    # Use mapped endpoint if available
    mapped_endpoint = endpoint_mapping.get(endpoint, endpoint)
    
    try:
        original = url_for(mapped_endpoint, **values)
    except:
        # Fallback to original endpoint if mapping fails
        original = url_for(endpoint, **values)
    
    base = current_app.config.get("BASE_PATH", "")
    if not base:
        return original
    if original.startswith(base + "/") or original == base:
        return original
    if original == "/":
        return base + "/"
    if original.startswith("/"):
        return base + original
    return original


@bp.app_context_processor
def inject_helpers():
    return {
        "url_for": prefixed_url_for,
        "base_path": current_app.config.get("BASE_PATH", ""),
        "sources": fetch_sources(),
    }


@bp.route("/", methods=["GET", "POST"])
def home():
    form_data = request.form if request.method == "POST" else request.args
    query = form_data.get("q", "").strip()
    source_filter = form_data.get("source", "").strip()
    rating_filter = form_data.get("stars", "").strip()

    try:
        min_rating = float(rating_filter) if rating_filter else None
    except ValueError:
        min_rating = None

    base_query = Recipe.query
    if source_filter:
        base_query = base_query.filter(Recipe.source == source_filter)
    if min_rating is not None:
        base_query = base_query.filter(func.coalesce(Recipe.rating, 0) >= min_rating)

    if query:
        terms = [part for part in re.split(r"\s+", query) if part]
        search_fields = (
            Recipe.title,
            Recipe.description,
            Recipe.filters,
            Recipe.ingredients,
        )
        for term in terms:
            like = f"%{term}%"
            base_query = base_query.filter(or_(*[field.ilike(like) for field in search_fields]))
        base_query = base_query.order_by(
            func.coalesce(Recipe.rating, 0).desc(),
            Recipe.created_at.desc(),
        )
    else:
        base_query = base_query.order_by(
            func.coalesce(Recipe.rating, 0).desc(),
            Recipe.created_at.desc(),
        )

    recipes = base_query.all()

    return render_template(
        "home.html",
        recipes=recipes,
        query=query,
        selected_source=source_filter,
        selected_stars=rating_filter,
        show_edit_link=False,
    )


@bp.route("/recipes/<string:slug>")
def recipe_detail(slug: str):
    recipe = Recipe.query.filter_by(slug=slug).first()
    if not recipe:
        abort(404)

    return render_template("recipe_detail.html", recipe=recipe, related=[], show_edit_link=recipe)


def handle_gemini_generation(recipe: Recipe, action: str) -> Optional[Recipe]:
    if action == "generate_image":
        generated, error = generate_recipe_from_image(request.files.get("gemini_image"))
    elif action == "generate_text":
        generated, error = generate_recipe_from_text(request.form.get("gemini_text", ""))
    elif action == "generate_url":
        generated, error = generate_recipe_from_url(request.form.get("gemini_url", ""))
    else:
        return None

    if error:
        flash(error)
        return recipe

    flash("Rezept aus KI erzeugt! Bitte prüfen und anschließend speichern.")
    return generated


@bp.route("/recipes/new", methods=["GET", "POST"])
def recipe_create():
    recipe = empty_recipe()

    if request.method == "POST":
        action = request.form.get("action", "")
        if action in {"generate_image", "generate_text", "generate_url"}:
            generated = handle_gemini_generation(recipe, action)
            return render_template("recipe_form.html", recipe=generated or recipe, is_new=True)

        if "json_file" in request.files and request.files["json_file"].filename:
            imported, error = parse_json_to_recipe(request.files["json_file"])
            if error:
                flash(error)
                return render_template("recipe_form.html", recipe=recipe, is_new=True)
            flash("JSON erfolgreich importiert! Bitte überprüfen Sie die Felder vor dem Speichern.")
            return render_template("recipe_form.html", recipe=imported, is_new=True)

        # Handle image upload
        uploaded_image_url = None
        if "image_upload" in request.files:
            uploaded_image_url = handle_image_upload(request.files["image_upload"])
        
        ingest_form(recipe, request.form, uploaded_image_url)
        errors = validate_recipe(recipe)
        if errors:
            for message in errors:
                flash(message)
        else:
            save_recipe(recipe)
            flash("Rezept angelegt.")
            return redirect(prefixed_url_for("recipe_detail", slug=recipe.slug))

    return render_template("recipe_form.html", recipe=recipe, is_new=True)


@bp.route("/recipes/<string:slug>/edit", methods=["GET", "POST"])
def recipe_edit(slug: str):
    recipe = Recipe.query.filter_by(slug=slug).first()
    if not recipe:
        abort(404)

    if request.method == "POST":
        # Handle image upload
        uploaded_image_url = None
        if "image_upload" in request.files:
            uploaded_image_url = handle_image_upload(request.files["image_upload"])
        
        ingest_form(recipe, request.form, uploaded_image_url)
        errors = validate_recipe(recipe)
        if errors:
            for message in errors:
                flash(message)
        else:
            save_recipe(recipe)
            flash("Rezept aktualisiert.")
            return redirect(prefixed_url_for("recipe_detail", slug=recipe.slug))

    return render_template("recipe_form.html", recipe=recipe, is_new=False)


@bp.route("/recipes/<string:slug>/delete", methods=["POST"])
def recipe_delete(slug: str):
    recipe = Recipe.query.filter_by(slug=slug).first()
    if not recipe:
        abort(404)

    db.session.delete(recipe)
    db.session.commit()
    flash("Rezept gelöscht.")
    return redirect(prefixed_url_for("home"))

