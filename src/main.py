from pathlib import Path
import requests


URL = "https://books.toscrape.com/"
CACHE_FILE = Path("cache/catalogue-page-1.html")

HEADERS = {
    "User-Agent": (
        "BooksToScrapeAmna/1.0 "
        "(+https://github.com/Amna-223/books-to-scrape)"
    )
}

TIMEOUT = 5


def fetch_and_cache():
    # Use the cached HTML if it already exists.
    if CACHE_FILE.exists():
        content = CACHE_FILE.read_bytes()
        print("CACHE HIT")
        print(f"Response size: {len(content)} bytes")
        return

    print("FETCH")

    try:
        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
    except requests.RequestException as error:
        print(f"Fetch failed: {error}")
        return

    if response.status_code != 200:
        print(f"Fetch failed: HTTP {response.status_code}")
        return

    content = response.content

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_bytes(content)
    print(f"Response size: {len(content)} bytes")


if __name__ == "__main__":
    fetch_and_cache()