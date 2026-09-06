"""База интернет-контекста — персистентное хранилище прочитанных веб-страниц."""
import sqlite3
import time
from urllib.parse import urlparse

from .paths import CONTEXT_INTERNET_DB


def save_to_internet(url, title, content, query=""):
    """Сохранить прочитанную веб-страницу в базу интернет-контекста.
    Персистентно, НЕ кэш — растёт с каждым fetch_page/batch_fetch."""
    try:
        domain = urlparse(url).netloc

        with sqlite3.connect(CONTEXT_INTERNET_DB) as con:
            con.execute(
                "INSERT OR REPLACE INTO pages "
                "(url, title, content, query, domain, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (url, title, content, query, domain, time.time()))
    except Exception:  # noqa: BLE001
        pass


def search_internet(query, limit=10):
    """Поиск по базе интернет-контекста (FTS5).
    Возвращает список {url, title, domain, snippet, score}."""
    try:
        with sqlite3.connect(CONTEXT_INTERNET_DB) as con:
            rows = con.execute(
                "SELECT p.url, p.title, p.domain, p.query, "
                "snippet(pages_fts, 1, '<b>', '</b>', '...', 32) as snippet, "
                "rank "
                "FROM pages_fts "
                "JOIN pages p ON p.rowid = pages_fts.rowid "
                "WHERE pages_fts MATCH ? "
                "ORDER BY rank "
                "LIMIT ?",
                (query, limit)).fetchall()

        return [
            {
                "url": r[0],
                "title": r[1],
                "domain": r[2],
                "query": r[3],
                "snippet": r[4],
                "score": -r[5]
            }
            for r in rows
        ]
    except Exception:  # noqa: BLE001
        return []


def get_internet_stats():
    """Статистика базы интернет-контекста."""
    try:
        with sqlite3.connect(CONTEXT_INTERNET_DB) as con:
            count = con.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
            domains = con.execute(
                "SELECT domain, COUNT(*) FROM pages GROUP BY domain ORDER BY COUNT(*) DESC LIMIT 10").fetchall()
            latest = con.execute(
                "SELECT MAX(fetched_at) FROM pages").fetchone()[0]
        return {
            "total": count,
            "top_domains": dict(domains),
            "latest": time.strftime("%Y-%m-%d %H:%M", time.localtime(latest)) if latest else None
        }
    except Exception:  # noqa: BLE001
        return {"total": 0, "top_domains": {}, "latest": None}
