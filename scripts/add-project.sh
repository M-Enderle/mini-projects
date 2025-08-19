#!/bin/bash

# Script to add a new project to the mini-projects setup
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

# Function to show usage
show_usage() {
    print_color $BLUE "Usage: $0 <project-name> [project-type]"
    echo ""
    echo "Project types:"
    echo "  streamlit  - Streamlit data app (default)"
    echo "  flask      - Flask web app"
    echo "  fastapi    - FastAPI REST API"
    echo "  jupyter    - Jupyter notebook server"
    echo ""
    echo "Example:"
    echo "  $0 my-dashboard streamlit"
    echo "  $0 my-api fastapi"
}

# Check arguments
if [ $# -lt 1 ]; then
    show_usage
    exit 1
fi

PROJECT_NAME=$1
PROJECT_TYPE=${2:-streamlit}
PROJECT_DIR="$PROJECT_NAME"

# Validate project name
if [[ ! $PROJECT_NAME =~ ^[a-z][a-z0-9-]*$ ]]; then
    print_color $RED "Error: Project name must start with a letter and contain only lowercase letters, numbers, and hyphens"
    exit 1
fi

# Check if project already exists
if [ -d "$PROJECT_DIR" ]; then
    print_color $RED "Error: Project directory '$PROJECT_DIR' already exists"
    exit 1
fi

print_color $GREEN "Creating new $PROJECT_TYPE project: $PROJECT_NAME"

# Create project directory
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Initialize poetry project
print_color $YELLOW "Initializing poetry project..."
poetry init --no-interaction --name "$PROJECT_NAME" --version "0.1.0"

# Add dependencies based on project type
case $PROJECT_TYPE in
    streamlit)
        print_color $YELLOW "Adding Streamlit dependencies..."
        poetry add streamlit pandas numpy
        PORT=8501
        CMD="streamlit run app.py"
        ;;
    flask)
        print_color $YELLOW "Adding Flask dependencies..."
        poetry add flask gunicorn
        PORT=5000
        CMD="gunicorn --bind 0.0.0.0:5000 app:app"
        ;;
    fastapi)
        print_color $YELLOW "Adding FastAPI dependencies..."
        poetry add fastapi uvicorn
        PORT=8000
        CMD="uvicorn app:app --host 0.0.0.0 --port 8000"
        ;;
    jupyter)
        print_color $YELLOW "Adding Jupyter dependencies..."
        poetry add jupyter pandas numpy matplotlib
        PORT=8888
        CMD="jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root"
        ;;
    *)
        print_color $RED "Error: Unknown project type '$PROJECT_TYPE'"
        exit 1
        ;;
esac

# Create Dockerfile
print_color $YELLOW "Creating Dockerfile..."
cat > Dockerfile << EOF
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VENV_IN_PROJECT=1
ENV POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

# Set working directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --only=main && rm -rf \$POETRY_CACHE_DIR

# Copy application code
COPY . .

# Expose port
EXPOSE $PORT

# Run the application
CMD ["poetry", "run", "$CMD"]
EOF

# Create .dockerignore
print_color $YELLOW "Creating .dockerignore..."
cat > .dockerignore << 'EOF'
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

.DS_Store
.vscode
.idea

# Docker
Dockerfile*
docker-compose*
.dockerignore

# Poetry virtual environment (if created locally)
.venv

# README and other docs
README.md
EOF

# Create sample application based on type
print_color $YELLOW "Creating sample application..."
case $PROJECT_TYPE in
    streamlit)
        cat > app.py << 'EOF'
import streamlit as st
import pandas as pd
import numpy as np

st.title('New Streamlit Project')
st.write('Welcome to your new Streamlit application!')

# Sample data
data = pd.DataFrame({
    'x': np.random.randn(100),
    'y': np.random.randn(100)
})

st.line_chart(data)
EOF
        ;;
    flask)
        cat > app.py << 'EOF'
from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>New Flask Project</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
        </style>
    </head>
    <body>
        <h1>New Flask Project</h1>
        <p>Welcome to your new Flask application!</p>
    </body>
    </html>
    ''')

@app.route('/api/health')
def health():
    return {'status': 'ok'}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
EOF
        ;;
    fastapi)
        cat > app.py << 'EOF'
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="New FastAPI Project")

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>New FastAPI Project</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
        </style>
    </head>
    <body>
        <h1>New FastAPI Project</h1>
        <p>Welcome to your new FastAPI application!</p>
        <p><a href="/docs">API Documentation</a></p>
    </body>
    </html>
    """

@app.get("/api/health")
def health():
    return {"status": "ok"}
EOF
        ;;
    jupyter)
        mkdir -p notebooks
        cat > notebooks/Welcome.ipynb << 'EOF'
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Welcome to Your New Jupyter Project\n",
    "\n",
    "This is a sample notebook to get you started."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "\n",
    "# Sample data\n",
    "data = pd.DataFrame({\n",
    "    'x': np.random.randn(100),\n",
    "    'y': np.random.randn(100)\n",
    "})\n",
    "\n",
    "plt.scatter(data['x'], data['y'])\n",
    "plt.title('Sample Plot')\n",
    "plt.show()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.13.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
EOF
        ;;
esac

cd ..

# Update docker-compose.yaml
print_color $YELLOW "Updating docker-compose.yaml..."
# Create backup
cp docker-compose.yaml docker-compose.yaml.bak

# Add new service to docker-compose.yaml
cat >> docker-compose.yaml << EOF

  # $PROJECT_NAME Project
  $PROJECT_NAME:
    build:
      context: ./$PROJECT_NAME
      dockerfile: Dockerfile
    container_name: $PROJECT_NAME
    restart: unless-stopped
    networks:
      - mini-projects
EOF

# Update nginx configuration
print_color $YELLOW "Updating nginx configuration..."
# Create backup
cp nginx/nginx.conf nginx/nginx.conf.bak

# Add new location block before the default location
sed -i.tmp "/# Default 404 for unknown routes/i\\
\\
        # $PROJECT_NAME Project\\
        location /$PROJECT_NAME/ {\\
            proxy_pass http://$PROJECT_NAME:$PORT/;\\
            proxy_set_header Host \$host;\\
            proxy_set_header X-Real-IP \$remote_addr;\\
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;\\
            proxy_set_header X-Forwarded-Proto \$scheme;\\
        }\\
" nginx/nginx.conf && rm nginx/nginx.conf.tmp

print_color $GREEN "✅ Project '$PROJECT_NAME' created successfully!"
print_color $BLUE "Next steps:"
echo "1. Edit $PROJECT_NAME/app.py to implement your application"
echo "2. Add any additional dependencies: cd $PROJECT_NAME && poetry add <package>"
echo "3. Build and start: docker-compose up -d --build $PROJECT_NAME"
echo "4. Access at: http://projects.enderles.com/$PROJECT_NAME/"
echo ""
print_color $YELLOW "To update the project index page, edit the HTML in nginx/nginx.conf" 