# Books to Scrape — Polite Web Scraper

A small Python scraping pipeline built for the FlyRank internship assignment.

The scraper discovers books from the first three catalogue pages of
[Books to Scrape](https://books.toscrape.com/), visits each individual book
page, extracts and cleans the required fields, validates every record,
stores valid records as JSON, and reports what happened during the run.

**Pipeline:** `fetch → extract → normalize → validate → store → report`

---

## Table of Contents

- [Target Site](#target-site)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Output](#output)
- [Record Schema](#record-schema)
- [Pipeline Details](#pipeline-details)
- [Politeness Rules](#politeness-rules)
- [Error Handling](#error-handling)
- [Project Structure](#project-structure)
- [Ethics](#ethics)
- [Limitations](#limitations)

---

## Target Site

| Field | Detail |
|---|---|
| Site | [Books to Scrape](https://books.toscrape.com/) |
| Scope | First 3 catalogue pages (60 books) |
| `robots.txt` | Returned `404 Not Found` — treated as no permission granted |

**Why this site:** Books to Scrape is a sandbox explicitly designed for practising web scraping.

**Data collected per book:**

- Title
- Product URL
- Original price text + normalized price in GBP
- Availability
- Rating
- Description
- Source catalogue page
- Fetch timestamp

---

## Requirements

- Python 3.10+
- `requests`
- `beautifulsoup4`
- `pydantic`

---

## Installation

```bash
git clone https://github.com/Amna-223/books-to-scrape.git
cd books-to-scrape
pip install -r requirements.txt
```

---

## Usage

```bash
python scraper.py
```

Cached HTML pages are stored in `src/cache/` and are excluded from Git via `.gitignore`.

---

## Output

After a successful run, the `output/` directory contains:

```
output/
├── books.json        # 60 valid scraped book records
├── errors.json       # Invalid or failed records with reasons
└── run-report.json   # Run summary (timing, fetches, cache hits, counts)
```

A normal successful run produces **60 unique valid records**.

---

## Record Schema

| Field | Type | Description |
|---|---|---|
| `title` | `string` | Book title |
| `product_url` | `URL` | Absolute canonical product URL |
| `price_text` | `string` | Original price text (e.g. `£51.77`) |
| `price_gbp` | `number` | Normalized price in GBP (e.g. `51.77`) |
| `availability_text` | `string` | Original availability text |
| `rating_text` | `string` | Book rating |
| `description` | `string \| null` | Product description, or `null` if not available |
| `source_page` | `URL` | Catalogue page where the book was discovered |
| `fetched_at` | `string` | ISO timestamp of when the page was fetched |

---

## Pipeline Details

### Fetch
Requests catalogue and book pages using a descriptive `User-Agent`, a 5-second timeout, and a delay between real requests. Only HTTP 200 responses are accepted.

### Cache
Successfully fetched HTML is saved to `src/cache/` and reused on subsequent runs, avoiding unnecessary requests during development.

### Extract
Beautiful Soup extracts fields from each book's product page. The scraper follows the catalogue's own `next` link to discover pages — no URLs are hardcoded.

### Normalize
Original price text is preserved and the numeric value is extracted:

```
£51.77  →  price_text: "£51.77"  |  price_gbp: 51.77
```

### Validate
Every record is validated with Pydantic before storage. Failed records go to `output/errors.json` along with the failure reason.

### Store
Valid records are written to `output/books.json`. The `product_url` is used as the canonical identity — duplicates are never stored twice.

### Report
Every run produces `output/run-report.json` recording: start time, duration, total fetches, cache hits, valid records, invalid records, and failed pages.

---

## Politeness Rules

- Descriptive `User-Agent` on every request
- Minimum **0.5 s** delay between real (non-cached) requests
- 5-second request timeout
- Caches successfully fetched HTML; reuses cache during development
- Retries a timeout **once**
- Retries HTTP `5xx` errors **once**
- Does **not** retry `403` or `404` responses
- Processes only the **first 3 catalogue pages**
- Deduplicates product URLs before processing

---

## Error Handling

Each book page is handled independently. A timeout, server error, extraction failure, or validation failure on one page is recorded and the scraper continues with the rest.

A failure test was run using an intentionally fake URL — the scraper completed normally and valid records were unaffected.

---

## Project Structure

```
books-to-scrape/
│
├── src/
│   └── cache/              # Local HTML cache (Git-ignored)
│
├── output/
│   ├── books.json          # Valid scraped records
│   ├── errors.json         # Invalid/failed records
│   └── run-report.json     # Run summary
│
├── scraper.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Ethics

- No logins, paywalls, or access blocks are bypassed
- Only the data needed for the assignment is collected
- When an official API exists, it should be preferred over scraping

---

## Limitations

- Intentionally scoped to the **first 3 catalogue pages** — not a full site crawl
- Depends on the current HTML structure of Books to Scrape; changes to CSS selectors or page layout may require updates to the extractor
- No browser automation needed — all required data is present in server-rendered HTML