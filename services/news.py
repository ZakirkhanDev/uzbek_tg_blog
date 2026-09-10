"""Small RSS-based news/transfer collector.

Uses public RSS feeds rather than scraping social-media pages. Each scheduler run
publishes at most one fresh item, with SQLite preventing repeats.
"""
import os
import re
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import quote
import requests

DEFAULT_NEWS_FEEDS = [
    "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "https://www.espn.com/espn/rss/soccer/news",
]
DEFAULT_TRANSFER_FEEDS = [
    "https://news.google.com/rss/search?q=football%20transfer&hl=en-US&gl=US&ceid=US:en",
    "https://www.skysports.com/rss/12040",
]


def _feeds(env_name, defaults):
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return defaults
    return [x.strip() for x in raw.split(",") if x.strip()]


def _strip_html(text):
    text = unescape(text or "")
    return re.sub(r"<[^>]+>", " ", text).strip()


def _text(node, names):
    for child in list(node):
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in names:
            return child.text or ""
    return ""


def fetch_feed_items(url, limit=8):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "OtabekZokirovFootballBot/4.0"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except (requests.RequestException, ET.ParseError):
        return []

    items = []
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1].lower()
        if tag != "item":
            continue
        title = _text(node, {"title"}).strip()
        link = _text(node, {"link"}).strip()
        description = _strip_html(_text(node, {"description", "summary", "content"}))
        pub = _text(node, {"pubdate", "published", "updated"}).strip()
        source = _text(node, {"source"}).strip() or "RSS"
        if title:
            items.append({"title": title, "body": description, "link": link, "pub": pub, "source": source, "feed": url})
        if len(items) >= limit:
            break
    return items


def _clean_title(title):
    return re.sub(r"\s+", " ", title or "").strip()


def _short_body(body, max_chars=420):
    body = re.sub(r"\s+", " ", body or "").strip()
    if len(body) > max_chars:
        body = body[:max_chars].rsplit(" ", 1)[0] + "…"
    return body


def get_fresh_news(posted_checker):
    for feed in _feeds("NEWS_RSS_URLS", DEFAULT_NEWS_FEEDS):
        for item in fetch_feed_items(feed):
            title = _clean_title(item["title"])
            key = "rss:news:" + title.lower()
            if not posted_checker(key):
                item["title"] = title
                item["body"] = _short_body(item["body"])
                item["event_key"] = key
                return item
    return None


def get_fresh_transfer(posted_checker):
    keywords = ("transfer", "sign", "joins", "deal", "loan", "moves", "agreement", "transfers")
    for feed in _feeds("TRANSFER_RSS_URLS", DEFAULT_TRANSFER_FEEDS):
        for item in fetch_feed_items(feed):
            title = _clean_title(item["title"])
            hay = (title + " " + item["body"]).lower()
            if not any(k in hay for k in keywords):
                continue
            key = "rss:transfer:" + title.lower()
            if not posted_checker(key):
                item["title"] = title
                item["body"] = _short_body(item["body"])
                item["event_key"] = key
                return item
    return None
