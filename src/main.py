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

# to check robots.txt
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
    """
    Discover all book URLs from the first 3 catalogue pages.
    Returns a list of absolute URLs.
    """
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
        
        # Find all book links on the page
        # Books are inside <article class="product_pod"> with an <a> link
        for article in soup.select("article.product_pod"):
            link = article.find("a")
            if link and link.get("href"):
                # Make absolute URL
                book_url = urljoin(current_page_url, link["href"])
                book_urls.add(book_url)
        
        # Find the "next" link
        next_link = soup.find("a", string="next")
        if next_link and next_link.get("href"):
            current_page_url = urljoin(current_page_url, next_link["href"])
            pages_discovered += 1
            if pages_discovered < MAX_PAGES:
                # Wait before next request
                time.sleep(DELAY)
        else:
            break
    
    print(f"catalogue_pages={pages_discovered}, discovered={len(book_urls)}")
    return list(book_urls)

def test_discovery():
    urls = discover_books()
    print(f"Unique URLs: {len(urls)}")
    if len(urls) == 60:
        print("✓ Found all 60 books")
    else:
        print(f"⚠ Expected 60, got {len(urls)}")

if __name__ == "__main__":
    test_discovery()