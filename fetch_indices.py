"""Fetch world stock index quotes from Yahoo Finance's public chart API (no API key).

Endpoint: https://query1.finance.yahoo.com/v8/finance/chart/SYMBOL
This is the same free, unauthenticated endpoint used by the popular
`yfinance` library. It requires no signup, no API key, and no GitHub secret.

Note: stooq.com's old free CSV quote endpoint (`/q/l/`) has been retired and
now requires an API key, so it can no longer be used for this project.
"""
import sqlite3
import sys
from datetime import datetime, timezone

import requests

DB_PATH = "political_news.db"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; political-news-collector/1.0)"}

# (country, index name, Yahoo Finance symbol)
INDICES = [
    ("ไทย", "SET Index", "^SET.BK"),
    ("สหรัฐฯ", "Dow Jones", "^DJI"),
    ("สหรัฐฯ", "S&P 500", "^GSPC"),
    ("สหรัฐฯ", "Nasdaq", "^IXIC"),
    ("ญี่ปุ่น", "Nikkei 225", "^N225"),
    ("ฮ่องกง", "Hang Seng", "^HSI"),
    ("จีน", "Shanghai Composite", "000001.SS"),
    ("อังกฤษ", "FTSE 100", "^FTSE"),
    ("เยอรมนี", "DAX", "^GDAXI"),
    ("เกาหลีใต้", "KOSPI", "^KS11"),
    ("สิงคโปร์", "STI", "^STI"),
]


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_indices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            index_name TEXT NOT NULL,
            symbol TEXT UNIQUE NOT NULL,
            price REAL,
            change_pct REAL,
            fetched_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def fetch_one(symbol: str) -> dict | None:
    url = YAHOO_URL.format(symbol=symbol)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[{symbol}] ERROR fetching: {exc}", file=sys.stderr)
        return None

    try:
        payload = resp.json()
        result = payload["chart"]["result"][0]
        meta = result["meta"]
    except (ValueError, KeyError, IndexError, TypeError):
        print(f"[{symbol}] WARNING: unexpected response: {resp.text[:200]!r}", file=sys.stderr)
        return None

    price = meta.get("regularMarketPrice")
    prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")

    if price is None:
        print(f"[{symbol}] WARNING: no price data in response", file=sys.stderr)
        return None

    change_pct = ((price - prev_close) / prev_close * 100) if prev_close else None

    return {"price": float(price), "change_pct": change_pct}


def collect() -> None:
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    now = datetime.now(timezone.utc).isoformat()
    ok, failed = 0, 0

    for country, index_name, symbol in INDICES:
        print(f"[{symbol}] fetching {index_name} ({country})")
        result = fetch_one(symbol)
        if result is None:
            failed += 1
            continue

        conn.execute(
            """
            INSERT INTO stock_indices (country, index_name, symbol, price, change_pct, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                country=excluded.country,
                index_name=excluded.index_name,
                price=excluded.price,
                change_pct=excluded.change_pct,
                fetched_at=excluded.fetched_at
            """,
            (country, index_name, symbol, result["price"], result["change_pct"], now),
        )
        ok += 1

    conn.commit()
    conn.close()
    print(f"Done. Indices updated: {ok}, failed: {failed}")


if __name__ == "__main__":
    collect()
