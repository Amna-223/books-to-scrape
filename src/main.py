from pathlib import Path
from time import sleep
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = Path("cache")

HEADERS = {
    "User-Agent": (
        "BooksToScrapeAmna/1.0 "
        "(+https://github.com/Amna-223/books-to/scrape)"
    )
}

TIMEOUT = 5
REQUEST_DELAY = 0.5


def fetch_page(url, cache_file):
    """Fetch a page or read it from cache."""

    if cache_file.exists():
        content = cache_file.read_bytes()

        print(f"CACHE HIT: {cache_file}")
        print(f"Response size: {len(content)} bytes")

        return content

    print(f"FETCH: {url}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
    except requests.RequestException as error:
        print(f"Fetch failed: {error}")
        return None

    if response.status_code != 200:
        print(f"Fetch failed: HTTP {response.status_code}")
        return None

    content = response.content

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(content)

    print(f"Response size: {len(content)} bytes")

    return content


def extract_book_urls(html, page_url):
    """Extract book URLs from a catalogue page."""

    soup = BeautifulSoup(html, "html.parser")

    book_urls = set()

    for article in soup.select("article.product_pod"):
        link = article.select_one("h3 a")

        if link and link.get("href"):
            absolute_url = urljoin(page_url, link["href"])
            book_urls.add(absolute_url)

    return book_urls


def find_next_url(html, page_url):
    """Find the next catalogue page."""

    soup = BeautifulSoup(html, "html.parser")

    next_link = soup.select_one("li.next a")

    if next_link and next_link.get("href"):
        return urljoin(page_url, next_link["href"])

    return None


def discover_catalogue_pages():
    """
    Discover the first three catalogue pages and keep
    each book URL associated with its source catalogue page.
    """

    current_url = BASE_URL
    book_sources = {}
    catalogue_pages = 0

    while catalogue_pages < 3:
        page_number = catalogue_pages + 1

        cache_file = CACHE_DIR / f"catalogue-page-{page_number}.html"

        html = fetch_page(current_url, cache_file)

        if html is None:
            break

        catalogue_pages += 1

        book_urls = extract_book_urls(html, current_url)

        for book_url in book_urls:
            book_sources[book_url] = current_url

        next_url = find_next_url(html, current_url)

        if next_url is None:
            break

        if catalogue_pages < 3:
            sleep(REQUEST_DELAY)

        current_url = next_url

    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={sum(1 for _ in book_sources)}")
    print(f"unique_urls={len(book_sources)}")

    return book_sources


def extract_book_details(html, product_url, source_page):
    """Extract a raw record from one book page."""

    soup = BeautifulSoup(html, "html.parser")

    product_main = soup.select_one("article.product_page")

    if product_main is None:
        raise ValueError("Product area not found")

    title_element = product_main.select_one("h1")

    price_element = product_main.select_one(".price_color")

    availability_element = product_main.select_one(
        ".availability"
    )

    rating_element = product_main.select_one(
        "p.star-rating"
    )

    description_element = product_main.select_one(
        "#product_description + p"
    )

    title = title_element.get_text(strip=True) if title_element else None

    price_text = (
        price_element.get_text(strip=True)
        if price_element
        else None
    )

    availability_text = (
        availability_element.get_text(" ", strip=True)
        if availability_element
        else None
    )

    rating_text = None

    if rating_element:
        classes = rating_element.get("class", [])

        for rating in ["One", "Two", "Three", "Four", "Five"]:
            if rating in classes:
                rating_text = rating
                break

    description = (
        description_element.get_text(" ", strip=True)
        if description_element
        else None
    )

    fetched_at = datetime.now(timezone.utc).isoformat()

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

    for index, (product_url, source_page) in enumerate(
        book_sources.items(),
        start=1
    ):
        cache_file = CACHE_DIR / f"book-{index}.html"

        if index > 1 and not cache_file.exists():
            sleep(REQUEST_DELAY)

        html = fetch_page(product_url, cache_file)

        if html is None:
            continue

        try:
            record = extract_book_details(
                html,
                product_url,
                source_page,
            )
        except Exception as error:
            print(f"Extraction failed: {error}")
            continue

        records.append(record)

    print(f"detail_pages={len(records)}")

    return records


if __name__ == "__main__":
    book_sources = discover_catalogue_pages()

    records = scrape_book_details(book_sources)

    if records:
        print("\nFirst raw record:")
        print(records[0])