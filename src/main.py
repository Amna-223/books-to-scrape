from pathlib import Path
from time import sleep
from datetime import datetime, timezone
from urllib.parse import urljoin
import json
import time

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, ValidationError


BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = Path("cache")

HEADERS = {
    "User-Agent": (
        "BooksToScrapeAmna/1.0 "
        "(+https://github.com/YOUR-USERNAME/YOUR-REPO)"
    )
}

TIMEOUT = 5
REQUEST_DELAY = 0.5
RETRY_DELAY = 1


class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None
    source_page: HttpUrl
    fetched_at: str


class RunStats:
    def __init__(self):
        self.pages_fetched = 0
        self.cache_hits = 0
        self.failed_pages = 0
        self.invalid_records = 0


stats = RunStats()


def fetch_page(url, cache_file):
    """Fetch a page or read it from cache."""

    if cache_file.exists():
        content = cache_file.read_bytes()

        stats.cache_hits += 1

        print(f"CACHE HIT: {cache_file}")
        print(f"Response size: {len(content)} bytes")

        return content

    print(f"FETCH: {url}")

    for attempt in range(2):

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=TIMEOUT,
            )

        except requests.Timeout:

            if attempt == 0:
                print("Timeout. Retrying once...")
                sleep(RETRY_DELAY)
                continue

            print("Fetch failed: timeout")
            stats.failed_pages += 1
            return None

        except requests.RequestException as error:
            print(f"Fetch failed: {error}")
            stats.failed_pages += 1
            return None

        if response.status_code == 200:
            content = response.content

            cache_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            cache_file.write_bytes(content)

            stats.pages_fetched += 1

            print(f"Response size: {len(content)} bytes")

            return content

        # Retry server errors once.
        if 500 <= response.status_code <= 599:

            if attempt == 0:
                print(
                    f"Server error HTTP {response.status_code}. "
                    "Retrying once..."
                )
                sleep(RETRY_DELAY)
                continue

            print(
                f"Fetch failed: HTTP {response.status_code}"
            )
            stats.failed_pages += 1
            return None

        # Never retry 403 or 404.
        if response.status_code in (403, 404):
            print(
                f"Fetch failed: HTTP {response.status_code}"
            )
            stats.failed_pages += 1
            return None

        # Other HTTP errors.
        print(
            f"Fetch failed: HTTP {response.status_code}"
        )
        stats.failed_pages += 1
        return None

    return None


def extract_book_urls(html, page_url):
    """Extract book URLs from a catalogue page."""

    soup = BeautifulSoup(html, "html.parser")

    book_urls = set()

    for article in soup.select("article.product_pod"):
        link = article.select_one("h3 a")

        if link and link.get("href"):
            absolute_url = urljoin(
                page_url,
                link["href"],
            )

            book_urls.add(absolute_url)

    return book_urls


def find_next_url(html, page_url):
    """Find the next catalogue page."""

    soup = BeautifulSoup(html, "html.parser")

    next_link = soup.select_one("li.next a")

    if next_link and next_link.get("href"):
        return urljoin(
            page_url,
            next_link["href"],
        )

    return None


def discover_catalogue_pages():
    """Discover the first three catalogue pages."""

    current_url = BASE_URL
    book_sources = {}
    catalogue_pages = 0

    while catalogue_pages < 3:

        page_number = catalogue_pages + 1

        cache_file = (
            CACHE_DIR /
            f"catalogue-page-{page_number}.html"
        )

        html = fetch_page(
            current_url,
            cache_file,
        )

        if html is None:
            break

        catalogue_pages += 1

        book_urls = extract_book_urls(
            html,
            current_url,
        )

        for book_url in book_urls:
            book_sources[book_url] = current_url

        next_url = find_next_url(
            html,
            current_url,
        )

        if next_url is None:
            break

        if catalogue_pages < 3:
            sleep(REQUEST_DELAY)

        current_url = next_url

    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(book_sources)}")
    print(f"unique_urls={len(book_sources)}")

    return book_sources


def extract_book_details(
    html,
    product_url,
    source_page,
):
    """Extract a raw record from one book page."""

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    product_main = soup.select_one(
        "article.product_page"
    )

    if product_main is None:
        raise ValueError(
            "Product area not found"
        )

    title_element = product_main.select_one("h1")

    price_element = product_main.select_one(
        ".price_color"
    )

    availability_element = product_main.select_one(
        ".availability"
    )

    rating_element = product_main.select_one(
        "p.star-rating"
    )

    description_element = product_main.select_one(
        "#product_description + p"
    )

    title = (
        title_element.get_text(strip=True)
        if title_element
        else None
    )

    price_text = (
        price_element.get_text(strip=True)
        if price_element
        else None
    )

    availability_text = (
        availability_element.get_text(
            " ",
            strip=True,
        )
        if availability_element
        else None
    )

    rating_text = None

    if rating_element:
        classes = rating_element.get(
            "class",
            [],
        )

        for rating in [
            "One",
            "Two",
            "Three",
            "Four",
            "Five",
        ]:
            if rating in classes:
                rating_text = rating
                break

    description = (
        description_element.get_text(
            " ",
            strip=True,
        )
        if description_element
        else None
    )

    fetched_at = datetime.now(
        timezone.utc
    ).isoformat()

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def scrape_book_details(book_sources):
    """Fetch and extract all discovered book pages."""

    records = []

    for index, (
        product_url,
        source_page,
    ) in enumerate(
        book_sources.items(),
        start=1,
    ):

        cache_file = (
            CACHE_DIR /
            f"book-{index}.html"
        )

        if (
            index > 1
            and not cache_file.exists()
        ):
            sleep(REQUEST_DELAY)

        html = fetch_page(
            product_url,
            cache_file,
        )

        if html is None:
            continue

        try:
            record = extract_book_details(
                html,
                product_url,
                source_page,
            )

        except Exception as error:
            print(
                f"Extraction failed for "
                f"{product_url}: {error}"
            )

            stats.failed_pages += 1
            continue

        records.append(record)

    print(
        f"detail_pages={len(records)}"
    )

    return records


def normalize_price(price_text):
    """Convert '£51.77' into 51.77."""

    if not price_text:
        raise ValueError(
            "Price is missing"
        )

    cleaned = (
        price_text
        .replace("£", "")
        .strip()
    )

    return float(cleaned)


def validate_records(raw_records):
    """Normalize, deduplicate, and validate records."""

    valid_records = []
    errors = []

    seen_urls = set()

    for raw_record in raw_records:

        product_url = raw_record[
            "product_url"
        ]

        if product_url in seen_urls:
            continue

        seen_urls.add(product_url)

        try:
            normalized_record = {
                **raw_record,
                "price_gbp": normalize_price(
                    raw_record[
                        "price_text"
                    ]
                ),
            }

            book = BookRecord.model_validate(
                normalized_record
            )

            valid_records.append(
                book.model_dump(
                    mode="json"
                )
            )

        except (
            ValueError,
            ValidationError,
        ) as error:

            stats.invalid_records += 1

            errors.append(
                {
                    "product_url": product_url,
                    "reason": str(error),
                }
            )

    return valid_records, errors


def save_json(data, file_path):
    """Save data as formatted JSON."""

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with file_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def save_run_report(
    start_time,
    duration,
    valid_records,
):
    """Save the final run report."""

    report = {
        "start_time": start_time,
        "duration_seconds": round(
            duration,
            2,
        ),
        "pages_fetched": stats.pages_fetched,
        "cache_hits": stats.cache_hits,
        "valid_records": len(
            valid_records
        ),
        "invalid_records": (
            stats.invalid_records
        ),
        "failed_pages": (
            stats.failed_pages
        ),
    }

    save_json(
        report,
        Path("output/run-report.json"),
    )

    print("\nRun report:")
    print(json.dumps(
        report,
        indent=2,
    ))


if __name__ == "__main__":

    start_timestamp = datetime.now(
        timezone.utc
    )

    start_time = time.perf_counter()

    book_sources = (
        discover_catalogue_pages()
    )

    # -------------------------------------------------
    # FAILURE TEST
    # Add ONE fake URL on purpose.
    # Remove this after verifying Stage 5.
    # -------------------------------------------------

    book_sources[
        "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html"
    ] = BASE_URL

    raw_records = scrape_book_details(
        book_sources
    )

    valid_records, errors = (
        validate_records(
            raw_records
        )
    )

    save_json(
        valid_records,
        Path("output/books.json"),
    )

    save_json(
        errors,
        Path("output/errors.json"),
    )

    duration = (
        time.perf_counter()
        - start_time
    )

    save_run_report(
        start_timestamp.isoformat(),
        duration,
        valid_records,
    )