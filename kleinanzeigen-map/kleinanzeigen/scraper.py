import time
from urllib.parse import urljoin, quote
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Database setup
Base = declarative_base()

class KleinanzeigenListing(Base):
    __tablename__ = 'listings'
    
    id = Column(Integer, primary_key=True)
    keyword = Column(String(200))  # Add keyword field
    title = Column(String(500))
    price = Column(String(100))  # Keep as string to handle various price formats
    plz = Column(String(10))
    ort = Column(String(200))
    # url = Column(Text)  # Removed URL storage
    latitude = Column(Float)  # Add coordinates for mapping
    longitude = Column(Float)
    scraped_at = Column(DateTime, default=datetime.utcnow)





class FlexibleKleinanzeigenScraper:
    def __init__(self, keyword, db_path="kleinanzeigen.db"):
        # Setup database
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        self.keyword = keyword
        self.base_url = f"https://www.kleinanzeigen.de/s-seite:{{}}/{quote(keyword)}/k0"
        self.all_listings = []
        
        # Setup requests session with headers
        self.session_requests = requests.Session()
        self.session_requests.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
    def scrape_page(self, page_num, progress_callback=None):
        """Scrape a single page and extract listing data"""
        url = self.base_url.format(page_num)
        
        try:
            if progress_callback:
                progress_callback(f"Scraping page {page_num}: {url}")
            
            response = self.session_requests.get(url, timeout=30)
            response.raise_for_status()

            if url != response.url:
                print(url)
                print(response.url)
                print("Redirected. This means the last page was reached.")
                return []
            
            # Parse content 
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all listing articles
            listings = soup.find_all('article', class_='aditem')
            
            if progress_callback:
                progress_callback(f"Found {len(listings)} articles on page {page_num}")
            
            page_listings = []
            for listing in listings:
                try:
                    # Extract title
                    title_elem = listing.find('h2')
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    # Extract price
                    price_elem = listing.find('div', class_='aditem-main--middle--price-shipping')
                    if price_elem:
                        price_p = price_elem.find('p')
                        price = price_p.get_text(strip=True) if price_p else ""
                    else:
                        price = ""
                    
                    # Extract location (PLZ and Ort)
                    location_elem = listing.find('div', class_='aditem-main--top--left')
                    location_text = location_elem.get_text(strip=True) if location_elem else ""
                    
                    # Split PLZ and Ort (format is usually "12345 City Name")
                    plz, ort = "", ""
                    if location_text:
                        parts = location_text.split(' ', 1)
                        if len(parts) >= 1:
                            plz = parts[0] if parts[0].isdigit() else ""
                        if len(parts) >= 2:
                            ort = parts[1]
                    
                    # Extract URL - store for current results but not in database
                    link_elem = listing.find('a', href=True)
                    relative_url = link_elem['href'] if link_elem else ""
                    full_url = urljoin("https://www.kleinanzeigen.de", relative_url) if relative_url else ""
                    
                    # Extract first image
                    image_url = ""
                    image_div = listing.find('div', class_='aditem-image')
                    if image_div:
                        img_elem = image_div.find('img')
                        if img_elem and img_elem.get('src'):
                            image_url = img_elem['src']
                    
                    # Skip if essential data is missing
                    if not title or not full_url:
                        continue
                    
                    # Skip "Gesuch" listings (wanted ads, not offers)
                    gesuch_elem = listing.find('span', class_='simpletag', string=lambda text: text and 'Gesuch' in text.strip())
                    if gesuch_elem:
                        if progress_callback:
                            progress_callback(f"  Skipping Gesuch: {title[:50]}...")
                        continue
                        
                    listing_data = {
                        'keyword': self.keyword,
                        'title': title,
                        'price': price,
                        'plz': plz,
                        'ort': ort,
                        'url': full_url,  # Include URL for current results
                        'image_url': image_url,  # Include first image URL
                        'latitude': None,
                        'longitude': None
                    }
                    
                    page_listings.append(listing_data)
                    if progress_callback:
                        progress_callback(f"  Found: {title[:50]}... | {price} | {plz} {ort}")
                    
                except Exception as e:
                    if progress_callback:
                        progress_callback(f"  Error extracting listing data: {e}")
                    continue
            
            if progress_callback:
                progress_callback(f"  Extracted {len(page_listings)} listings from page {page_num}")
            return page_listings
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error scraping page {page_num}: {e}")
            return []
    


    def scrape_all_pages(self, max_pages=50, progress_callback=None):
        """Scrape all pages up to max_pages"""
        reached_max_pages = False
        
        try:
            # Scrape all pages
            for page_num in range(1, max_pages + 1):
                try:
                    listings = self.scrape_page(page_num, progress_callback)
                    self.all_listings.extend(listings)
                    
                    if len(listings) == 0:
                        print(f"Page {page_num} has no listings - reached end of results")
                        break
                    
                    # Check if we reached the maximum pages
                    if page_num == max_pages:
                        reached_max_pages = True
                    
                except Exception as e:
                    if progress_callback:
                        progress_callback(f"Failed to scrape page {page_num}: {e}")
                    continue
            
            # Final summary
            if progress_callback:
                total_scraped = len(self.all_listings)
                if reached_max_pages:
                    progress_callback(f"Scraping completed! Found {total_scraped} total listings (nur die ersten {max_pages} Seiten durchsucht)")
                else:
                    progress_callback(f"Scraping completed! Found {total_scraped} total listings")
                
            return reached_max_pages
                
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error checking pagination: {e}")
            return False
    
    def save_to_database(self, progress_callback=None):
        """Save all collected listings to the database"""
        if progress_callback:
            progress_callback(f"Saving {len(self.all_listings)} listings to database...")
        
        # Clear existing data for this keyword to ensure fresh results
        try:
            self.session.query(KleinanzeigenListing).filter_by(keyword=self.keyword).delete()
            self.session.commit()
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error clearing existing data: {e}")
            self.session.rollback()
        
        for listing_data in self.all_listings:
            try:
                # Create new listing (no duplicate checking)
                listing = KleinanzeigenListing(
                    keyword=listing_data['keyword'],
                    title=listing_data['title'],
                    price=listing_data['price'],
                    plz=listing_data['plz'],
                    ort=listing_data['ort'],
                    latitude=listing_data['latitude'],
                    longitude=listing_data['longitude']
                )
                
                self.session.add(listing)
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Error saving listing: {e}")
                continue
        
        try:
            self.session.commit()
            if progress_callback:
                progress_callback("Successfully saved all listings to database!")
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error committing to database: {e}")
            self.session.rollback()
    

    
    def get_all_listings(self):
        """Get all listings for the current keyword"""
        return self.session.query(KleinanzeigenListing).filter_by(keyword=self.keyword).all()
    

    
    def close(self):
        """Close database session"""
        self.session.close()

 