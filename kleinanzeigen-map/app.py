from __future__ import annotations

import csv
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Tuple

from flask import Flask, flash, jsonify, redirect, render_template, request, session as flask_session, url_for
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from sqlalchemy import desc, func
from werkzeug.middleware.proxy_fix import ProxyFix

from kleinanzeigen import FlexibleKleinanzeigenScraper, KleinanzeigenListing, SessionLocal


DEFAULT_BASE_PATH = "/kleinanzeigen-map"
DEFAULT_MAX_PAGES = 50
MAX_PAGES_HARD_LIMIT = 50
MAX_RESULTS = 300


def _normalize_base_path(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    if not value:
        return ""
    if not value.startswith('/'):
        value = f"/{value}"
    return value.rstrip('/')


def _load_plz_coords() -> dict[str, Tuple[float, float]]:
    coords: dict[str, Tuple[float, float]] = {}
    csv_path = Path(__file__).resolve().parent / "plz_geocoord.csv"
    if not csv_path.exists():
        return coords
    with csv_path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row:
                continue
            plz = str(row.get("plz") or "").strip()
            if not plz:
                continue
            try:
                lat = float(row.get("lat", "") or 0)
                lng = float(row.get("lng", "") or 0)
            except (TypeError, ValueError):
                continue
            coords[plz] = (lat, lng)
    return coords


PLZ_COORDS = _load_plz_coords()


@lru_cache(maxsize=128)
def _lookup_plz(plz: str | None) -> Tuple[float | None, float | None]:
    digits = ''.join(ch for ch in (plz or "") if ch.isdigit())
    if not digits:
        return None, None
    lat_lng = PLZ_COORDS.get(digits)
    if lat_lng:
        return lat_lng
    return None, None


@lru_cache(maxsize=64)
def _geocode_location(plz: str | None, ort: str | None) -> Tuple[float | None, float | None]:
    query_parts = [part for part in (plz, ort, "Germany") if part]
    if not query_parts:
        return None, None
    try:
        geocoder = Nominatim(user_agent="kleinanzeigen-map-app", timeout=10)
        location = geocoder.geocode(", ".join(query_parts))
    except (GeocoderServiceError, GeocoderTimedOut):
        return None, None
    if not location:
        return None, None
    return location.latitude, location.longitude


def _enrich_coordinates(listings: Iterable[dict]) -> None:
    for entry in listings:
        lat = entry.get("latitude")
        lon = entry.get("longitude")
        if lat and lon:
            continue
        lat, lon = _lookup_plz(entry.get("plz"))
        if not lat or not lon:
            lat, lon = _geocode_location(entry.get("plz"), entry.get("ort"))
        if lat and lon:
            entry["latitude"] = lat
            entry["longitude"] = lon


def _clean_price_display(value: str | None) -> str | None:
    if not value:
        return None
    first_part = value.split('€')[0].strip()
    if not first_part:
        return value
    cleaned = first_part.replace('VB', '').replace('ab', '').strip()
    if not cleaned:
        return value
    result = f"{cleaned}€"
    if 'VB' in value:
        result += " VB"
    return result
    

def _price_as_int(value: str | None) -> int | None:
    if not value:
        return None
    part = value.split('€')[0]
    part = part.replace('VB', '').replace('ab', '').replace('.', '').replace(',', '').strip()
    digits = ''.join(ch for ch in part if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None
    

def _serialize_listing(listing: KleinanzeigenListing) -> dict:
    return {
        "id": listing.id,
        "keyword": listing.keyword,
        "title": listing.title,
        "price": listing.price,
        "price_display": _clean_price_display(listing.price),
        "price_value": _price_as_int(listing.price),
        "plz": listing.plz,
        "ort": listing.ort,
        "url": listing.url,
        "image_url": listing.image_url,
        "latitude": listing.latitude,
        "longitude": listing.longitude,
        "scraped_at": listing.scraped_at.isoformat() if listing.scraped_at else None,
    }


def create_app() -> Flask:
    base_path = _normalize_base_path(os.environ.get("KLEINANZEIGEN_BASE_PATH", DEFAULT_BASE_PATH))
    max_pages_default = int(os.environ.get("KLEINANZEIGEN_MAX_PAGES", DEFAULT_MAX_PAGES))
    max_pages_default = max(1, min(MAX_PAGES_HARD_LIMIT, max_pages_default))

    static_url_path = f"{base_path}/static" if base_path else "/static"
    app = Flask(__name__, static_folder="static", template_folder="templates", static_url_path=static_url_path)
    app.config["SECRET_KEY"] = os.environ.get("KLEINANZEIGEN_SECRET_KEY", "kleinanzeigen-map-secret")
    app.config["BASE_PATH"] = base_path
    app.config["MAX_PAGES_DEFAULT"] = max_pages_default

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    @app.context_processor
    def inject_base_path() -> dict:
        return {"base_path": base_path or ""}

    @app.teardown_appcontext
    def remove_session(exception: Exception | None = None) -> None:  # noqa: ARG001
        SessionLocal.remove()

    def _fetch_listings(session_db, keyword: str, min_price: int | None) -> List[dict]:
        results = (
            session_db.query(KleinanzeigenListing)
            .filter(KleinanzeigenListing.keyword == keyword)
            .order_by(desc(KleinanzeigenListing.scraped_at))
            .limit(MAX_RESULTS)
            .all()
        )
        data = [_serialize_listing(item) for item in results]
        if min_price is not None:
            data = [item for item in data if item["price_value"] is None or item["price_value"] >= min_price]
        _enrich_coordinates(data)
        return data

    def index() -> str:
        session_db = SessionLocal()
        active_keyword = request.args.get("keyword", "").strip()
        req_min_price = request.args.get("min_price")
        active_min_price: int | None = None
        if req_min_price:
            try:
                active_min_price = max(0, int(req_min_price))
            except ValueError:
                active_min_price = None

        recent_searches = flask_session.get("recent_searches")
        if not isinstance(recent_searches, list):
            recent_searches = []

        if not active_keyword and recent_searches:
            active_keyword = recent_searches[0].get("keyword", "")
            active_min_price = recent_searches[0].get("min_price")

        listings: List[dict] = []
        last_scraped: datetime | None = None
        if active_keyword:
            listings = _fetch_listings(session_db, active_keyword, active_min_price)
            if listings:
                ts = listings[0].get("scraped_at")
                last_scraped = datetime.fromisoformat(ts) if ts else None

        return render_template(
            "index.html",
            active_keyword=active_keyword,
            active_min_price=active_min_price,
            listings=listings,
            recent_searches=recent_searches,
            last_scraped=last_scraped,
            max_pages_default=app.config["MAX_PAGES_DEFAULT"],
        )

    def trigger_scrape() -> str:
        keyword = request.form.get("keyword", "").strip()
        if not keyword:
            flash("Bitte gib einen Suchbegriff ein.", "error")
            return redirect(url_for("index"))

        # Always use the maximum of 50 pages
        max_pages = MAX_PAGES_HARD_LIMIT

        min_price: int | None = None
        req_min_price = request.form.get("min_price")
        if req_min_price:
            try:
                min_price = max(0, int(req_min_price))
            except ValueError:
                min_price = None

        scraper = FlexibleKleinanzeigenScraper(keyword, min_price=min_price)

        try:
            def _log(message: str) -> None:
                app.logger.info("scrape[%s]: %s", keyword, message)

            reached_limit = scraper.scrape_all_pages(max_pages=max_pages, progress_callback=_log)
            if len(scraper.all_listings) > MAX_RESULTS:
                scraper.all_listings = scraper.all_listings[:MAX_RESULTS]
                reached_limit = True
            _enrich_coordinates(scraper.all_listings)
            scraper.save_to_database(_log)
            total = len(scraper.all_listings)
            message = f"{total} Anzeigen gespeichert."
            if reached_limit:
                message += " Es wurden nur die ersten {max_pages} Seiten berücksichtigt."
            flash(message, "success")
        except Exception as exc:  # noqa: BLE001
            app.logger.exception("Scraping fehlgeschlagen")
            flash(f"Fehler beim Scrapen: {exc}", "error")
        finally:
            scraper.close()

        recent_searches = flask_session.get("recent_searches")
        if not isinstance(recent_searches, list):
            recent_searches = []
        new_entry = {"keyword": keyword, "min_price": min_price}
        recent_searches = [entry for entry in recent_searches if not (entry.get("keyword") == keyword and entry.get("min_price") == min_price)]
        recent_searches.insert(0, new_entry)
        flask_session["recent_searches"] = recent_searches[:10]
        flask_session.modified = True

        redirect_kwargs = {"keyword": keyword}
        if min_price is not None:
            redirect_kwargs["min_price"] = min_price
        return redirect(url_for("index", **redirect_kwargs))

    def api_listings() -> str:
        session = SessionLocal()
        keyword = request.args.get("keyword", "").strip()
        if not keyword:
            rows = (
                session.query(KleinanzeigenListing.keyword)
                .order_by(desc(KleinanzeigenListing.scraped_at))
                .limit(1)
                .all()
            )
            keyword = rows[0][0] if rows else ""
        listings = _fetch_listings(session, keyword) if keyword else []
        return jsonify({"keyword": keyword, "items": listings})

    index_rule = (base_path or "") + "/"
    if not index_rule.startswith("/"):
        index_rule = "/" + index_rule
    if index_rule == "//":
        index_rule = "/"

    app.add_url_rule(index_rule, endpoint="index", view_func=index, methods=["GET"])
    app.add_url_rule(index_rule, endpoint="scrape", view_func=trigger_scrape, methods=["POST"])

    if index_rule != "/":
        app.add_url_rule("/", endpoint="root_index", view_func=index, methods=["GET"])
        app.add_url_rule("/", endpoint="root_scrape", view_func=trigger_scrape, methods=["POST"])

    api_rule = (base_path or "") + "/api/listings"
    if not api_rule.startswith("/"):
        api_rule = "/" + api_rule
    app.add_url_rule(api_rule, endpoint="api_listings", view_func=api_listings, methods=["GET"])
    if api_rule != "/api/listings":
        app.add_url_rule("/api/listings", endpoint="api_listings_root", view_func=api_listings, methods=["GET"])

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5003)), debug=False)

