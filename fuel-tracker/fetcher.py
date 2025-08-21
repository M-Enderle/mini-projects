import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import List, Optional

import requests
from flask import current_app

from database import insert_prices, map_source, upsert_station, get_db

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_URLS_FILE = os.path.join(_DATA_DIR, "urls.txt")
_FETCH_INTERVAL_SECONDS = 60


def _ensure_data_dir() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)


def _load_urls() -> List[tuple]:
    """Returns list of (custom_name, url) tuples"""
    _ensure_data_dir()
    if not os.path.exists(_URLS_FILE):
        return []
    urls = []
    with open(_URLS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "," in line:
                parts = line.split(",", 1)
                custom_name = parts[0].strip()
                url = parts[1].strip()
                urls.append((custom_name, url))
            else:
                # Fallback: treat as URL-only
                urls.append((None, line))
    return urls


def _safe_get(dct, path: List[str], default=None):
    cur = dct
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        elif isinstance(cur, list) and isinstance(key, int) and 0 <= key < len(cur):
            cur = cur[key]
        else:
            return default
    return cur


def _parse_payload(payload: dict, source_url: str, custom_name: Optional[str] = None) -> Optional[dict]:
    try:
        data = payload.get("data", {})
        header = data.get("header", {})
        addresses = data.get("addresses", [])
        logo_list = header.get("logos", []) or data.get("logos", [])
        coords = _safe_get(data, ["geoData", "coordinates", 0], {})
        addr = addresses[0] if addresses else {}
        external_id = str(header.get("id")) if header.get("id") is not None else None
        if not external_id:
            return None
        # Use custom name if provided, otherwise fallback to API name
        station_name = custom_name if custom_name else _safe_get(header, ["names", 0, "value"], "Unknown")
        station_meta = {
            "external_id": external_id,
            "name": station_name,
            "street": addr.get("street"),
            "house_number": addr.get("houseNumber"),
            "postal_code": addr.get("postalCode"),
            "city": addr.get("city"),
            "county": addr.get("county"),
            "country": addr.get("country"),
            "longitude": coords.get("longitude", addr.get("longitude")),
            "latitude": coords.get("latitude", addr.get("latitude")),
            "logo_url": _safe_get(logo_list, [0, "url"], None),
            "operator_name": _safe_get(data, ["operator", "companyName"], None),
            "operator_phone": _safe_get(data, ["operator", "phone"], None),
            "operator_email": _safe_get(data, ["operator", "email"], None),
            "operator_url": _safe_get(data, ["operator", "url"], None),
            "last_updated": header.get("lastUpdated"),
            "source_url": source_url,
        }
        prices_groups = data.get("prices", [])
        fuel_prices = []
        for group in prices_groups:
            for p in group.get("prices", []):
                fuel_code = p.get("fuel")
                if isinstance(fuel_code, str) and fuel_code.upper().startswith("GASOLINE"):
                    fuel_prices.append(
                        {
                            "fuel": fuel_code,
                            "price": p.get("price"),
                            "unit": p.get("unit"),
                            "lastUpdated": p.get("lastUpdated"),
                        }
                    )
        return {"meta": station_meta, "fuel_prices": fuel_prices}
    except Exception:
        return None


def fetch_once_all() -> int:
    urls = _load_urls()
    if not urls:
        return 0
    fetched_total = 0
    fetched_at = datetime.now(timezone.utc).isoformat()
    for custom_name, url in urls:
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            payload = resp.json()
            parsed = _parse_payload(payload, url, custom_name)
            if not parsed:
                continue
            upsert_station(parsed["meta"])
            map_source(url, parsed["meta"]["external_id"])
            fetched_total += insert_prices(parsed["meta"]["external_id"], fetched_at, parsed["fuel_prices"])
        except Exception:
            continue
    return fetched_total


def _loop() -> None:
    while True:
        try:
            fetch_once_all()
        except Exception:
            pass
        time.sleep(_FETCH_INTERVAL_SECONDS)


_background_thread: Optional[threading.Thread] = None


def start_background_fetch_loop() -> None:
    global _background_thread
    if _background_thread and _background_thread.is_alive():
        return
    _ensure_data_dir()
    _background_thread = threading.Thread(target=_loop, name="fuel-fetch-loop", daemon=True)
    _background_thread.start() 