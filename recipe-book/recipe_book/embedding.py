from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from google import genai

from .config import gemini_api_key
from .models import Recipe

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


def embed_recipe(recipe: Recipe) -> None:
    """Generate embedding for recipe using Gemini embeddings API."""
    try:
        # Combine recipe text fields for embedding
        text_parts = []
        if recipe.title:
            text_parts.append(f"Titel: {recipe.title}")
        if recipe.description:
            text_parts.append(f"Beschreibung: {recipe.description}")
        if recipe.source:
            text_parts.append(f"Quelle: {recipe.source}")
        if recipe.tags:
            text_parts.append(f"Tags: {', '.join(recipe.tags)}")
        
        text = " | ".join(text_parts)
        
        if not text.strip():
            logger.warning("Kein Text für Embedding gefunden für Rezept: %s", recipe.title)
            recipe.embedding = None
            recipe.embedding_dim = None
            return
        
        client = get_client()
        result = client.models.embed_content(
            model="models/text-embedding-004",
            content=text
        )
        
        if result.embedding and result.embedding.values:
            vector = np.array(result.embedding.values, dtype=np.float32)
            recipe.embedding = vector.tobytes()
            recipe.embedding_dim = len(vector)
            logger.debug("Embedding erstellt für Rezept '%s' mit Dimension %d", recipe.title, len(vector))
        else:
            logger.warning("Kein Embedding erhalten für Rezept: %s", recipe.title)
            recipe.embedding = None
            recipe.embedding_dim = None
            
    except Exception as exc:
        logger.exception("Fehler beim Erstellen des Embeddings für Rezept '%s'", recipe.title)
        recipe.embedding = None
        recipe.embedding_dim = None


def embed_query(query: str) -> Optional[np.ndarray]:
    """Generate embedding for search query using Gemini embeddings API."""
    try:
        if not query.strip():
            return None
            
        client = get_client()
        result = client.models.embed_content(
            model="models/text-embedding-004",
            content=query
        )
        
        if result.embedding and result.embedding.values:
            return np.array(result.embedding.values, dtype=np.float32)
        else:
            logger.warning("Kein Embedding für Query erhalten: %s", query)
            return None
            
    except Exception as exc:
        logger.exception("Fehler beim Erstellen des Query-Embeddings: %s", query)
        return None

