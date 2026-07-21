"""Export the political_news.db data into a single static docs/index.html page."""
import html
import sqlite3
from datetime import datetime, timezone

DB_PATH = "political_news.db"
OUTPUT_PATH = "docs/index.html"
MAX_NEWS_ITEMS = 100


def fetch_indices(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    try:
        return conn.execute(
            "SELECT country, index_name, symbol, price, change_pct, fetched_at "
            "FROM stock_indices ORDER BY country, index_name"
        ).fetchall()
    except sqlite3.OperationalError:
        return []


def fetch_news(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    try:
        return conn.execute(
            "SELECT title, link, source, published, collected_at "
            "FROM news ORDER BY collected_at DESC LIMIT ?",
            (MAX_NEWS_ITEMS,),
        ).fetchall()
    except sqlite3.OperationalError:
        return []


def render_indices_rows(rows: list[sqlite3.Row]) -> str:
    if not rows:
        return '<tr><td colspan="4" class="empty">ยังไม่มีข้อมูลดัชนีหุ้น</td></tr>'

    out = []
    for r in rows:
        price = r["price"]
        change = r["change_pct"]
        price_str = f"{price:,.2f}" if price is not None else "N/D"
        if change is None:
            change_str = "N/D"
            change_class = ""
        else:
            sign = "+" if change >= 0 else ""
            change_str = f"{sign}{change:.2f}%"
            change_class = "up" if change >= 0 else "down"

        out.append(
            "<tr>"
            f'<td>{html.escape(r["country"])}</td>'
            f'<td>{html.escape(r["index_name"])} <span class="symbol">{html.escape(r["symbol"])}</span></td>'
            f'<td class="num">{price_str}</td>'
            f'<td class="num {change_class}">{change_str}</td>'
            "</tr>"
        )
    return "\n".join(out)


def render_news_items(rows: list[sqlite3.Row]) -> str:
    if not rows:
        return '<p class="empty">ยังไม่มีข่าวการเมือง</p>'

    out = []
    for r in rows:
        title = html.escape(r["title"])
        link = html.escape(r["link"])
        source = html.escape(r["source"])
        published = html.escape(r["published"] or "")
        out.append(
            '<li class="news-item">'
            f'<a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>'
            '<div class="news-meta">'
            f'<span class="source">{source}</span>'
            + (f'<span class="published">{published}</span>' if published else "")
            + "</div></li>"
        )
    return "\n".join(out)


def render_html(indices_rows, news_rows) -> str:
    now_str = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ข่าวการเมือง และ ดัชนีหุ้นโลก</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #f5f6f8;
    --card-bg: #ffffff;
    --text: #1a1a1a;
    --muted: #666666;
    --border: #e2e2e2;
    --up: #0a8a3f;
    --down: #d13438;
    --accent: #2455a4;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #14161a;
      --card-bg: #1e2126;
      --text: #eaeaea;
      --muted: #9a9a9a;
      --border: #33363c;
      --up: #4fd07a;
      --down: #ff6b6b;
      --accent: #6ea8ff;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 0 0 40px;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Sarabun", "Noto Sans Thai", Arial, sans-serif;
    line-height: 1.5;
  }}
  header {{
    background: var(--accent);
    color: #fff;
    padding: 20px 16px;
    text-align: center;
  }}
  header h1 {{
    margin: 0 0 6px;
    font-size: 1.4rem;
  }}
  header .updated {{
    font-size: 0.85rem;
    opacity: 0.9;
  }}
  main {{
    max-width: 900px;
    margin: 0 auto;
    padding: 16px;
  }}
  section {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 20px;
  }}
  section h2 {{
    margin-top: 0;
    font-size: 1.1rem;
    border-bottom: 2px solid var(--border);
    padding-bottom: 8px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }}
  th, td {{
    text-align: left;
    padding: 8px 6px;
    border-bottom: 1px solid var(--border);
  }}
  th {{
    color: var(--muted);
    font-weight: 600;
    font-size: 0.8rem;
    text-transform: uppercase;
  }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.up {{ color: var(--up); font-weight: 600; }}
  td.down {{ color: var(--down); font-weight: 600; }}
  .symbol {{ color: var(--muted); font-size: 0.75rem; }}
  ul.news-list {{
    list-style: none;
    margin: 0;
    padding: 0;
  }}
  li.news-item {{
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
  }}
  li.news-item:last-child {{ border-bottom: none; }}
  li.news-item a {{
    color: var(--accent);
    text-decoration: none;
    font-weight: 500;
  }}
  li.news-item a:hover {{ text-decoration: underline; }}
  .news-meta {{
    margin-top: 4px;
    font-size: 0.8rem;
    color: var(--muted);
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }}
  .empty {{ color: var(--muted); text-align: center; padding: 12px; }}
  footer {{
    text-align: center;
    color: var(--muted);
    font-size: 0.75rem;
    margin-top: 20px;
  }}
  @media (max-width: 480px) {{
    table {{ font-size: 0.8rem; }}
    th, td {{ padding: 6px 4px; }}
  }}
</style>
</head>
<body>
<header>
  <h1>ข่าวการเมือง &amp; ดัชนีหุ้นโลก</h1>
  <div class="updated">อัปเดตล่าสุด: {now_str}</div>
</header>
<main>
  <section id="indices">
    <h2>ดัชนีหุ้นโลก</h2>
    <table>
      <thead>
        <tr><th>ประเทศ</th><th>ดัชนี</th><th class="num">ราคาล่าสุด</th><th class="num">เปลี่ยนแปลง %</th></tr>
      </thead>
      <tbody>
{render_indices_rows(indices_rows)}
      </tbody>
    </table>
  </section>

  <section id="news">
    <h2>ข่าวการเมืองล่าสุด</h2>
    <ul class="news-list">
{render_news_items(news_rows)}
    </ul>
  </section>
</main>
<footer>
  Political News Collector — ข้อมูลจาก RSS สาธารณะ และ stooq.com
</footer>
</body>
</html>
"""


def export() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    indices_rows = fetch_indices(conn)
    news_rows = fetch_news(conn)
    conn.close()

    output = render_html(indices_rows, news_rows)

    import os
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"Exported {OUTPUT_PATH} ({len(indices_rows)} indices, {len(news_rows)} news items)")


if __name__ == "__main__":
    export()
