from __future__ import annotations

import json
import os
from typing import Optional

from flask import current_app, has_app_context
from sqlalchemy import inspect, text

from .embedding import embed_recipe
from .extensions import db
from .models import Recipe
from .utils import generate_unique_slug, normalize_filters, normalise_rating, parse_list_field, parse_steps


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
    if "rating" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN rating INTEGER"))
    if "ingredients" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN ingredients TEXT"))
    if "steps" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN steps TEXT"))
    missing = Recipe.query.filter((Recipe.slug.is_(None)) | (Recipe.slug == "")).all()
    if missing:
        used = {recipe.slug for recipe in Recipe.query.filter(Recipe.slug.is_not(None)).all() if recipe.slug}
        for recipe in missing:
            recipe.slug = generate_unique_slug(recipe.title, used, ignore_id=recipe.id)
            used.add(recipe.slug)
        db.session.commit()


def init_db() -> None:
    if not has_app_context():
        raise RuntimeError("init_db must be called within an application context")

    db_path = current_app.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///recipe_book.db")
    filename = db_path.replace("sqlite:///", "")
    if filename and not os.path.exists(filename):
        open(filename, "a").close()

    db.create_all()
    ensure_slug_column()
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
            "rating": 5,
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
            "rating": 4,
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
            rating=item.get("rating"),
            ingredients=item.get("ingredients"),
            steps=item.get("steps"),
        )
        embed_recipe(recipe)
        db.session.add(recipe)
    db.session.commit()

