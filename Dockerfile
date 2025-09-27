FROM python:3.13-slim

# Install nginx and poetry
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*
RUN pip install poetry && poetry config virtualenvs.create false

WORKDIR /app

# Copy and install kleinanzeigen-map
COPY kleinanzeigen-map/ ./kleinanzeigen-map/
RUN cd kleinanzeigen-map && poetry install

# Copy and install fuel-tracker
COPY fuel-tracker/ ./fuel-tracker/
RUN cd fuel-tracker && poetry install

# Copy and install recipe-book
COPY recipe-book/ ./recipe-book/
RUN cd recipe-book && poetry install

# Copy nginx config and static index page
COPY nginx.conf /etc/nginx/nginx.conf
RUN mkdir -p /usr/share/nginx/html
COPY index.html /usr/share/nginx/html/index.html

# Copy static files for serving by nginx
COPY recipe-book/static/ /usr/share/nginx/html/static/
COPY fuel-tracker/static/ /usr/share/nginx/html/fuel-tracker-static/

# Simple startup script
COPY start.sh ./
RUN chmod +x start.sh

EXPOSE 4000

CMD ["./start.sh"] 