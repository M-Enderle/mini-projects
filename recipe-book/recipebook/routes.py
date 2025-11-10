from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any, Optional
from werkzeug.utils import secure_filename

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from recipebook.extensions import db
from recipebook.embedding import embed_query, embed_recipe
from recipebook.gemini import (
    generate_recipe_from_image,
    generate_recipe_from_text,
    generate_recipe_from_url,
    generate_recipe_via_prompt,
)
from recipebook.models import Recipe
from recipebook.services import fetch_sources
from recipebook.utils import (
    build_recipe_from_payload,
    empty_recipe,
    ingest_form,
    payload_to_recipe,
    recipe_to_payload,
    save_recipe,
    update_recipe_from_payload,
    validate_recipe,
)


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
    
    # Return a URL to the uploaded file using Flask's url_for so it respects
    # the app's configured static URL path (including any BASE_PATH prefix).
    return url_for('static', filename=f"uploads/{unique_filename}")


def prefixed_url_for(endpoint: str, **values) -> str:
    # Map old endpoint names to new blueprint names
    endpoint_mapping = {
        'home': 'main.home',
        'recipe_create': 'main.recipe_create',
        'recipe_detail': 'main.recipe_detail',
        'recipe_edit': 'main.recipe_edit',
        'recipe_delete': 'main.recipe_delete',
        'regenerate_embeddings': 'main.regenerate_embeddings',
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


def _deserialize_recipe_payload(raw: Optional[str]) -> Optional[dict[str, Any]]:
    if raw is None:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    try:
        data = json.loads(trimmed)
    except json.JSONDecodeError:
        flash("Rezeptdaten konnten nicht gelesen werden. Bitte erneut generieren.")
        return None
    if data is None:
        return None
    if not isinstance(data, dict):
        flash("Rezeptdaten haben ein unerwartetes Format. Bitte erneut generieren.")
        return None
    return data


def _preview_warnings_from_payload(payload: Optional[dict[str, Any]]) -> list[str]:
    if not payload:
        return []
    recipe_candidate = payload_to_recipe(payload)
    warnings = validate_recipe(recipe_candidate)
    return [message for message in warnings if message != "Bild-URL angeben."]


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

    recipes = Recipe.query.all()
    
    # If there's a search query, use semantic search with embeddings
    if query:
        query_vector = embed_query(query)
        if query_vector is not None:
            # Calculate similarity scores for all recipes
            recipe_scores = []
            for recipe in recipes:
                similarity = recipe.similarity_to(query_vector)
                if similarity > 0.1:  # Only include recipes with some similarity
                    recipe_scores.append((recipe, similarity))
            
            # Sort by similarity score (descending)
            recipe_scores.sort(key=lambda x: x[1], reverse=True)
            recipes = [recipe for recipe, _ in recipe_scores]
        else:
            # Fallback to text search if embedding fails
            terms = [part for part in re.split(r"\s+", query) if part]
            search_fields = (
                Recipe.title,
                Recipe.description,
                Recipe.filters,
                Recipe.ingredients,
            )
            filtered_recipes = []
            for recipe in recipes:
                match = False
                for term in terms:
                    for field in [recipe.title, recipe.description, recipe.filters, recipe.ingredients or ""]:
                        if field and term.lower() in field.lower():
                            match = True
                            break
                    if match:
                        break
                if match:
                    filtered_recipes.append(recipe)
            recipes = filtered_recipes
            
            # Sort by date for fallback search
            recipes.sort(key=lambda r: (r.created_at or 0), reverse=True)
    else:
        # No query - sort by creation date
        recipes.sort(key=lambda r: (r.created_at or 0), reverse=True)

    return render_template(
        "home.html",
        recipes=recipes,
        query=query,
        show_edit_link=False,
    )


@bp.route("/recipes/<string:slug>")
def recipe_detail(slug: str):
    recipe = Recipe.query.filter_by(slug=slug).first()
    if not recipe:
        abort(404)

    return render_template("recipe_detail.html", recipe=recipe, related=[], show_edit_link=recipe)


def handle_gemini_generation(recipe: Optional[Recipe], action: str) -> Optional[Recipe]:
    base_recipe = recipe or empty_recipe()

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
        return base_recipe

    flash("Rezept aus KI erzeugt! Vorschau aktualisiert.")
    return generated or base_recipe


@bp.route("/recipes/new", methods=["GET", "POST"])
def recipe_create():
    payload: Optional[dict[str, Any]] = None
    prompt_text = ""
    manual_image_url = ""

    if request.method == "POST":
        action = request.form.get("action", "").strip()
        prompt_text = request.form.get("prompt_text", "").strip()
        manual_image_url = request.form.get("image_url", "").strip()
        payload = _deserialize_recipe_payload(request.form.get("recipe_payload"))

        if action in {"generate_image", "generate_text", "generate_url"}:
            current_recipe = payload_to_recipe(payload) if payload else None
            generated = handle_gemini_generation(current_recipe, action)
            if generated:
                payload = recipe_to_payload(generated)
                if not manual_image_url:
                    manual_image_url = payload.get("image_url", "") or ""
        elif action == "prompt_generate":
            base_payload = payload if payload else None
            generated, error = generate_recipe_via_prompt(prompt_text, base_payload)
            if error:
                flash(error)
            elif generated:
                payload = recipe_to_payload(generated)
                flash("Prompt angewendet. Vorschau aktualisiert.")
                if not manual_image_url:
                    manual_image_url = payload.get("image_url", "") or ""
        elif action == "reset":
            payload = None
            manual_image_url = ""
            prompt_text = ""
        elif action == "save":
            if not payload:
                flash("Bitte zuerst ein Rezept über den Prompt erzeugen.")
            else:
                recipe = build_recipe_from_payload(payload)
                uploaded_image_url = handle_image_upload(request.files.get("image_upload"))
                if uploaded_image_url:
                    recipe.image_url = uploaded_image_url
                    manual_image_url = uploaded_image_url
                elif manual_image_url:
                    recipe.image_url = manual_image_url
                else:
                    recipe.image_url = payload.get("image_url") or None

                # Apply form fields (portions, total_time)
                ingest_form(recipe, request.form, uploaded_image_url=uploaded_image_url)

                errors = validate_recipe(recipe)
                if errors:
                    for message in errors:
                        flash(message)
                else:
                    embed_recipe(recipe)
                    save_recipe(recipe)
                    flash("Rezept angelegt.")
                    return redirect(prefixed_url_for("recipe_detail", slug=recipe.slug))
        else:
            if action:
                flash("Unbekannte Aktion.")
    else:
        payload = None

    if payload and not manual_image_url:
        manual_image_url = payload.get("image_url", "") or ""
    # Do not expose internal/static file paths in the editable URL input.
    # Only show external URLs (http/https) in the image_url input field.
    if manual_image_url and (manual_image_url.startswith("http://") or manual_image_url.startswith("https://")):
        manual_image_url_input = manual_image_url
    else:
        manual_image_url_input = ""
    preview_warnings = _preview_warnings_from_payload(payload)
    display_image_url = manual_image_url or (payload.get("image_url") if payload else "")

    return render_template(
        "recipe_form.html",
        recipe=None,
        is_new=True,
        recipe_payload=payload,
        prompt_text=prompt_text,
        manual_image_url=manual_image_url,
        manual_image_url_input=manual_image_url_input,
        preview_warnings=preview_warnings,
        display_image_url=display_image_url,
        can_save=bool(payload),
    )


@bp.route("/recipes/<string:slug>/edit", methods=["GET", "POST"])
def recipe_edit(slug: str):
    recipe = Recipe.query.filter_by(slug=slug).first()
    if not recipe:
        abort(404)

    payload: dict[str, Any] = recipe_to_payload(recipe)
    manual_image_url = recipe.image_url or ""
    prompt_text = ""

    if request.method == "POST":
        action = request.form.get("action", "").strip()
        prompt_text = request.form.get("prompt_text", "").strip()
        manual_image_url = request.form.get("image_url", "").strip() or manual_image_url
        payload = _deserialize_recipe_payload(request.form.get("recipe_payload")) or payload

        if action in {"generate_image", "generate_text", "generate_url"}:
            current_recipe = payload_to_recipe(payload) if payload else recipe
            generated = handle_gemini_generation(current_recipe, action)
            if generated:
                payload = recipe_to_payload(generated)
                if not manual_image_url:
                    manual_image_url = payload.get("image_url", "") or manual_image_url
        elif action == "prompt_generate":
            base_payload = payload or recipe_to_payload(recipe)
            generated, error = generate_recipe_via_prompt(prompt_text, base_payload)
            if error:
                flash(error)
            elif generated:
                payload = recipe_to_payload(generated)
                flash("Prompt angewendet. Vorschau aktualisiert.")
                if not manual_image_url:
                    manual_image_url = payload.get("image_url", "") or manual_image_url
        elif action == "reset":
            payload = recipe_to_payload(recipe)
            manual_image_url = recipe.image_url or ""
            prompt_text = ""
        elif action == "save":
            if not payload:
                flash("Keine Änderungen zum Speichern vorhanden.")
            else:
                update_recipe_from_payload(recipe, payload)
                uploaded_image_url = handle_image_upload(request.files.get("image_upload"))
                if uploaded_image_url:
                    recipe.image_url = uploaded_image_url
                    manual_image_url = uploaded_image_url
                elif manual_image_url:
                    recipe.image_url = manual_image_url
                else:
                    recipe.image_url = payload.get("image_url") or None

                # Apply form fields (portions, total_time)
                ingest_form(recipe, request.form, uploaded_image_url=uploaded_image_url)

                errors = validate_recipe(recipe)
                if errors:
                    for message in errors:
                        flash(message)
                else:
                    embed_recipe(recipe)
                    save_recipe(recipe)
                    flash("Rezept aktualisiert.")
                    return redirect(prefixed_url_for("recipe_detail", slug=recipe.slug))
        else:
            if action:
                flash("Unbekannte Aktion.")

    preview_warnings = _preview_warnings_from_payload(payload)
    display_image_url = manual_image_url or (payload.get("image_url") if payload else recipe.image_url or "")

    # Do not expose internal/static file paths in the editable URL input.
    # Only show external URLs (http/https) in the image_url input field.
    if manual_image_url and (manual_image_url.startswith("http://") or manual_image_url.startswith("https://")):
        manual_image_url_input = manual_image_url
    else:
        manual_image_url_input = ""

    return render_template(
        "recipe_form.html",
        recipe=recipe,
        is_new=False,
        recipe_payload=payload,
        prompt_text=prompt_text,
        manual_image_url=manual_image_url,
        manual_image_url_input=manual_image_url_input,
        preview_warnings=preview_warnings,
        display_image_url=display_image_url,
        can_save=bool(payload),
    )


@bp.route("/recipes/<string:slug>/delete", methods=["POST"])
def recipe_delete(slug: str):
    recipe = Recipe.query.filter_by(slug=slug).first()
    if not recipe:
        abort(404)

    db.session.delete(recipe)
    db.session.commit()
    flash("Rezept gelöscht.")
    return redirect(prefixed_url_for("home"))


@bp.route("/admin/regenerate-embeddings", methods=["POST"])
def regenerate_embeddings():
    """Regenerate embeddings for all recipes."""
    try:
        recipes = Recipe.query.all()
        count = 0
        for recipe in recipes:
            embed_recipe(recipe)
            count += 1
        
        db.session.commit()
        flash(f"Embeddings für {count} Rezepte regeneriert.")
    except Exception as e:
        flash(f"Fehler beim Regenerieren der Embeddings: {str(e)}")
    
    return redirect(prefixed_url_for("home"))

