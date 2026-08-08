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
    """
    Fetch a URL with caching.
    If cache_key is provided, save the HTML to cache/{cache_key}.html
    Returns HTML content or None on failure.
    """
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

def test_fetch():
    """Test fetch with caching"""
    html = fetch_url("https://books.toscrape.com/catalogue/page-1.html", "catalogue-page-1")
    if html:
        print(f"Response size: {len(html)} bytes")
    else:
        print("Fetch failed")

if __name__ == "__main__":
    test_fetch()