from __future__ import annotations

import os


def base_path() -> str:
    return os.getenv("RECIPE_BOOK_BASE_PATH", "/recipe-book")


def db_filename() -> str:
    return os.getenv("RECIPE_BOOK_DB", "recipe_book.db")


def db_path() -> str:
    """Return full path to database file in data directory."""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, db_filename())


def secret_key() -> str:
    return os.getenv("RECIPE_BOOK_SECRET", "change-me")


def sqlalchemy_uri() -> str:
    return f"sqlite:///{db_path()}"


def gemini_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY")


def gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash")


def log_level() -> str:
    return os.getenv("LOG_LEVEL", "INFO").upper()

