import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from kleinanzeigen.scraper import FlexibleKleinanzeigenScraper
from datetime import datetime

# Simple page config
st.set_page_config(page_title="Kleinanzeigen-Karte", page_icon="🔍", layout="wide")

# Load PLZ coordinate data
@st.cache_data
def load_plz_data():
    """Load PLZ coordinates from CSV file"""
    try:
        df = pd.read_csv('plz_geocoord.csv')
        # Create a dictionary for fast lookup: PLZ -> (lat, lng)
        plz_dict = dict(zip(df['plz'].astype(str), zip(df['lat'], df['lng'])))
        return plz_dict
    except Exception as e:
        st.error(f"Fehler beim Laden der PLZ-Daten: {e}")
        return {}

# Load PLZ data once
PLZ_COORDS = load_plz_data()

def get_coordinates_from_plz(plz):
    """Get coordinates from PLZ using the CSV data"""
    if not plz:
        return None, None
    
    # Clean PLZ - remove any non-digits and convert to string
    plz_clean = ''.join(c for c in str(plz) if c.isdigit())
    if not plz_clean:
        return None, None
    
    # Try to find coordinates
    coords = PLZ_COORDS.get(plz_clean)
    if coords:
        return coords[0], coords[1]  # lat, lng
    
    return None, None

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None
if 'last_keyword' not in st.session_state:
    st.session_state.last_keyword = None

def scrape_data(keyword):
    """Scrape new data"""
    scraper = FlexibleKleinanzeigenScraper(keyword)
    
    # Progress placeholder
    progress_text = st.empty()
    
    def progress_callback(message):
        progress_text.text(message)
    
    try:
        scraper.scrape_all_pages(50, progress_callback)
        scraper.save_to_database(progress_callback)
        
        # Get results and add coordinates from PLZ
        listings = scraper.get_all_listings()
        
        # Add coordinates to listings using PLZ lookup
        progress_callback("Füge GPS-Koordinaten hinzu...")
        updated_count = 0
        
        for listing in listings:
            if not listing.latitude or not listing.longitude:
                # Get coordinates from PLZ
                lat, lng = get_coordinates_from_plz(listing.plz)
                
                if lat and lng:
                    listing.latitude = lat
                    listing.longitude = lng
                    updated_count += 1
                    progress_callback(f"Koordinaten für PLZ {listing.plz} hinzugefügt")
        
        # Save updated coordinates
        if updated_count > 0:
            scraper.session.commit()
            progress_callback(f"Koordinaten zu {updated_count} Anzeigen hinzugefügt")
        
        # Convert to data format
        data = []
        for listing in listings:
            # Get URL from scraped data since it's not stored in database
            scraped_listing = next((item for item in scraper.all_listings if item['title'] == listing.title and item['plz'] == listing.plz), None)
            url = scraped_listing['url'] if scraped_listing else ""
            
            data.append({
                'title': listing.title,
                'price': listing.price,
                'plz': listing.plz,
                'ort': listing.ort,
                'url': url,  # Include URL from scraped data
                'latitude': listing.latitude,
                'longitude': listing.longitude
            })
        
        scraper.close()
        return data
    except Exception as e:
        st.error(f"Fehler: {e}")
        scraper.close()
        return []

def clean_price_display(price_str):
    """Clean price string for display - keep first price and VB if present"""
    if not price_str:
        return None
    
    # Split by € and take the first part
    first_part = price_str.split('€')[0].strip()
    
    # Check if original had VB after the first price
    has_vb = 'VB' in price_str and price_str.find('VB') < price_str.find('€', price_str.find('€') + 1) if price_str.count('€') > 1 else 'VB' in price_str
    
    # Clean the first part but preserve structure
    if first_part:
        # Remove any trailing VB from first part for processing
        clean_first = first_part.replace('VB', '').strip()
        if clean_first:
            result = clean_first + '€'
            if has_vb:
                result += ' VB'
            return result
    
    return price_str  # fallback to original

def create_simple_map(data):
    """Create a simple map"""
    valid_data = [d for d in data if d['latitude'] and d['longitude']]
    
    if not valid_data:
        return None
    
    # Center map on Germany (hardcoded coordinates)
    germany_center_lat = 51.1657
    germany_center_lon = 10.4515
    
    m = folium.Map(location=[germany_center_lat, germany_center_lon], zoom_start=6)
    
    # Calculate price statistics for relative coloring
    prices = []
    for item in valid_data:
        if item['price']:
            try:
                # Same price parsing logic as below
                price_str = item['price'].split('€')[0].strip()
                price_str = price_str.replace('VB', '').replace('ab', '').strip()
                price_str = price_str.replace('.', '').replace(',', '')
                price_clean = ''.join(c for c in price_str if c.isdigit())
                
                if price_clean and price_clean.isdigit():
                    prices.append(int(price_clean))
            except:
                continue
    
    # Calculate statistics if we have prices
    price_stats = None
    if prices:
        import statistics
        avg_price = statistics.mean(prices)
        try:
            std_dev = statistics.stdev(prices) if len(prices) > 1 else 0
        except:
            std_dev = 0
        price_stats = {'avg': avg_price, 'std': std_dev}
    
    # Add markers with color coding based on price
    for item in valid_data:
        # Determine marker color based on price
        color = 'blue'  # default color
        icon = 'info-sign'
        
        if item['price']:
            try:
                # Cut everything after the first € sign
                price_str = item['price'].split('€')[0].strip()
                
                # Remove common non-numeric characters but keep digits and dots/commas
                price_str = price_str.replace('VB', '').replace('ab', '').strip()
                
                # Replace common thousand separators
                price_str = price_str.replace('.', '').replace(',', '')
                
                # Extract only digits
                price_clean = ''.join(c for c in price_str if c.isdigit())
                
                if price_clean and price_clean.isdigit():
                    price_val = int(price_clean)
                    
                    # Color coding based on relative price (standard deviations from mean)
                    if price_stats and price_stats['std'] > 0:
                        avg = price_stats['avg']
                        std = price_stats['std']
                        
                        # Calculate how many standard deviations from mean
                        z_score = (price_val - avg) / std
                        
                        if z_score < -1.5:  # Much below average
                            color = 'green'
                            icon = 'euro-sign'
                        elif z_score < -0.5:  # Below average
                            color = 'lightgreen'
                            icon = 'euro-sign'
                        elif z_score < 0.5:  # Around average
                            color = 'orange'
                            icon = 'euro-sign'
                        elif z_score < 1.5:  # Above average
                            color = 'red'
                            icon = 'euro-sign'
                        else:  # Much above average
                            color = 'darkred'
                            icon = 'euro-sign'
                    else:
                        # Fallback to simple ranges if no statistics available
                        if price_val < 100:
                            color = 'green'
                        elif price_val < 500:
                            color = 'orange'
                        else:
                            color = 'red'
                        icon = 'euro-sign'
                        
            except (ValueError, AttributeError):
                # If price parsing fails, use default blue
                color = 'blue'
                icon = 'info-sign'
        
        # Clean price for display
        clean_price = clean_price_display(item['price'])
        
        popup_content = f"<b>{item['title'][:50]}</b><br><b>Preis: {clean_price or 'k.A.'}</b><br>Standort: {item['plz']} {item['ort']}"
        if item.get('url'):
            popup_content += f"<br><a href='{item['url']}' target='_blank'>Anzeige ansehen</a>"
            
        folium.Marker(
            location=[item['latitude'], item['longitude']],
            popup=popup_content,
            tooltip=f"{clean_price or 'Kein Preis'} - {item['ort']}",
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)
    
    return m

# Main UI
st.title("Kleinanzeigen-Karte")

# Simple input form
col1, col2 = st.columns([4, 1])

with col1:
    keyword = st.text_input("Suche nach:")

with col2:
    st.write("")  # spacing
    search_btn = st.button("🔍 Suchen", type="primary", use_container_width=True)

# Search action - always scrape fresh data
if search_btn and keyword:
    with st.spinner("Suche läuft..."):
        results = scrape_data(keyword)
        if results:
            st.session_state.results = results
            st.session_state.last_keyword = keyword
            st.success(f"{len(results)} Anzeigen gefunden!")
        else:
            st.warning("Keine Ergebnisse gefunden")

# Display results
if st.session_state.results:
    data = st.session_state.results
    
    # Map
    st.subheader("📍 Karte")
    
    # Calculate and show price statistics
    prices = []
    for item in data:
        if item['price']:
            try:
                price_str = item['price'].split('€')[0].strip()
                price_str = price_str.replace('VB', '').replace('ab', '').strip()
                price_str = price_str.replace('.', '').replace(',', '')
                price_clean = ''.join(c for c in price_str if c.isdigit())
                if price_clean and price_clean.isdigit():
                    prices.append(int(price_clean))
            except:
                continue
    
    map_obj = create_simple_map(data)
    if map_obj:
        st_folium(map_obj, width="100%", height=500)
    else:
        st.info("Keine Standorte zum Anzeigen auf der Karte gefunden")

else:
    st.info("Gib einen Suchbegriff ein und klicke auf Suchen um zu beginnen") 