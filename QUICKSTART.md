# 🚀 Quick Start Guide

## Prerequisites
- Docker and Docker Compose installed
- Poetry installed (for local development)

## Start Everything
```bash
# Start all services
./scripts/manage.sh start

# Or use docker-compose directly
docker-compose up -d
```

## Access Your Projects
- **Main Index**: http://projects.enderles.com/ (or localhost:4000)
- **Kleinanzeigen Map**: http://projects.enderles.com/kleinanzeigen-map/

## Add New Projects
```bash
# Add a new Streamlit project
./scripts/manage.sh add my-dashboard streamlit

# Add a new FastAPI project  
./scripts/manage.sh add my-api fastapi

# Add a new Flask web app
./scripts/manage.sh add my-webapp flask

# Add a new Jupyter notebook server
./scripts/manage.sh add my-notebooks jupyter
```

## Common Commands
```bash
# View status
./scripts/manage.sh status

# View logs
./scripts/manage.sh logs -f

# Stop everything
./scripts/manage.sh stop

# List all projects
./scripts/manage.sh list

# Clean up Docker resources
./scripts/manage.sh clean
```

## Project Structure
```
mini-projects/
├── docker-compose.yaml       # Main orchestration
├── nginx/
│   └── nginx.conf            # Reverse proxy config
├── scripts/
│   ├── manage.sh            # Management commands
│   └── add-project.sh       # Add new projects
├── kleinanzeigen-map/       # Example project
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app.py
└── your-new-projects/       # Future projects go here
```

## For Your Home Server
1. Point `projects.enderles.com` to your server's IP
2. Configure your main nginx to proxy to port 4000:
   ```nginx
   location / {
       proxy_pass http://localhost:4000;
   }
   ```
3. Start the services: `./scripts/manage.sh start`

That's it! 🎉 