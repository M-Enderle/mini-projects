from __future__ import annotations

import json
import logging
import mimetypes
from typing import Optional, Tuple

from flask import current_app
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

from .config import gemini_api_key, gemini_model
from .utils import recipe_from_data

logger = logging.getLogger(__name__)
_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = gemini_api_key()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY ist nicht gesetzt.")
        _client = genai.Client(api_key=api_key)
    return _client


def normalise_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text[3:]
        if text.startswith("json"):
            text = text[4:]
        text = text.lstrip()
        fence = text.rfind("```")
        if fence != -1:
            text = text[:fence]
    return text.strip()


def call_gemini(parts: list[types.Part | str]) -> str:
    client = get_client()
    response = client.models.generate_content(model=gemini_model(), contents=parts)
    logger.debug(
        "Gemini Anfrage: model=%s, parts=%s, response_candidates=%s",
        gemini_model(),
        parts,
        getattr(response, "candidates", None),
    )
    text = (response.text or "").strip()
    if text:
        return text
    collected: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        if content:
            for part in getattr(content, "parts", []) or []:
                piece = getattr(part, "text", None)
                if piece:
                    collected.append(piece)
    if collected:
        return "\n".join(fragment.strip() for fragment in collected if fragment)
    raise RuntimeError("Gemini lieferte keine Textausgabe.")


def extract_recipe_from_json(raw: str) -> dict:
    cleaned = normalise_json(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("Gemini-Ausgabe konnte nicht geparst werden: %s", cleaned)
        raise RuntimeError("Gemini-Antwort konnte nicht als JSON geparst werden.") from exc


def validate_image(file_storage) -> Tuple[bytes, str]:
    if not file_storage or not file_storage.filename:
        raise RuntimeError("Bitte Bilddatei auswählen.")
    mime_type, _ = mimetypes.guess_type(file_storage.filename)
    if not mime_type or not mime_type.startswith("image/"):
        raise RuntimeError("Nur Bilddateien sind erlaubt.")
    return file_storage.read(), mime_type


def fetch_url_content(url: str) -> str:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Set user agent and reasonable timeout
            page.set_extra_http_headers({"User-Agent": "Recipe-Book/1.0"})
            
            # Navigate to the page and wait for it to load
            page.goto(url, timeout=30000)  # 30 second timeout
            page.wait_for_load_state('networkidle', timeout=10000)  # Wait for network to be idle
            
            # Get the page content
            content = page.content()
            browser.close()
            
            return content
    except Exception as exc:
        raise RuntimeError(f"Fehler beim Laden der URL: {exc}") from exc


def generate_recipe_from_image(image_file):
    try:
        image_data, mime_type = validate_image(image_file)
        image_part = types.Part(
            inline_data=types.Blob(data=image_data, mime_type=mime_type)
        )
        prompt = """Analysiere dieses Bild und erstelle ein Rezept dafür. Antworte ausschließlich mit gültigem JSON im folgenden Format:

{
  "title": "Name des Gerichts",
  "description": "Kurze appetitliche Beschreibung (1-2 Sätze)",
  "source": "Gemini AI",
  "filters": "passende Tags durch Kommata getrennt (z.B. vegetarisch, dessert, schnell)",
  "rating": null,
  "ingredients": [
    "# Für die Soße",
    "200ml Sahne",
    "1 EL Senf",
    "# Für das Hauptgericht",
    "500g Fleisch",
    "2 Zwiebeln"
  ],
  "steps": [
    "Schritt 1 der Zubereitung",
    "Schritt 2 der Zubereitung"
  ]
}

Verwende deutsche Sprache und realistische Mengenangaben. Du kannst Zutaten in Abschnitte unterteilen, indem du Zeilen mit # beginnst (z.B. "# Für die Soße", "# Für den Teig")."""
        response = call_gemini([prompt, image_part])
        current_app.logger.debug("Gemini Bild-Antwort: %s", response)
        data = extract_recipe_from_json(response)
        return recipe_from_data(data), None
    except Exception as exc:  # pragma: no cover - defensive
        current_app.logger.exception("Fehler bei der Gemini Bildanalyse")
        return None, f"Fehler bei der Bildanalyse: {exc}"


def generate_recipe_from_text(text: str):
    if not text.strip():
        return None, "Bitte Textbeschreibung eingeben."
    try:
        prompt = f"""Erstelle ein Rezept basierend auf dieser Beschreibung: "{text}"

Antworte ausschließlich mit gültigem JSON im folgenden Format:

{{
  "title": "Name des Gerichts",
  "description": "Kurze appetitliche Beschreibung (1-2 Sätze)",
  "source": "Gemini AI",
  "filters": "passende Tags durch Kommata getrennt (z.B. vegetarisch, dessert, schnell)",
  "rating": null,
  "ingredients": [
    "# Für die Soße",
    "200ml Sahne",
    "1 EL Senf",
    "# Für das Hauptgericht",
    "500g Fleisch",
    "2 Zwiebeln"
  ],
  "steps": [
    "Schritt 1 der Zubereitung",
    "Schritt 2 der Zubereitung"
  ]
}}

Verwende deutsche Sprache und realistische Mengenangaben. Du kannst Zutaten in Abschnitte unterteilen, indem du Zeilen mit # beginnst (z.B. "# Für die Soße", "# Für den Teig")."""
        response = call_gemini([prompt])
        current_app.logger.debug("Gemini Text-Antwort: %s", response)
        data = extract_recipe_from_json(response)
        return recipe_from_data(data), None
    except Exception as exc:  # pragma: no cover - defensive
        current_app.logger.exception("Fehler bei der Gemini Textanalyse")
        return None, f"Fehler bei der Textanalyse: {exc}"


def generate_recipe_from_url(url: str):
    if not url.strip():
        return None, "Bitte URL eingeben."
    try:
        html_content = fetch_url_content(url)
        print(html_content)
        print("--------------------------------")
        print(len(html_content))
        print("--------------------------------")
        prompt = f"""Analysiere diesen HTML-Inhalt und extrahiere ein Rezept daraus:

        {html_content}

Antworte ausschließlich mit gültigem JSON im folgenden Format:

{{
  "title": "Name des Gerichts",
  "description": "Kurze appetitliche Beschreibung (1-2 Sätze)",
  "source": "Quelle des Inhalts",
  "filters": "passende Tags durch Kommata getrennt (z.B. vegetarisch, dessert, schnell)",
  "image_url": "URL zum Bild des Gerichts",
  "rating": null,
  "ingredients": [
    "# Für die Soße",
    "200ml Sahne",
    "1 EL Senf",
    "# Für das Hauptgericht",
    "500g Fleisch",
    "2 Zwiebeln"
  ],
  "steps": [
    "Schritt 1 der Zubereitung",
    "Schritt 2 der Zubereitung"
  ]
}}

Verwende deutsche Sprache und realistische Mengenangaben. Du kannst Zutaten in Abschnitte unterteilen, indem du Zeilen mit # beginnst (z.B. "# Für die Soße", "# Für den Teig"). Ignoriere Werbung und irrelevante Inhalte."""
        response = call_gemini([prompt])
        current_app.logger.debug("Gemini URL-Antwort: %s", response)
        data = extract_recipe_from_json(response)
        return recipe_from_data(data), None
    except Exception as exc:  # pragma: no cover - defensive
        current_app.logger.exception("Fehler bei der Gemini URL-Analyse")
        return None, f"Fehler bei der URL-Analyse: {exc}"

