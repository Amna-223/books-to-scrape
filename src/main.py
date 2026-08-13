from pathlib import Path
from time import sleep
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/"
CACHE_DIR = Path("cache")

HEADERS = {
    "User-Agent": (
        "BooksToScrapeAmna/1.0 "
        "(+https://github.com/Amna-223/books-to-scrape)"
    )
}

TIMEOUT = 5
REQUEST_DELAY = 0.5


def fetch_page(url, cache_file):
    """
    Return the HTML for a page.

    If the page is already cached, read it from disk.
    Otherwise fetch it from the website and cache it.
    """

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
    """Extract and normalize all book URLs from a catalogue page."""

    soup = BeautifulSoup(html, "html.parser")

    book_urls = set()

    for article in soup.select("article.product_pod"):
        link = article.select_one("h3 a")

        if link and link.get("href"):
            absolute_url = urljoin(page_url, link["href"])
            book_urls.add(absolute_url)

    return book_urls


def find_next_url(html, page_url):
    """Find the catalogue's next-page URL."""

    soup = BeautifulSoup(html, "html.parser")

    next_link = soup.select_one("li.next a")

    if next_link and next_link.get("href"):
        return urljoin(page_url, next_link["href"])

    return None


def discover_catalogue_pages():
    current_url = BASE_URL
    discovered_urls = set()
    catalogue_pages = 0

    while catalogue_pages < 3:
        page_number = catalogue_pages + 1

        cache_file = CACHE_DIR / f"catalogue-page-{page_number}.html"

        html = fetch_page(current_url, cache_file)

        if html is None:
            break

        catalogue_pages += 1

        book_urls = extract_book_urls(html, current_url)
        discovered_urls.update(book_urls)

        next_url = find_next_url(html, current_url)

        if next_url is None:
            break

        if catalogue_pages < 3:
            sleep(REQUEST_DELAY)

        current_url = next_url

    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(discovered_urls)}")
    print(f"unique_urls={len(discovered_urls)}")

    return discovered_urls


if __name__ == "__main__":
    discover_catalogue_pages()