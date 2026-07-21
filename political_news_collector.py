"""Collect Thai/English political news from RSS feeds into SQLite.

Sources: Thai PBS, The Standard, BBC Thai, Bangkok Post, Nation Thailand.
Deduplicates articles by a hash of their URL.
"""
import hashlib
import sqlite3
import sys
from datetime import datetime, timezone

import feedparser

DB_PATH = "political_news.db"

FEEDS = {
    "Thai PBS": "https://www.thaipbs.or.th/rss/news.xml",
    "The Standard": "https://thestandard.co/feed/",
    "BBC Thai": "https://feeds.bbci.co.uk/thai/rss.xml",
    "Bangkok Post": "https://www.bangkokpost.com/rss/data/topstories.xml",
    "Nation Thailand": "https://www.nationthailand.com/rss",
}

KEYWORDS = [
    # Thai
    "การเมือง", "รัฐบาล", "นายก", "นายกรัฐมนตรี", "สภา", "รัฐสภา",
    "ส.ส.", "ส.ว.", "เลือกตั้ง", "พรรค", "รัฐมนตรี", "คณะรัฐมนตรี",
    "ครม.", "กกต.", "รัฐธรรมนูญ", "ฝ่ายค้าน", "ยุบสภา", "อภิปราย",
    # English
    "politic", "government", "election", "parliament", "minister",
    "cabinet", "congress", "senate", "vote", "coup", "prime minister",
    "opposition", "constitution", "lawmaker", "mp ",
]


def matched_keywords(text: str) -> list[str]:
    lowered = text.lower()
    return [kw for kw in KEYWORDS if kw.lower() in lowered]


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_hash TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            source TEXT NOT NULL,
            published TEXT,
            summary TEXT,
            matched_keywords TEXT,
            collected_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def hash_url(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def collect() -> None:
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    total_new = 0
    total_seen = 0

    for source, feed_url in FEEDS.items():
        print(f"[{source}] fetching {feed_url}")
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            print(f"[{source}] ERROR fetching feed: {exc}", file=sys.stderr)
            continue

        if parsed.bozo and not parsed.entries:
            print(f"[{source}] WARNING: feed parse issue ({parsed.bozo_exception})", file=sys.stderr)

        for entry in parsed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", "") or entry.get("description", "")
            published = entry.get("published", "") or entry.get("updated", "")

            if not title or not link:
                continue

            combined_text = f"{title} {summary}"
            hits = matched_keywords(combined_text)
            if not hits:
                continue

            total_seen += 1
            url_hash = hash_url(link)

            try:
                conn.execute(
                    """
                    INSERT INTO news
                        (url_hash, title, link, source, published, summary, matched_keywords, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        url_hash,
                        title,
                        link,
                        source,
                        published,
                        summary,
                        ", ".join(hits),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                total_new += 1
            except sqlite3.IntegrityError:
                # duplicate url_hash -> already collected
                pass

        conn.commit()

    conn.close()
    print(f"Done. Political articles matched: {total_seen}, newly stored: {total_new}")


if __name__ == "__main__":
    collect()
