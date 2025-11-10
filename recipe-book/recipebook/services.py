from __future__ import annotations

import json
import os

from flask import current_app, has_app_context
from sqlalchemy import inspect, text

from recipebook.embedding import embed_recipe
from recipebook.extensions import db
from recipebook.models import Recipe
from recipebook.utils import generate_unique_slug, normalize_filters, parse_list_field, parse_steps


def fetch_sources() -> list[str]:
    rows = db.session.query(Recipe.source).distinct().order_by(Recipe.source).all()
    return [row[0] for row in rows]


def ensure_slug_column() -> None:
    engine = db.engine
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("recipes")}
    
    if "slug" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN slug VARCHAR(200)"))
    if "ingredients" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN ingredients TEXT"))
    if "steps" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN steps TEXT"))
    
    # Only query after all columns are guaranteed to exist
    try:
        missing = Recipe.query.filter((Recipe.slug.is_(None)) | (Recipe.slug == "")).all()
        if missing:
            used = {recipe.slug for recipe in Recipe.query.filter(Recipe.slug.is_not(None)).all() if recipe.slug}
            for recipe in missing:
                recipe.slug = generate_unique_slug(recipe.title, used, ignore_id=recipe.id)
                used.add(recipe.slug)
            db.session.commit()
    except Exception as e:
        current_app.logger.warning(f"⚠️  Could not update missing slugs: {e}")


def ensure_portions_column() -> None:
    """Add portions column if it doesn't exist and set default values."""
    engine = db.engine
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("recipes")}
    
    if "portions" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN portions INTEGER DEFAULT 4"))
        
        current_app.logger.info("✅ Added 'portions' column to recipes table with default value 4")


def ensure_total_time_column() -> None:
    """Add total_time column if it doesn't exist."""
    engine = db.engine
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("recipes")}
    
    if "total_time" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN total_time INTEGER DEFAULT 0"))
        
        current_app.logger.info("✅ Added 'total_time' column to recipes table with default value 0")


def set_default_portions() -> None:
    """Set default portions value for existing records without portions."""
    try:
        recipes = Recipe.query.all()
        updated = 0
        for recipe in recipes:
            if recipe.portions is None:
                recipe.portions = 4
                updated += 1
        if updated > 0:
            db.session.commit()
            current_app.logger.info(f"✅ Set default portions for {updated} recipes")
    except Exception as e:
        current_app.logger.warning(f"⚠️  Could not set default portions: {e}")


def init_db() -> None:
    if not has_app_context():
        raise RuntimeError("init_db must be called within an application context")

    db_path = current_app.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///recipe_book.db")
    filename = db_path.replace("sqlite:///", "")
    if filename and not os.path.exists(filename):
        open(filename, "a").close()

    db.create_all()
    
    # Run migrations in order - CRITICAL: do these BEFORE any Recipe.query calls!
    ensure_portions_column()
    ensure_total_time_column()
    ensure_slug_column()
    
    # Now we can safely set defaults
    set_default_portions()
    
    if Recipe.query.count():
        return

    recipes = [
        {
            "title": "Geraschte Tomaten-Bucatini",
            "description": (
                "Langsam geröstete Kirschtomaten mit Knoblauchconfit,"
                " unter Bucatini gehoben und mit Basilikumöl sowie Zitronenzeste vollendet."
            ),
            "image_url": "https://images.unsplash.com/photo-1525755662778-989d0524087e?auto=format&fit=crop&w=800&q=80",
            "source": "Hausgemacht",
            "filters": "vegetarisch, sommer, pasta",
            "ingredients": json.dumps([
                "400 g Bucatini",
                "500 g Kirschtomaten",
                "4 EL Knoblauchconfit",
                "Basilikumöl, Zitronenzeste",
            ]),
            "steps": json.dumps([
                {"text": "Tomaten mit Confit im Ofen rösten, bis sie karamellisieren."},
                {"text": "Bucatini garen und mit Tomaten sowie Basilikumöl vermengen."},
                {"text": "Mit Zitronenzeste und frischem Basilikum anrichten."},
            ]),
        },
        {
            "title": "Orangenblüten-Panna-Cotta",
            "description": (
                "Luftige Vanille-Panna-Cotta mit Orangenblüte,"
                " serviert zu gerösteten Aprikosen und Pistazienkrokant."
            ),
            "image_url": "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?auto=format&fit=crop&w=800&q=80",
            "source": "Wochenend-Projekte",
            "filters": "dessert, gekühlt, vorbereiten",
            "ingredients": json.dumps([
                "400 ml Sahne",
                "2 TL Orangenblütenwasser",
                "3 Blatt Gelatine",
                "6 Aprikosen, 40 g Pistazien",
            ]),
            "steps": json.dumps([
                {"text": "Gelatine einweichen, Sahne mit Zucker und Vanille erhitzen."},
                {"text": "Gelatine einrühren, Orangenblüte zugeben und kalt stellen."},
                {"text": "Aprikosen rösten und mit gehackten Pistazien servieren."},
            ]),
        },
    ]

    used_slugs: set[str] = set()
    for item in recipes:
        slug = generate_unique_slug(item["title"], used_slugs)
        recipe = Recipe(
            title=item["title"],
            slug=slug,
            description=item["description"],
            image_url=item["image_url"],
            source=item["source"],
            filters=item["filters"],
            ingredients=item.get("ingredients"),
            steps=item.get("steps"),
        )
        embed_recipe(recipe)
        db.session.add(recipe)
    db.session.commit()

