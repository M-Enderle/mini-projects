from __future__ import annotations

from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from .models import Recipe

_embedding_model: Optional[SentenceTransformer] = None


def get_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _embedding_model


def embed_recipe(recipe: Recipe) -> None:
    text = " \n".join(
        filter(
            None,
            [
                recipe.title,
                recipe.description,
                recipe.source,
                ", ".join(recipe.tags),
            ],
        )
    )
    vector = get_model().encode(text, convert_to_numpy=True, normalize_embeddings=True)
    recipe.embedding = vector.astype(np.float32).tobytes()
    recipe.embedding_dim = vector.shape[0]

