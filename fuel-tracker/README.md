# Spritpreis Tracker

Verfolge Tankstellenpreise jede Minute. Flask + SQLite, Seaborn Diagramme, Leaflet Karte.

## Setup

```bash
cd fuel-tracker
poetry install
poetry run python app.py
```

Öffne http://127.0.0.1:5001

## Tankstellen konfigurieren

Füge Einträge in `fuel-tracker/data/urls.txt` im Format `Name,URL` hinzu (eine pro Zeile). Der Hintergrund-Fetcher aktualisiert jede Minute. Du kannst auch "Jetzt aktualisieren" im Header klicken für eine sofortige Aktualisierung.

## Notizen
- Datenquelle: ÖAMTC API
- Datenbankdatei: `fuel-tracker/fuel_tracker.db`
- Endpunkte:
  - `/` Tankstellenliste
  - `/station/<id>` Tankstellendetails, Karte und Preisverlauf
  - `/api/stations` JSON
  - `/api/station/<id>/history` JSON
  - `POST /fetch-now` einmalige Aktualisierung auslösen 