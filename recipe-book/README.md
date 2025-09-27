# Recipe Book

A modern web application for managing and organizing recipes with semantic search capabilities.

## Features

- 🍳 Create, edit, and organize recipes
- 🔍 Semantic search using AI embeddings
- 📁 Filter by source and rating
- 📤 JSON import for bulk recipe creation
- ⭐ 5-star rating system
- 🏷️ Tag-based categorization
- 📱 Responsive design
- 🤖 **NEW:** AI recipe generation with Gemini
  - 📷 Generate recipes from food images
  - 📝 Create recipes from text descriptions
  - 🔗 Extract recipes from web URLs

## Quick Start

1. Install dependencies:
```bash
poetry install
```

2. Set up environment variables for AI features (optional):
```bash
cp .env.example .env
# Edit .env and add your Gemini API key
```

3. Run the application:
```bash
poetry run python app.py
```

4. Open your browser to `http://localhost:5002`

## AI Recipe Generation Setup

To use the AI recipe generation features, you need a Google Gemini API key:

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy `.env.example` to `.env`
4. Add your API key to the `.env` file:
```
GEMINI_API_KEY=your_actual_api_key_here
```

The AI features will be available in the "New Recipe" form and allow you to:
- Upload food images to generate recipes
- Describe a dish to create a recipe
- Provide URLs to extract recipes from web pages

## JSON Import Format

The application supports importing recipes via JSON files. You can upload a single recipe or an array of recipes.

### Single Recipe Format

```json
{
  "title": "Aprikosen-Panna-Cotta mit gerösteten Pistazien",
  "description": "Ein cremiges Dessert mit fruchtiger Aprikosennote und knusprigen Pistazien",
  "image_url": "https://example.com/panna-cotta.jpg",
  "source": "Meine Küche",
  "filters": "dessert, vegetarisch, glutenfrei",
  "rating": 4.5,
  "ingredients": [
    "200ml Sahne",
    "50g Zucker",
    "1 Päckchen Gelatine",
    "1 TL Vanilleextrakt",
    "2 EL Orangenblütenwasser",
    "100g getrocknete Aprikosen",
    "50g Pistazien, gehackt"
  ],
  "steps": [
    {
      "text": "Gelatine in kaltem Wasser einweichen."
    },
    {
      "text": "Sahne mit Zucker und Vanille in einem Topf erhitzen, nicht kochen lassen."
    },
    {
      "text": "Gelatine ausdrücken und in die warme Sahne einrühren bis sie vollständig aufgelöst ist."
    },
    {
      "text": "Orangenblütenwasser unterrühren und die Masse in Förmchen füllen."
    },
    {
      "text": "Mindestens 4 Stunden im Kühlschrank kalt stellen."
    },
    {
      "text": "Aprikosen in einer Pfanne ohne Fett rösten bis sie duften."
    },
    {
      "text": "Panna Cotta stürzen und mit gerösteten Aprikosen und gehackten Pistazien servieren."
    }
  ]
}
```

### Multiple Recipes Format

```json
[
  {
    "title": "Recipe 1",
    "description": "First recipe description",
    // ... other fields
  },
  {
    "title": "Recipe 2", 
    "description": "Second recipe description",
    // ... other fields
  }
]
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | The name of the recipe |
| `description` | string | Yes | A brief description of the dish |
| `image_url` | string | No | URL to an image of the finished dish |
| `source` | string | No | Where the recipe came from (defaults to "Unbekannt") |
| `filters` | string | No | Comma-separated tags/categories |
| `rating` | number | No | Rating from 1-5 (can be decimal like 4.5) |
| `ingredients` | array/string | No | List of ingredients or newline-separated string |
| `steps` | array/string | No | Cooking steps as objects with "text" field or newline-separated string |

### Alternative Formats

The application is flexible with input formats:

**Ingredients as string:**
```json
"ingredients": "200ml Sahne\n50g Zucker\n1 Päckchen Gelatine"
```

**Steps as string:**
```json
"steps": "Gelatine einweichen\nSahne erhitzen\nGelatine einrühren"
```

**Steps as simple array:**
```json
"steps": [
  "Gelatine in kaltem Wasser einweichen",
  "Sahne mit Zucker erhitzen"
]
```

## Usage

### Creating Recipes

1. Click "Neu" in the navigation
2. Fill out the form manually, or
3. Upload a JSON file using "JSON importieren"
4. Review the populated fields
5. Click "Speichern" to save

### Searching Recipes

The application uses semantic search powered by AI embeddings:

- Search by ingredients: "Zitrus, Pasta"
- Search by cuisine: "Italienisch"
- Search by dish type: "Dessert"
- Search by cooking method: "Gebraten"

### Filtering

- **Source**: Filter by recipe source/cookbook
- **Rating**: Show only recipes with minimum star rating

## Technical Details

### Architecture

- **Backend**: Flask with SQLite database
- **Search**: Sentence transformers for semantic embeddings
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Styling**: Custom CSS with modern design

### Database Schema

```sql
CREATE TABLE recipe (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    image_url VARCHAR(500),
    source VARCHAR(200) NOT NULL,
    filters VARCHAR(500),
    rating FLOAT,
    ingredients TEXT, -- JSON array
    steps TEXT,       -- JSON array
    embedding BLOB,   -- AI embedding vector
    embedding_dim INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home page with search and filters |
| POST | `/` | Search recipes |
| GET | `/recipes/new` | Recipe creation form |
| POST | `/recipes/new` | Create new recipe or import JSON |
| GET | `/recipes/{slug}` | Recipe detail page |
| GET | `/recipes/{slug}/edit` | Recipe edit form |
| POST | `/recipes/{slug}/edit` | Update recipe |

### Configuration

The application supports configuration via environment variables:

- `BASE_PATH`: URL prefix for reverse proxy deployment
- `FLASK_ENV`: Set to "development" for debug mode

### Development

```bash
# Install dependencies
poetry install

# Run in development mode
export FLASK_ENV=development
poetry run python app.py

# The app will be available at http://localhost:5002
```

### Deployment

The application includes Docker support:

```bash
# Build container
docker build -t recipe-book .

# Run container
docker run -p 5002:5002 recipe-book
```

Or use the included docker-compose setup for a complete deployment with nginx.

## Dependencies

- Flask: Web framework
- SQLAlchemy: Database ORM
- sentence-transformers: AI embeddings for search
- numpy: Vector operations
- Jinja2: Template engine

## License

This project is open source and available under the MIT License.
