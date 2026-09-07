"""База знаний скиллов — персистентное хранилище прочитанных скиллов."""
import sqlite3
import time

from .paths import SKILL_KNOWLEDGE_DB


def save_skill_to_knowledge(skill_id, content, source="external"):
    """Сохранить прочитанный скилл в базу знаний (персистентно, НЕ кэш).
    Растёт с каждым прочитанным скиллом — 'локальный интернет скиллов'."""
    parts = [p for p in skill_id.split("/") if p]
    if len(parts) < 3:
        return

    owner, repo, name = parts[0], parts[1], parts[2]

    # Извлечь описание из content (первая строка после --- или первые 200 символов)
    description = ""
    lines = content.split("\n")
    for line in lines[:20]:
        if line.startswith("description:"):
            description = line.replace("description:", "").strip().strip('"')
            break
    if not description:
        description = content[:200].replace("\n", " ").strip()

    try:
        with sqlite3.connect(SKILL_KNOWLEDGE_DB) as con:
            con.execute(
                "INSERT OR REPLACE INTO skills "
                "(id, name, owner, repo, source, description, installs, content, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (skill_id, name, owner, repo, source, description, 0, content, time.time()))
    except Exception:  # noqa: BLE001 — база знаний не критична
        pass


def search_knowledge(query, limit=10):
    """Поиск по локальной базе знаний скиллов (FTS5).
    Возвращает список {id, name, owner, repo, snippet, score}."""
    try:
        with sqlite3.connect(SKILL_KNOWLEDGE_DB) as con:
            # FTS5 поиск с подсветкой (snippet)
            rows = con.execute(
                "SELECT s.id, s.name, s.owner, s.repo, s.description, "
                "snippet(skills_fts, 2, '<b>', '</b>', '...', 32) as snippet, "
                "rank "
                "FROM skills_fts "
                "JOIN skills s ON s.rowid = skills_fts.rowid "
                "WHERE skills_fts MATCH ? "
                "ORDER BY rank "
                "LIMIT ?",
                (query, limit)).fetchall()

        return [
            {
                "id": r[0],
                "name": r[1],
                "owner": r[2],
                "repo": r[3],
                "description": r[4],
                "snippet": r[5],
                "score": -r[6]  # rank отрицательный, инвертируем для удобства
            }
            for r in rows
        ]
    except Exception:  # noqa: BLE001
        return []


def get_knowledge_stats():
    """Статистика базы знаний скиллов."""
    try:
        with sqlite3.connect(SKILL_KNOWLEDGE_DB) as con:
            count = con.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
            sources = con.execute(
                "SELECT source, COUNT(*) FROM skills GROUP BY source").fetchall()
            latest = con.execute(
                "SELECT MAX(fetched_at) FROM skills").fetchone()[0]
        return {
            "total": count,
            "sources": dict(sources),
            "latest": time.strftime("%Y-%m-%d %H:%M", time.localtime(latest)) if latest else None
        }
    except Exception:  # noqa: BLE001
        return {"total": 0, "sources": {}, "latest": None}
