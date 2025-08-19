# Kleinanzeigen Map Scraper 🗺️

A Streamlit web application that scrapes Kleinanzeigen.de listings for any keyword and displays them on an interactive map.

## Features

- 🔍 **Keyword Search**: Search for any keyword on Kleinanzeigen.de
- 📄 **Multi-page Scraping**: Automatically scrapes all available pages (up to 100)
- 🗺️ **Interactive Map**: View all listings on an interactive map with color-coded markers
- 📊 **Data Export**: Download results as CSV
- 🎯 **Smart Filtering**: Filter by city and price range
- 💾 **Database Storage**: All data is stored in SQLite database with SQLAlchemy
- 📍 **Automatic Geocoding**: Converts postal codes and cities to map coordinates

## Installation

1. **Install dependencies using Poetry:**
   ```bash
   poetry install
   ```

2. **Install Playwright browsers:**
   ```bash
   poetry run playwright install
   ```

## Usage

### Streamlit Web App (Recommended)

1. **Start the Streamlit app:**
   ```bash
   poetry run streamlit run streamlit_app.py
   ```

2. **Open your browser** to `http://localhost:8501`

3. **Enter a keyword** in the sidebar (e.g., "tamron", "iphone", "bicycle")

4. **Set the number of pages** to scrape (default: 10)

5. **Click "Start Scraping"** and wait for the process to complete

6. **View results** on the interactive map and in the data table

### Command Line Usage

You can also run the scraper directly:

```bash
# Run the original scraper (hardcoded for "tamron")
poetry run python kleinanzeigen/main.py

# Test with 3 pages
poetry run python test_scraper.py
```

## How It Works

1. **Web Scraping**: Uses Playwright to navigate Kleinanzeigen.de pages
2. **Data Extraction**: Extracts title, price, postal code, city, and URL from each listing
3. **Geocoding**: Converts locations to GPS coordinates using Nominatim (OpenStreetMap)
4. **Database Storage**: Saves all data to SQLite database with SQLAlchemy ORM
5. **Map Visualization**: Creates interactive maps using Folium
6. **Web Interface**: Provides user-friendly interface with Streamlit

## Map Features

- **Color-coded markers**:
  - 🟢 Green: Under 100€
  - 🟠 Orange: 100€-1000€
  - 🔴 Red: Over 1000€
  - 🔵 Blue: No price or other

- **Interactive popups** with listing details and direct links
- **Automatic centering** based on listing locations
- **Responsive design** that works on different screen sizes

## Data Structure

The application stores the following data for each listing:

- **Title**: Item title/description
- **Price**: Listed price (if available)
- **PLZ**: German postal code
- **Ort**: City/location name
- **URL**: Direct link to the listing
- **Coordinates**: Latitude and longitude for mapping
- **Keyword**: Search term used
- **Timestamp**: When the listing was scraped

## Technical Details

- **Backend**: Python with asyncio for concurrent scraping
- **Web Scraping**: Playwright for JavaScript-heavy sites
- **HTML Parsing**: BeautifulSoup4 for data extraction
- **Database**: SQLite with SQLAlchemy ORM
- **Geocoding**: Geopy with Nominatim service
- **Frontend**: Streamlit for web interface
- **Maps**: Folium with OpenStreetMap tiles
- **Data Processing**: Pandas for data manipulation

## Rate Limiting & Ethics

The scraper includes:
- 1-second delays between page requests
- Respectful user agent strings
- Error handling for failed requests
- Duplicate detection to avoid re-scraping

Please use responsibly and respect Kleinanzeigen.de's terms of service.

## File Structure

```
kleinanzeigen-map/
├── kleinanzeigen/
│   ├── __init__.py
│   ├── main.py          # Original scraper
│   └── scraper.py       # Flexible scraper for Streamlit
├── streamlit_app.py     # Main Streamlit application
├── test_scraper.py      # Test script for 3 pages
├── run_scraper.py       # Simple runner script
├── pyproject.toml       # Poetry dependencies
├── poetry.lock          # Locked dependencies
└── README.md           # This file
```

## Troubleshooting

1. **Playwright browser issues**: Run `poetry run playwright install` again
2. **Geocoding rate limits**: The app includes delays, but you may need to wait if hitting limits
3. **No listings found**: Try different keywords or check if the site structure changed
4. **Map not loading**: Check your internet connection and try refreshing the page

## Contributing

Feel free to submit issues and enhancement requests!
