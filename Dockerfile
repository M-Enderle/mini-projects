FROM python:3.13-slim

# Install nginx and poetry
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*
RUN pip install poetry

WORKDIR /app

# Copy and install kleinanzeigen-map
COPY kleinanzeigen-map/ ./kleinanzeigen-map/
RUN cd kleinanzeigen-map && poetry install

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Simple startup script
COPY start.sh ./
RUN chmod +x start.sh

EXPOSE 4000

CMD ["./start.sh"] 