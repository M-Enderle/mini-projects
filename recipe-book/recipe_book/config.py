from __future__ import annotations

import os


def base_path() -> str:
    return os.getenv("RECIPE_BOOK_BASE_PATH", "/recipe-book")


def db_filename() -> str:
    return os.getenv("RECIPE_BOOK_DB", "recipe_book.db")


def secret_key() -> str:
    return os.getenv("RECIPE_BOOK_SECRET", "change-me")


def sqlalchemy_uri() -> str:
    return f"sqlite:///{db_filename()}"


def gemini_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY")


def gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash")


def log_level() -> str:
    return os.getenv("LOG_LEVEL", "INFO").upper()

