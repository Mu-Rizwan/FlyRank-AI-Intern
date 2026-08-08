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

# ----- Pydantic Schema for validated records -----
class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float = Field(ge=0)  # Cleaned price
    availability_text: str
    rating_text: Optional[str] = None
    description: Optional[str] = None
    source_page: HttpUrl
    fetched_at: str  # ISO format timestamp

def clean_price(price_text: str) -> Optional[float]:
    """Convert '£51.77' to 51.77"""
    if not price_text:
        return None
    try:
        # Remove currency symbol and any spaces
        cleaned = price_text.replace("£", "").replace("Â", "").strip()
        return float(cleaned)
    except ValueError:
        return None

def normalize_url(base: str, relative: str) -> str:
    """Convert relative URL to absolute using urljoin"""
    return urljoin(base, relative)

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
    
    print(f"catalogue_pages={pages_discovered}, discovered={len(book_urls)}")
    return list(book_urls)

def extract_book_details(url: str, source_page: str) -> Dict[str, Any]:
    """Extract all fields from a book detail page."""
    parsed = urlparse(url)
    path_parts = parsed.path.split("/")
    cache_key = path_parts[-2] if len(path_parts) >= 2 else f"book_{hash(url)}"
    
    html = fetch_url(url, cache_key)
    if html is None:
        return None
    
    soup = BeautifulSoup(html, "html.parser")
    
    title_elem = soup.select_one("h1")
    title = title_elem.text.strip() if title_elem else None
    
    price_elem = soup.select_one("p.price_color")
    price_text = price_elem.text.strip() if price_elem else None
    
    avail_elem = soup.select_one("p.instock.availability")
    availability_text = avail_elem.text.strip() if avail_elem else None
    
    rating_elem = soup.select_one("p.star-rating")
    rating = None
    if rating_elem:
        for cls in rating_elem.get("class", []):
            if cls in ["One", "Two", "Three", "Four", "Five"]:
                rating = cls
                break
    
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

def process_books():
    """Main processing function"""
    start_time = datetime.datetime.now()
    
    # Discover books
    book_urls = discover_books()
    good_records = []
    error_records = []
    
    for i, url in enumerate(book_urls):
        print(f"Processing {i+1}/{len(book_urls)}: {url}")
        
        # Extract raw data
        raw = extract_book_details(url, "https://books.toscrape.com/catalogue/page-1.html")
        if raw is None:
            error_records.append({
                "url": url,
                "error": "Failed to fetch page"
            })
            continue
        
        # Clean price
        price_gbp = clean_price(raw.get("price_text"))
        if price_gbp is None:
            error_records.append({
                "url": url,
                "error": "Invalid price format",
                "raw": raw
            })
            continue
        
        # Prepare validated record
        try:
            record = BookRecord(
                title=raw["title"],
                product_url=raw["product_url"],
                price_text=raw["price_text"],
                price_gbp=price_gbp,
                availability_text=raw["availability_text"],
                rating_text=raw.get("rating_text"),
                description=raw.get("description"),
                source_page=raw["source_page"],
                fetched_at=raw["fetched_at"]
            )
            good_records.append(record.model_dump(mode='json'))
        except ValidationError as e:
            error_records.append({
                "url": url,
                "error": str(e),
                "raw": raw
            })
        
        time.sleep(DELAY)
    
    # Write outputs
    with open("output/books.json", "w", encoding="utf-8") as f:
        json.dump(good_records, f, indent=2)
    
    with open("output/errors.json", "w", encoding="utf-8") as f:
        json.dump(error_records, f, indent=2)
    
    # Run report
    duration = (datetime.datetime.now() - start_time).total_seconds()
    report = {
        "start_time": start_time.isoformat(),
        "duration_seconds": duration,
        "total_book_urls": len(book_urls),
        "valid_records": len(good_records),
        "invalid_records": len(error_records),
        "cache_hits": 0,  # Track this if you want
        "failed_pages": len([e for e in error_records if "Failed to fetch" in str(e)]),
    }
    
    with open("output/run-report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Complete! {len(good_records)} valid records, {len(error_records)} errors")
    print(f"  Duration: {duration:.1f} seconds")

if __name__ == "__main__":
    process_books()