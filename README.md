# Mini Projects

A containerized multi-project setup with nginx reverse proxy for hosting multiple small projects on a home server.

## 🏗️ Architecture

- **Nginx Reverse Proxy**: Routes requests from `projects.enderles.com` to individual project containers
- **Individual Project Containers**: Each project runs in its own container with poetry for dependency management
- **Docker Compose**: Orchestrates all services with a single command

## 🚀 Quick Start

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Access projects:**
   - Main index: `http://projects.enderles.com/` (or `localhost:4000`)
   - Kleinanzeigen Map: `http://projects.enderles.com/kleinanzeigen-map/`

3. **Stop all services:**
   ```bash
   docker-compose down
   ```

## 📁 Current Projects

### Kleinanzeigen Map
- **Path**: `/kleinanzeigen-map/`
- **Description**: Scrape and visualize Kleinanzeigen listings on an interactive map
- **Technology**: Python, Streamlit, SQLAlchemy, Folium
- **Port**: Internal 8501

## ➕ Adding New Projects

### 1. Create Project Directory
```bash
mkdir your-new-project
cd your-new-project
```

### 2. Initialize with Poetry
```bash
poetry init
poetry add your-dependencies
```

### 3. Create Dockerfile
Create a `Dockerfile` similar to the kleinanzeigen-map example:

```dockerfile
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VENV_IN_PROJECT=1
ENV POETRY_CACHE_DIR=/tmp/poetry_cache

RUN apt-get update && apt-get install -y curl build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install poetry

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --only=main && rm -rf $POETRY_CACHE_DIR

COPY . .
EXPOSE 8000

CMD ["poetry", "run", "python", "app.py"]
```

### 4. Update docker-compose.yaml
Add your service to the `docker-compose.yaml`:

```yaml
  your-new-project:
    build:
      context: ./your-new-project
      dockerfile: Dockerfile
    container_name: your-new-project
    volumes:
      - ./your-new-project/data:/app/data  # If you need persistent data
    environment:
      - YOUR_ENV_VAR=value
    restart: unless-stopped
    networks:
      - mini-projects
```

### 5. Update nginx configuration
Add a new location block in `nginx/nginx.conf`:

```nginx
# Your New Project
location /your-new-project/ {
    proxy_pass http://your-new-project:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 6. Update the index page
Modify the HTML in the nginx.conf root location to include your new project.

### 7. Rebuild and restart
```bash
docker-compose up -d --build
```

## 🛠️ Development

### Building individual services
```bash
# Build specific service
docker-compose build kleinanzeigen-map

# Build and start specific service
docker-compose up -d --build kleinanzeigen-map
```

### Viewing logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f kleinanzeigen-map
```

### Accessing containers
```bash
# Execute commands in running container
docker-compose exec kleinanzeigen-map bash

# Or for Alpine-based containers
docker-compose exec nginx sh
```

## 📋 Project Templates

### Web App Template (Flask/FastAPI)
```bash
# Create new web app project
mkdir my-web-app
cd my-web-app
poetry init
poetry add flask  # or fastapi uvicorn
```

### Data Science Template (Jupyter/Streamlit)
```bash
# Create new data science project
mkdir my-data-project
cd my-data-project
poetry init
poetry add streamlit pandas numpy matplotlib
```

### API Template (FastAPI)
```bash
# Create new API project
mkdir my-api
cd my-api
poetry init
poetry add fastapi uvicorn pydantic
```

## 🔧 Configuration

### Environment Variables
Set project-specific environment variables in the docker-compose.yaml file under each service.

### Persistent Data
Mount volumes for any data that needs to persist between container restarts:
```yaml
volumes:
  - ./project-name/data:/app/data
  - ./project-name/config.yaml:/app/config.yaml:ro
```

### Custom Domains
To add custom domains or subdomains, update the nginx configuration and ensure your DNS points to the server.

## 🚨 Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs service-name

# Rebuild without cache
docker-compose build --no-cache service-name
```

### Port conflicts
Make sure no other services are using port 4000 on your host machine.

### Permission issues
Ensure proper file permissions for mounted volumes:
```bash
sudo chown -R $USER:$USER ./project-directory
```

## 📊 Monitoring

### Health checks
- Nginx health: `http://projects.enderles.com/health`
- Individual project health depends on the application

### Resource usage
```bash
# View resource usage
docker stats

# View specific container
docker stats kleinanzeigen-map
```

## 🔐 Security Considerations

1. **Firewall**: Ensure only necessary ports are exposed
2. **Updates**: Regularly update base images and dependencies
3. **Secrets**: Use Docker secrets or environment files for sensitive data
4. **SSL**: Consider adding SSL termination at the nginx level

## 📝 License

This project setup is open source. Individual projects may have their own licenses. 