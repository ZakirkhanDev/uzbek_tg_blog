"""Real football photo finder.

Uses Wikimedia Commons' public API (no API key required) to find reusable
football imagery. It deliberately does not scrape Instagram/Flashscore.
"""
import os
import re
from pathlib import Path
from urllib.parse import quote
import requests

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ASSETS.mkdir(exist_ok=True)

UA = "OtabekZokirovFootballBot/2.0 (Telegram media bot)"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def _clean_terms(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"[^\w\s'’-]", " ", text, flags=re.UNICODE)
    words = text.split()
    # Keep searches focused; long news bodies tend to return poor results.
    return " ".join(words[:12])


def find_real_photo(query: str):
    """Return (local_path, source_url) for a Commons photo, or (None, None)."""
    query = _clean_terms(query)
    if not query:
        return None, None

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,  # File namespace
        "gsrlimit": 8,
        "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": 1600,
    }
    try:
        r = requests.get(COMMONS_API, params=params, headers={"User-Agent": UA}, timeout=20)
        r.raise_for_status()
        pages = (r.json().get("query") or {}).get("pages") or {}
    except requests.RequestException:
        return None, None

    candidates = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        mime = info.get("mime", "")
        width = info.get("width", 0) or 0
        height = info.get("height", 0) or 0
        url = info.get("thumburl") or info.get("url")
        if not url or not mime.startswith("image/"):
            continue
        if width < 700 or height < 400:
            continue
        if width / max(height, 1) < 1.15:
            continue
        candidates.append((width * height, url, page.get("title", ""), info.get("descriptionurl", "")))

    if not candidates:
        return None, None

    # Prefer the largest suitable image.
    _, url, title, source_url = max(candidates, key=lambda x: x[0])
    safe = re.sub(r"[^A-Za-z0-9]+", "_", title)[:80] or "football_photo"
    path = ASSETS / f"media_{safe}.jpg"
    try:
        data = requests.get(url, headers={"User-Agent": UA}, timeout=30).content
        if not data:
            return None, None
        path.write_bytes(data)
        return path, source_url or url
    except requests.RequestException:
        return None, None


def get_news_photo(title: str, body: str = ""):
    """Find a real photo using the most useful words from a news post."""
    # Try title first, then a title + short body fallback.
    for query in (title, f"{title} {body[:120]}"):
        path, source = find_real_photo(query)
        if path:
            return path, source
    return None, None


def get_transfer_photo(player: str, new_club: str = ""):
    for query in (player, f"{player} {new_club}"):
        path, source = find_real_photo(query)
        if path:
            return path, source
    return None, None
