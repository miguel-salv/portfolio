# pip install requests beautifulsoup4

import os
from collections import deque
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Comment

# ─── Configuration ────────────────────────────────────────────────────────────

BASE_URL = "https://miguelsalv.framer.website/"
OUTPUT_DIR = "."

# ─── Globals ──────────────────────────────────────────────────────────────────

session = requests.Session()
session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
    }
)

visited_urls: set[str] = set()
stats = {"pages": 0}
base_netloc = urlparse(BASE_URL).netloc

# ─── Helpers ──────────────────────────────────────────────────────────────────


def is_same_origin(url: str) -> bool:
    parsed = urlparse(url)
    if not parsed.netloc:
        return True
    return parsed.netloc == base_netloc


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))


def url_to_filepath(url: str) -> str:
    """Map a page URL to its local file path inside OUTPUT_DIR.

    /              -> index.html
    /about         -> about.html
    /projects/foo  -> projects/foo.html
    """
    path = urlparse(url).path.strip("/")
    if not path:
        return os.path.join(OUTPUT_DIR, "index.html")
    if path.endswith(".html"):
        return os.path.join(OUTPUT_DIR, path)
    return os.path.join(OUTPUT_DIR, path + ".html")


# ─── HTML processing ─────────────────────────────────────────────────────────


def process_page(url: str, html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    page_filepath = url_to_filepath(url)
    page_dir = os.path.dirname(page_filepath)
    os.makedirs(page_dir, exist_ok=True)

    # ── Strip Framer branding ────────────────────────────────────────────
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        if "framer.com" in comment.lower() or "made in framer" in comment.lower():
            comment.extract()

    badge = soup.find(id="__framer-badge-container")
    if badge:
        badge.decompose()

    for tag in list(soup.find_all(["div", "a"])):
        if tag.attrs is None:
            continue
        text = tag.get_text(strip=True).lower()
        href = (tag.get("href") or "").lower()
        if "made with" in text or "framer.com" in href:
            tag.decompose()

    gen = soup.find("meta", attrs={"name": "generator"})
    if gen and "framer" in (gen.get("content") or "").lower():
        gen.decompose()

    for script in list(soup.find_all("script")):
        if script.string and "__framer_force" in script.string:
            script.decompose()

    for meta in list(soup.find_all("meta")):
        name = (meta.get("name") or "").lower()
        if name.startswith("framer-"):
            meta.decompose()

    for tag in soup.find_all(True):
        if tag.attrs is None:
            continue
        to_remove = [attr for attr in tag.attrs if attr.startswith("data-framer")]
        for attr in to_remove:
            del tag[attr]

    # ── Save HTML ─────────────────────────────────────────────────────────
    with open(page_filepath, "w", encoding="utf-8") as f:
        f.write(str(soup))
    stats["pages"] += 1
    print(f"  ✓ Saved {page_filepath}")


# ─── Crawler ──────────────────────────────────────────────────────────────────


def crawl() -> None:
    queue: deque[str] = deque([BASE_URL])
    visited_urls.add(normalize_url(BASE_URL))

    while queue:
        url = queue.popleft()
        print(f"Crawling: {url}")

        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  ⚠ Failed to fetch {url}: {exc}")
            continue

        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            continue

        process_page(url, resp.text)

        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            abs_href = urljoin(url, href)
            abs_href = normalize_url(abs_href)

            if not is_same_origin(abs_href):
                continue

            parsed = urlparse(abs_href)
            if parsed.scheme not in ("http", "https", ""):
                continue

            if abs_href not in visited_urls:
                visited_urls.add(abs_href)
                queue.append(abs_href)


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    print(f"Scraping {BASE_URL} → ./\n")
    crawl()

    import shutil
    shutil.copy2("index.html", "404.html")
    print("  ✓ Copied index.html → 404.html")

    print("\n--- Summary ---")
    print(f"Pages saved: {stats['pages']}")


if __name__ == "__main__":
    main()
