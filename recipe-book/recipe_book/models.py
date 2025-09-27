from __future__ import annotations

from datetime import datetime
from typing import Optional

import numpy as np

from .extensions import db


class Recipe(db.Model):
    __tablename__ = "recipes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(300), nullable=True)
    source = db.Column(db.String(120), nullable=False)
    filters = db.Column(db.String(160), nullable=False, default="")
    rating = db.Column(db.Integer, nullable=True)
    ingredients = db.Column(db.Text, nullable=True)
    steps = db.Column(db.Text, nullable=True)
    embedding = db.Column(db.LargeBinary, nullable=True)
    embedding_dim = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def tags(self) -> list[str]:
        if not self.filters:
            return []
        return [tag.strip() for tag in self.filters.split(",") if tag.strip()]

    def embedding_vector(self) -> Optional[np.ndarray]:
        if not self.embedding or not self.embedding_dim:
            return None
        return np.frombuffer(self.embedding, dtype=np.float32)
    
    def similarity_to(self, query_vector: np.ndarray) -> float:
        """Calculate cosine similarity between this recipe's embedding and a query vector."""
        recipe_vector = self.embedding_vector()
        if recipe_vector is None:
            return 0.0
        
        # Normalize vectors
        recipe_norm = np.linalg.norm(recipe_vector)
        query_norm = np.linalg.norm(query_vector)
        
        if recipe_norm == 0 or query_norm == 0:
            return 0.0
        
        # Calculate cosine similarity
        return float(np.dot(recipe_vector, query_vector) / (recipe_norm * query_norm))

