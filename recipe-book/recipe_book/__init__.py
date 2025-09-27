from __future__ import annotations

import logging

from dotenv import load_dotenv
from flask import Flask

from .config import base_path, gemini_model, log_level, secret_key, sqlalchemy_uri
from .extensions import db
from .routes import bp as main_bp
from .services import init_db


load_dotenv()


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder="../static",
        static_url_path=f"{base_path()}/static",
        template_folder="../templates",
    )
    app.config.update(
        SQLALCHEMY_DATABASE_URI=sqlalchemy_uri(),
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
    ]

    for endpoint, source_endpoint, rule_suffix, methods in routes:
        view = app.view_functions.get(source_endpoint)
        if view is None:
            continue
        rule = f"{prefix}{rule_suffix}"
        app.add_url_rule(rule, endpoint=endpoint, view_func=view, methods=methods)
 
