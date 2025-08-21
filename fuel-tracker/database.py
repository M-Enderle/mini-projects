import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from flask import g, has_app_context

_DB_PATH = os.path.join(os.path.dirname(__file__), "fuel_tracker.db")
_global_db: Optional[sqlite3.Connection] = None


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_db() -> sqlite3.Connection:
    global _global_db
    if has_app_context():
        db: Optional[sqlite3.Connection] = getattr(g, "_db", None)
        if db is None:
            db = sqlite3.connect(_DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
            db.row_factory = sqlite3.Row
            g._db = db
        return db
    # Fallback for background threads without app context
    if _global_db is None:
        _global_db = sqlite3.connect(_DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
        _global_db.row_factory = sqlite3.Row
    return _global_db


def close_db() -> None:
    global _global_db
    if has_app_context():
        db: Optional[sqlite3.Connection] = getattr(g, "_db", None)
        if db is not None:
            db.close()
            g._db = None
    else:
        if _global_db is not None:
            _global_db.close()
            _global_db = None


def init_db() -> None:
    db = get_db()
    with db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS stations (
                external_id TEXT PRIMARY KEY,
                name TEXT,
                street TEXT,
                house_number TEXT,
                postal_code TEXT,
                city TEXT,
                county TEXT,
                country TEXT,
                longitude REAL,
                latitude REAL,
                logo_url TEXT,
                operator_name TEXT,
                operator_phone TEXT,
                operator_email TEXT,
                operator_url TEXT,
                last_updated TEXT,
                source_url TEXT
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                fuel TEXT NOT NULL,
                price REAL,
                unit TEXT,
                api_last_updated TEXT,
                FOREIGN KEY(station_id) REFERENCES stations(external_id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                url TEXT PRIMARY KEY,
                station_id TEXT
            )
            """
        )
        db.execute("CREATE INDEX IF NOT EXISTS idx_prices_station_time ON prices(station_id, fetched_at)")


def upsert_station(meta: dict) -> None:
    db = get_db()
    with db:
        db.execute(
            """
            INSERT INTO stations (
                external_id, name, street, house_number, postal_code, city, county, country,
                longitude, latitude, logo_url, operator_name, operator_phone, operator_email,
                operator_url, last_updated, source_url
            ) VALUES (
                :external_id, :name, :street, :house_number, :postal_code, :city, :county, :country,
                :longitude, :latitude, :logo_url, :operator_name, :operator_phone, :operator_email,
                :operator_url, :last_updated, :source_url
            )
            ON CONFLICT(external_id) DO UPDATE SET
                name=excluded.name,
                street=excluded.street,
                house_number=excluded.house_number,
                postal_code=excluded.postal_code,
                city=excluded.city,
                county=excluded.county,
                country=excluded.country,
                longitude=excluded.longitude,
                latitude=excluded.latitude,
                logo_url=excluded.logo_url,
                operator_name=excluded.operator_name,
                operator_phone=excluded.operator_phone,
                operator_email=excluded.operator_email,
                operator_url=excluded.operator_url,
                last_updated=excluded.last_updated,
                source_url=excluded.source_url
            """,
            meta,
        )


def insert_prices(station_id: str, fetched_at_iso: str, fuel_prices: Iterable[dict]) -> int:
    db = get_db()
    rows = 0
    with db:
        for fp in fuel_prices:
            db.execute(
                """
                INSERT INTO prices (station_id, fetched_at, fuel, price, unit, api_last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    station_id,
                    fetched_at_iso,
                    fp.get("fuel"),
                    fp.get("price"),
                    fp.get("unit"),
                    fp.get("lastUpdated"),
                ),
            )
            rows += 1
    return rows


def map_source(url: str, station_id: Optional[str]) -> None:
    db = get_db()
    with db:
        db.execute(
            "INSERT INTO sources (url, station_id) VALUES (?, ?) ON CONFLICT(url) DO UPDATE SET station_id=excluded.station_id",
            (url, station_id),
        )


def fetch_stations() -> List[sqlite3.Row]:
    db = get_db()
    cur = db.execute(
        "SELECT external_id, name, city, street, house_number, postal_code, logo_url, latitude, longitude FROM stations ORDER BY name"
    )
    return cur.fetchall()


def fetch_station_by_id(station_id: str) -> Optional[sqlite3.Row]:
    db = get_db()
    cur = db.execute(
        "SELECT * FROM stations WHERE external_id = ?",
        (station_id,),
    )
    row = cur.fetchone()
    return row


def fetch_price_history(station_id: str) -> List[sqlite3.Row]:
    db = get_db()
    cur = db.execute(
        """SELECT fuel, price, unit, fetched_at, api_last_updated 
        FROM prices 
        WHERE station_id = ? AND fetched_at >= datetime('now', '-24 hours')
        ORDER BY fetched_at ASC""",
        (station_id,),
    )
    return cur.fetchall()


def fetch_price_stats(station_id: str) -> dict:
    db = get_db()
    # Use substr to avoid timezone parsing pitfalls; treat timestamps as UTC
    avg_weekday = db.execute(
        """
        SELECT strftime('%w', substr(fetched_at, 1, 19)) AS weekday,
               AVG(price) AS avg_price
        FROM prices
        WHERE station_id = ?
        GROUP BY weekday
        ORDER BY CAST(weekday AS INTEGER)
        """,
        (station_id,),
    ).fetchall()

    avg_hour = db.execute(
        """
        SELECT substr(fetched_at, 12, 2) AS hour,
               AVG(price) AS avg_price
        FROM prices
        WHERE station_id = ?
        GROUP BY hour
        ORDER BY CAST(hour AS INTEGER)
        """,
        (station_id,),
    ).fetchall()

    avg_month = db.execute(
        """
        SELECT substr(fetched_at, 1, 7) AS month,
               AVG(price) AS avg_price
        FROM prices
        WHERE station_id = ?
        GROUP BY month
        ORDER BY month
        """,
        (station_id,),
    ).fetchall()

    min_day = db.execute(
        """
        SELECT substr(fetched_at, 1, 10) AS day,
               MIN(price) AS min_price
        FROM prices
        WHERE station_id = ?
        GROUP BY day
        ORDER BY day
        """,
        (station_id,),
    ).fetchall()

    return {
        "avg_by_weekday": [dict(r) for r in avg_weekday],
        "avg_by_hour": [dict(r) for r in avg_hour],
        "avg_by_month": [dict(r) for r in avg_month],
        "min_by_day": [dict(r) for r in min_day],
    }


def fetch_stations_with_current_price() -> List[sqlite3.Row]:
    db = get_db()
    cur = db.execute(
        """
        SELECT s.external_id, s.name, s.city, s.street, s.house_number, s.postal_code,
               s.logo_url, s.latitude, s.longitude,
               p.price as current_price, p.fetched_at as price_time
        FROM stations s
        LEFT JOIN (
            SELECT station_id, price, fetched_at,
                   ROW_NUMBER() OVER (PARTITION BY station_id ORDER BY fetched_at DESC) as rn
            FROM prices
        ) p ON s.external_id = p.station_id AND p.rn = 1
        ORDER BY s.name
        """
    )
    return cur.fetchall() 