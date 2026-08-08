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

# ----- Pydantic Schema -----
class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float = Field(ge=0)
    availability_text: str
    rating_text: Optional[str] = None
    description: Optional[str] = None
    source_page: HttpUrl
    fetched_at: str

def clean_price(price_text: str) -> Optional[float]:
    if not price_text:
        return None
    try:
        cleaned = price_text.replace("£", "").replace("Â", "").strip()
        return float(cleaned)
    except ValueError:
        return None

def fetch_url(url: str, cache_key: str = None) -> Optional[str]:
    """Fetch a URL with caching and retries for certain errors."""
    if cache_key:
        cache_file = f"cache/{cache_key}.html"
        if os.path.exists(cache_file):
            print(f"CACHE HIT: {url}")
            return open(cache_file, "r", encoding="utf-8").read()
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            print(f"FETCH: {url} (attempt {attempt + 1})")
            response = requests.get(
                url,
                timeout=TIMEOUT,
                headers={"User-Agent": USER_AGENT}
            )
            
            if response.status_code == 404:
                print(f"ERROR 404: {url} (page not found)")
                return None
            if response.status_code == 403:
                print(f"ERROR 403: {url} (forbidden)")
                return None
            if response.status_code >= 500:
                print(f"ERROR {response.status_code}: {url} (server error)")
                if attempt < MAX_RETRIES:
                    wait = (2 ** attempt)  # Exponential backoff: 1s, 2s
                    print(f"  Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                return None
            
            response.raise_for_status()
            
            if cache_key:
                with open(f"cache/{cache_key}.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
            
            return response.text
        except requests.exceptions.Timeout:
            print(f"TIMEOUT: {url}")
            if attempt < MAX_RETRIES:
                wait = 2 ** attempt
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
                continue
            return None
        except requests.exceptions.RequestException as e:
            print(f"ERROR fetching {url}: {e}")
            return None
    
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
    """Main processing function with error handling and reporting."""
    start_time = datetime.datetime.now()
    cache_hits = 0  # Track cache hits (you can increment inside fetch_url if you modify it)
    
    # Discover books
    book_urls = discover_books()
    good_records = []
    error_records = []
    failed_pages = 0
    
    # Add one fake URL for testing (if you want to test failure handling)
    book_urls.append("https://books.toscrape.com/fake-book.html")
    
    for i, url in enumerate(book_urls):
        print(f"\nProcessing {i+1}/{len(book_urls)}: {url}")
        
        try:
            # Extract raw data
            raw = extract_book_details(url, "https://books.toscrape.com/catalogue/page-1.html")
            if raw is None:
                failed_pages += 1
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
            
            # Validate with schema
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
        except Exception as e:
            # Catch any unexpected error
            failed_pages += 1
            error_records.append({
                "url": url,
                "error": f"Unexpected error: {e}"
            })
        
        # Delay between requests
        if i < len(book_urls) - 1:
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
        "duration_seconds": round(duration, 2),
        "total_book_urls": len(book_urls),
        "valid_records": len(good_records),
        "invalid_records": len(error_records),
        "failed_pages": failed_pages,
        "cache_hits": 0,  # You can increment this
    }
    
    with open("output/run-report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✓ Complete!")
    print(f"  Valid records: {len(good_records)}")
    print(f"  Invalid records: {len(error_records)}")
    print(f"  Failed pages: {failed_pages}")
    print(f"  Duration: {duration:.1f} seconds")
    print(f"{'='*50}")

if __name__ == "__main__":
    process_books()