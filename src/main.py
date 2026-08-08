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
def check_robots():
    try:
        response = requests.get(
            "https://books.toscrape.com/robots.txt",
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        print(f"Robots.txt status: {response.status_code}")
        print(response.text[:500])
    except Exception as e:
        print(f"Error checking robots.txt: {e}")

if __name__ == "__main__":
    check_robots()