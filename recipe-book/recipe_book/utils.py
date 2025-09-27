from __future__ import annotations

import json
import re
from functools import wraps
from typing import Any, Callable, Optional
from unicodedata import normalize

from flask import current_app, render_template

from .embedding import embed_recipe
from .extensions import db
from .models import Recipe


def slugify(value: str) -> str:
    value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value or "recipe"


def generate_unique_slug(title: str, existing: Optional[set[str]] = None, ignore_id: Optional[int] = None) -> str:
    base = slugify(title)
    if existing is not None:
        taken = existing
    else:
        rows = db.session.query(Recipe.slug, Recipe.id).filter(Recipe.slug.is_not(None)).all()
        taken = {slug for slug, recipe_id in rows if slug and recipe_id != ignore_id}
    if base not in taken:
        if existing is not None:
            existing.add(base)
        return base

    index = 2
    while True:
        candidate = f"{base}-{index}"
        if candidate not in taken:
            if existing is not None:
                existing.add(candidate)
            return candidate
        index += 1


def parse_steps(payload: Any) -> list[dict[str, str]]:
    if isinstance(payload, list):
        result: list[dict[str, str]] = []
        for item in payload:
            if isinstance(item, dict) and "text" in item:
                text_value = str(item.get("text", "")).strip()
            else:
                text_value = str(item or "").strip()
            if text_value:
                result.append({"text": text_value})
        return result
    if isinstance(payload, str) and payload.strip():
        try:
            data = json.loads(payload)
            return parse_steps(data)
        except json.JSONDecodeError:
            lines = [line.strip() for line in payload.splitlines() if line.strip()]
            return [{"text": line} for line in lines]
    return []


def parse_list_field(value: str) -> list[str | dict[str, str]]:
    """Parse ingredients list supporting section headers with #"""
    result = []
    for line in value.splitlines():
        line = line.strip()
        if not line:
            continue
        # Check if line is a section header (starts with #)
        if line.startswith('#'):
            header_text = line[1:].strip()
            if header_text:
                result.append({"type": "header", "text": header_text})
        else:
            result.append(line)
    return result


def normalize_filters(raw: str) -> str:
    if not raw:
        return ""
    if isinstance(raw, (list, tuple)):
        parts = {str(part).strip() for part in raw if str(part).strip()}
    else:
        parts = {part.strip() for part in str(raw).split(",") if part.strip()}
    return ", ".join(sorted(parts, key=str.lower))


def normalise_rating(raw: Any) -> Optional[int]:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if 1 <= value <= 5 else None


def parse_json_to_recipe(json_file):
    if not json_file or json_file.filename == '':
        return None, "Bitte JSON-Datei auswählen."

    try:
        raw_json = json_file.read().decode('utf-8')
        payload = json.loads(raw_json)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "Ungültige JSON-Datei."

    if isinstance(payload, list):
        if not payload:
            return None, "Leere JSON-Liste."
        item = payload[0]
    elif isinstance(payload, dict):
        item = payload
    else:
        return None, "JSON muss ein Objekt oder eine Liste sein."

    if not isinstance(item, dict):
        return None, "Ungültiges Rezept-Format."
    recipe = recipe_from_data(item)
    return recipe, None


def recipe_from_data(item: dict[str, Any]) -> Recipe:
    title = str(item.get("title", "")).strip()
    description = str(item.get("description", "")).strip()
    source = str(item.get("source", "")).strip() or "Unbekannt"

    return Recipe(
        title=title,
        slug="",
        description=description,
        image_url=str(item.get("image_url", "")).strip() or None,
        source=source,
        filters=normalize_filters(item.get("filters", "")),
        rating=normalise_rating(item.get("rating")),
        ingredients=json.dumps(
            item.get("ingredients")
            if isinstance(item.get("ingredients"), list)
            else parse_list_field(str(item.get("ingredients", "")))
        ),
        steps=json.dumps(parse_steps(item.get("steps", []))),
    )


def empty_recipe() -> Recipe:
    return Recipe(
        title="",
        slug="",
        description="",
        image_url="",
        source="",
        filters="",
        rating=None,
        ingredients=json.dumps([]),
        steps=json.dumps([]),
    )


def ingest_form(recipe: Recipe, data, uploaded_image_url: Optional[str] = None) -> None:
    original_title = recipe.title
    recipe.title = data.get("title", recipe.title).strip()
    recipe.description = data.get("description", recipe.description).strip()
    # Prioritize uploaded image over URL
    if uploaded_image_url:
        recipe.image_url = uploaded_image_url
    else:
        recipe.image_url = data.get("image_url", recipe.image_url or "").strip() or None
    recipe.source = data.get("source", recipe.source).strip()
    recipe.filters = normalize_filters(data.get("filters", recipe.filters))
    ingredients_raw = data.get("ingredients", "")
    recipe.ingredients = json.dumps(parse_list_field(ingredients_raw))
    steps_raw = data.getlist("steps[]") or []
    recipe.steps = json.dumps(parse_steps(steps_raw))
    recipe.rating = normalise_rating(data.get("rating", ""))
    if recipe.title != original_title:
        recipe.slug = generate_unique_slug(recipe.title, ignore_id=recipe.id)
    embed_recipe(recipe)


def validate_recipe(recipe: Recipe) -> list[str]:
    errors: list[str] = []
    if not recipe.title:
        errors.append("Titel angeben.")
    if not recipe.description:
        errors.append("Beschreibung ergänzen.")
    if not recipe.image_url:
        errors.append("Bild-URL angeben.")
    if recipe.rating is not None and not (1 <= recipe.rating <= 5):
        errors.append("Bewertung zwischen 1 und 5.")
    return errors


def with_recipes(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        from .services import init_db

        init_db()
        return view(*args, **kwargs)

    return wrapped


def save_recipe(recipe: Recipe) -> None:
    db.session.add(recipe)
    db.session.commit()


def render_with(path: str, **context):
    from .services import fetch_sources

    context.setdefault("base_path", current_app.config.get("BASE_PATH", ""))
    context.setdefault("sources", fetch_sources())
    context.setdefault("show_edit_link", False)
    return render_template(path, **context)

