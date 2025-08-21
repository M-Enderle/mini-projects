# Mini Projects

Collection of small web applications running in Docker.

## Services

- **Kleinanzeigen Map** (Port 8501) - Visualizes classified ads on a map
- **Spritpreis Tracker** (Port 5001) - Tracks fuel station prices every minute

## Setup

```bash
# Build and start all services
docker-compose up --build

# Access the services
open http://localhost:4000
```

## Individual Services

### Kleinanzeigen Map
- Streamlit app at `/kleinanzeigen-map/`
- SQLite database: `kleinanzeigen-map/kleinanzeigen.db`

### Spritpreis Tracker  
- Flask app at `/fuel-tracker/`
- SQLite database: `fuel-tracker/fuel_tracker.db`
- Background fetcher runs every 60 seconds
- Configure stations in `fuel-tracker/data/urls.txt`

## Architecture

- **Nginx** reverse proxy on port 4000
- **Docker Compose** orchestrates all services
- **Volume mounts** persist databases 