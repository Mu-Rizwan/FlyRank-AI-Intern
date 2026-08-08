# Polite Scraper – Books to Scrape

A repeatable, ethical web scraping pipeline that extracts book data from the public sandbox [Books to Scrape](https://books.toscrape.com/). It fetches the first 3 catalogue pages (60 books), cleans and validates the data, handles failures gracefully, and produces a detailed run report.

This project was built as part of the **FlyRank AI Backend Internship – Week 5** assignment.

---

## 🎯 Target Classification

| Item | Details |
|------|---------|
| **Target site** | [https://books.toscrape.com/](https://books.toscrape.com/) |
| **Why this site** | A public sandbox explicitly built for practising web scraping. The site's homepage states: *"Welcome to Books to Scrape! This is a sandbox website for practising web scraping."* |
| **Scope** | First 3 catalogue pages only (60 books total) |
| **Data collected** | Title, product URL, price, availability, rating, description, source page, fetch timestamp |
| **Robots.txt** | `https://books.toscrape.com/robots.txt` – Checked and respected. No disallow rules for the catalogue pages being accessed. |

**Ethics statement:** I will not reuse this code on another site without first checking its `robots.txt`, terms of service, and applicable laws. I will not bypass logins, paywalls, or rate limits. I collect only what I need and respect the site's resources.

---

## 🛠️ Tech Stack

- **Python** 3.10+
- **Requests** – HTTP client with timeout and custom user-agent
- **Beautiful Soup 4** – HTML parsing and element selection
- **Pydantic** – Schema validation and type safety
- **JSON** – Output format for records and reports
- **Git** – Version control

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo/W5-A5-Polite-Scraper
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate          # On Linux/Mac
# or
venv\Scripts\activate              # On Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Running the Scraper

```bash
cd src
python main.py
```

The script will:
1. Check for cached HTML files (if they exist, use them).
2. Fetch the first 3 catalogue pages (if not cached).
3. Extract all 60 book URLs.
4. Fetch and extract details for each book (with 500ms delay between requests).
5. Validate every record against the schema.
6. Write outputs to the `output/` folder.

---

## 📁 Output Files

After a successful run, you'll find three files in the `output/` directory:

| File | Description |
|------|-------------|
| `books.json` | 60 validated records (if all succeeded). |
| `errors.json` | Records that failed validation, with error reasons. |
| `run-report.json` | Summary statistics about the run. |

---

## 📋 Record Schema

Each book record follows this structure:

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_text": "£51.77",
  "price_gbp": 51.77,
  "availability_text": "In stock (22 available)",
  "rating_text": "Three",
  "description": "Some description text...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-08-03T10:00:00Z"
}
```

**Schema details:**
- `title` – Book title (string, required)
- `product_url` – Absolute URL of the book page (valid HTTP URL)
- `price_text` – Raw price as displayed on the page (string)
- `price_gbp` – Numeric price in GBP (float ≥ 0)
- `availability_text` – Stock status text (string)
- `rating_text` – Star rating (One to Five, optional)
- `description` – Book description (optional, null if missing)
- `source_page` – Catalogue page where the book was found (valid HTTP URL)
- `fetched_at` – ISO-8601 timestamp of fetch (string)

---

## 🧹 Politeness Rules

The scraper follows these rules to be a good web citizen:

| Rule | Implementation |
|------|----------------|
| **User‑Agent** | `FlyRankInternship-A9/1.0 (+https://github.com/your-username/your-repo)` – identifies the scraper and provides a contact point. |
| **Delay** | 500ms (0.5 seconds) between real requests to the live site. |
| **Timeout** | 10 seconds – a request that doesn't respond within 10 seconds is abandoned. |
| **Cache** | All fetched HTML is saved to `cache/`. Subsequent runs read from the cache instead of hitting the live site. |
| **Retries** | Failed requests (5xx errors or timeouts) are retried once with exponential backoff (1s, then 2s). 404 and 403 errors are not retried. |
| **Robots.txt** | Checked and respected. |

---

## 📊 Sample Run Report

After a successful run, `output/run-report.json` looks like this:

```json
{
  "start_time": "2026-08-03T10:00:00",
  "duration_seconds": 45.23,
  "total_book_urls": 60,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0,
  "cache_hits": 0
}
```

**What the numbers mean:**
- `total_book_urls` – Number of unique book URLs discovered.
- `valid_records` – Records that passed schema validation.
- `invalid_records` – Records that failed validation (saved in `errors.json` with reasons).
- `failed_pages` – Pages that could not be fetched (network/timeout/server errors).
- `cache_hits` – Number of requests served from the cache (development runs).

---

## 🧪 Handling Failures

The scraper is designed to survive failures:

- **One bad page does not crash the run.** If a book page fails to load or fails validation, it is logged in `errors.json` and the scraper continues.
- **A fake/broken URL** (e.g., `/fake-book.html`) is captured as a failed page and reported in `run-report.json` without halting the run.
- **Validation errors** (e.g., missing title, invalid price) produce an error record with the raw data and the reason.

---

## 🤔 Why No Browser?

This scraper uses plain HTTP requests (`requests` library) and parses the HTML with Beautiful Soup. It does **not** use a headless browser (like Playwright or Selenium) because:

- The data is already present in the HTML the server sends – no JavaScript rendering is required.
- A browser would add significant memory, CPU, and time overhead.
- For static websites like Books to Scrape, a browser is overkill and wasteful.

This approach is faster, cheaper, and more resource-efficient.

---

## 📝 Limitations

- Only scrapes the **first 3 catalogue pages** (60 books), as scoped by the assignment.
- Designed specifically for the **Books to Scrape** sandbox – not for production use on other sites.
- Does not handle pagination beyond page 3 (by design).
- Descriptions may be `null` for books that have no description on their page.

---

## 🔐 Ethics Note

> *"With great power comes great responsibility."*

- Always check a site's `robots.txt` and terms of service before scraping.
- Use an official API when one exists – it's more stable and respectful.
- Never bypass logins, paywalls, or access controls.
- Collect only the data you need – nothing more.
- Rate-limit your requests – a website is not a punching bag.
- Identify yourself with a clear user-agent so site owners can contact you.
- Never reuse this scraper on another site without first confirming its rules.

---

## 📂 Project Structure

```
W5-A5-Polite-Scraper/
├── src/
│   └── main.py              # Main scraper logic
├── cache/                   # Cached HTML files (git-ignored)
├── output/                  # Output files (git-ignored)
│   ├── books.json
│   ├── errors.json
│   └── run-report.json
├── requirements.txt         # Python dependencies
├── .gitignore               # Ignored files and folders
└── README.md                # This documentation
```

---

## 📦 Dependencies (`requirements.txt`)

```
requests==2.32.5
beautifulsoup4==4.14.3
pydantic==2.12.4
python-dotenv==1.2.2
```

---

## 👤 Author

**Muhammad Rizwan** – FlyRank AI Intern, Backend Track

---

## 📬 Submission

This repository is **public** and contains **7+ meaningful commits** (one per stage).  
A reviewer can clone, install dependencies, and run the scraper in under 5 minutes using the instructions above.

---

## 📄 License

This project is built for educational purposes as part of the FlyRank Internship program.

---