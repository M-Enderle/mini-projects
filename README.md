# Mini Projects - Simple Version

One container that runs nginx + your projects.

## Usage

```bash
# Start
docker-compose up -d

# Stop  
docker-compose down

# View logs
docker-compose logs -f
```

## Access

- Main page: http://localhost:4000
- Kleinanzeigen Map: http://localhost:4000/kleinanzeigen-map/

## Add New Project

1. Create project directory with `pyproject.toml`
2. Add to `Dockerfile`:
   ```dockerfile
   COPY your-project/ ./your-project/
   RUN cd your-project && poetry install
   ```
3. Add to `nginx.conf`:
   ```nginx
   location /your-project/ {
       proxy_pass http://localhost:8502/;
   }
   ```
4. Add to `start.sh`:
   ```bash
   cd your-project && poetry run your-command &
   ```
5. Rebuild: `docker-compose up -d --build`

That's it! 