from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from flask import Flask

from recipebook.config import base_path, db_filename, gemini_model, log_level, secret_key
from recipebook.extensions import db
from recipebook.routes import bp as main_bp
from recipebook.services import init_db


load_dotenv()


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder="../static",
        static_url_path=f"{base_path()}/static",
        template_folder="../templates",
    )
    # Maximum request size (bytes). Useful to protect from very large uploads.
    # Default to 10 MiB but can be overridden with the MAX_CONTENT_LENGTH env var.
    max_content = int(os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))
    app.config.setdefault("MAX_CONTENT_LENGTH", max_content)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, db_filename())}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=secret_key(),
        BASE_PATH=base_path(),
        GEMINI_MODEL=gemini_model(),
    )

    if not app.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s"))
        app.logger.addHandler(handler)

    app.logger.setLevel(getattr(logging, log_level(), logging.INFO))
    app.logger.propagate = False

    db.init_app(app)
    app.register_blueprint(main_bp)

    # Register template filters
    @app.template_filter("json_loads")
    def json_loads_filter(value):
        if not value:
            return []
        try:
            import json
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return []

    _register_prefixed_routes(app)

    with app.app_context():
        init_db()

    return app


def _register_prefixed_routes(app: Flask) -> None:
    prefix = base_path().rstrip("/")
    if not prefix:
        return

    routes = [
        ("home_prefixed", "main.home", "/", ["GET", "POST"]),
        ("recipe_create_prefixed", "main.recipe_create", "/recipes/new", ["GET", "POST"]),
        ("recipe_edit_prefixed", "main.recipe_edit", "/recipes/<string:slug>/edit", ["GET", "POST"]),
        ("recipe_delete_prefixed", "main.recipe_delete", "/recipes/<string:slug>/delete", ["POST"]),
        ("recipe_detail_prefixed", "main.recipe_detail", "/recipes/<string:slug>", ["GET"]),
        ("regenerate_embeddings_prefixed", "main.regenerate_embeddings", "/admin/regenerate-embeddings", ["POST"]),
    ]

    for endpoint, source_endpoint, rule_suffix, methods in routes:
        view = app.view_functions.get(source_endpoint)
        if view is None:
            continue
        rule = f"{prefix}{rule_suffix}"
        app.add_url_rule(rule, endpoint=endpoint, view_func=view, methods=methods)
 
