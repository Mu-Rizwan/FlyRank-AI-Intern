import os
import sys
import json
import time
import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError, HttpUrl, Field
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
BASE_URL = "https://books.toscrape.com/"
USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/your-username/your-repo)"
TIMEOUT = 10  # seconds
DELAY = 0.5   # seconds between requests
MAX_PAGES = 3

# Create directories if they don't exist
os.makedirs("cache", exist_ok=True)
os.makedirs("output", exist_ok=True)

def fetch_url(url: str, cache_key: str = None) -> Optional[str]:
    """Fetch a URL with caching."""
    if cache_key:
        cache_file = f"cache/{cache_key}.html"
        if os.path.exists(cache_file):
            print(f"CACHE HIT: {url}")
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()
    
    try:
        print(f"FETCH: {url}")
        response = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()
        
        if cache_key:
            with open(f"cache/{cache_key}.html", "w", encoding="utf-8") as f:
                f.write(response.text)
        
        return response.text
    except requests.exceptions.Timeout:
        print(f"TIMEOUT: {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching {url}: {e}")
        return None

def discover_books() -> List[str]:
    """Discover all book URLs from the first 3 catalogue pages."""
    book_urls: Set[str] = set()
    current_page_url = urljoin(BASE_URL, "catalogue/page-1.html")
    pages_discovered = 0
    
    while pages_discovered < MAX_PAGES:
        cache_key = f"catalogue-page-{pages_discovered + 1}"
        html = fetch_url(current_page_url, cache_key)
        
        if html is None:
            print(f"Failed to fetch {current_page_url}")
            break
        
        soup = BeautifulSoup(html, "html.parser")
        
        for article in soup.select("article.product_pod"):
            link = article.find("a")
            if link and link.get("href"):
                book_url = urljoin(current_page_url, link["href"])
                book_urls.add(book_url)
        
        next_link = soup.find("a", string="next")
        if next_link and next_link.get("href"):
            current_page_url = urljoin(current_page_url, next_link["href"])
            pages_discovered += 1
            if pages_discovered < MAX_PAGES:
                time.sleep(DELAY)
        else:
            break
    return list(book_urls)

def extract_book_details(url: str, source_page: str) -> Dict[str, Any]:
    """
    Extract all fields from a book detail page.
    Returns a dict with the raw data.
    """
    # Generate cache key from URL
    parsed = urlparse(url)
    path_parts = parsed.path.split("/")
    cache_key = path_parts[-2] if len(path_parts) >= 2 else f"book_{hash(url)}"
    
    html = fetch_url(url, cache_key)
    if html is None:
        return None
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Title - from h1
    title_elem = soup.select_one("h1")
    title = title_elem.text.strip() if title_elem else None
    
    # Price - from p.price_color
    price_elem = soup.select_one("p.price_color")
    price_text = price_elem.text.strip() if price_elem else None
    
    # Availability - from p.instock.availability
    avail_elem = soup.select_one("p.instock.availability")
    availability_text = avail_elem.text.strip() if avail_elem else None
    
    # Rating - from p.star-rating
    rating_elem = soup.select_one("p.star-rating")
    rating = None
    if rating_elem:
        for cls in rating_elem.get("class", []):
            if cls in ["One", "Two", "Three", "Four", "Five"]:
                rating = cls
                break
    
    # Description - from product_page > p
    desc_elem = soup.select_one("div.product_page p")
    description = desc_elem.text.strip() if desc_elem else None
    
    return {
        "title": title,
        "product_url": url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

def test_extraction():
    """Extract one book to verify"""
    books = discover_books()
    if books:
        sample = books[0]
        print(f"Extracting: {sample}")
        record = extract_book_details(sample, "https://books.toscrape.com/catalogue/page-1.html")
        if record:
            print(json.dumps(record, indent=2))
        else:
            print("Extraction failed")

if __name__ == "__main__":
    test_extraction()