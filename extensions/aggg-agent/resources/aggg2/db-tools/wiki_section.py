"""wiki_section — секция Wiki в каждом поиске (CLI search.py + MCP db-tools).

Единая реализация «Wiki всегда» (DRY): топ постов по теме с заголовками
присоединяется к результатам ЛЮБОГО поиска, не только пустого. Паттерны:
query-операция LLM Wiki (Karpathy: читать из compiled-слоя при каждом
запросе) + agentic retrieval (агент видит хиты и сам решает, открывать
ли). Дешево: одна SQLite-выборка + frontmatter ≤3 файлов.
"""

import os
import sqlite3

from _compat import chulan_root

ROOT = chulan_root()
SKIP = {"index.md", "log.md", "README.md"}


def wiki_section(query, safe, current_db, seen_paths=None, limit=3):
    """Секция для вывода: топ постов Wiki с заголовками.

    query  — сырой запрос (для trigram-фолбэка, литеральная подстрока)
    safe   — санитизированный запрос (FTS5: search.py sanitize_query /
             mcp _fts_safe)
    current_db — путь/имя базы, в которой ищут (сама wiki — секции нет)
    seen_paths — пути уже показанных файлов (дедуп: в aggg2 Wiki/ внутри
             индекса — дубли не показываем)
    """
    if seen_paths is None:
        seen_paths = set()
    wiki = os.path.join(ROOT, "db", "wiki.db")
    if os.path.abspath(current_db) == os.path.abspath(wiki):
        return ""
    if not os.path.isfile(wiki):
        return ""
    rows = []
    try:
        wcon = sqlite3.connect(wiki)
        try:
            rows = wcon.execute(
                "SELECT rel_path FROM files_fts WHERE files_fts MATCH ? "
                "ORDER BY rank LIMIT ?", (safe, limit + 5)).fetchall()
            if not rows and len(query) >= 3:
                rows = wcon.execute(
                    "SELECT rel_path FROM files_fts_trigram "
                    "WHERE files_fts_trigram MATCH ? ORDER BY rank LIMIT ?",
                    (query, limit + 5)).fetchall()
        finally:
            wcon.close()
    except (sqlite3.Error, OSError):
        return ""
    seen = set(seen_paths)
    seen |= {("Wiki/" + p if not p.startswith("Wiki/") else p)
             for p in seen_paths}
    fresh = [r[0] for r in rows
             if r[0] not in SKIP
             and r[0] not in seen and "Wiki/" + r[0] not in seen][:limit]
    if not fresh:
        return ""
    lines = [f"  • {wiki_title(p)} — {p}" for p in fresh]
    return "\n📚 Wiki (ищи всегда):\n" + "\n".join(lines)


def wiki_title(rel_path):
    """Заголовок поста из frontmatter (title:), фолбэк — имя файла.
    Читается только первый килобайт, ≤3 файла на поиск."""
    p = os.path.join(ROOT, "Wiki", rel_path)
    try:
        with open(p, encoding="utf-8") as f:
            head = f.read(1024)
        for ln in head.splitlines()[:15]:
            if ln.startswith("title:"):
                return ln.split(":", 1)[1].strip().strip("'\"")
    except (OSError, UnicodeDecodeError):
        pass
    return os.path.splitext(os.path.basename(rel_path))[0]
