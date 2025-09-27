from __future__ import annotations

from recipe_book import create_app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)

