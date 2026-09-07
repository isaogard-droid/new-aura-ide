"""Кэш-функции и circuit breaker для skills_search."""
import json
import os
import sqlite3
import time

from .paths import (
    CACHE_DB,
    CACHE_DIR,
    CIRCUIT_BREAKER_CONFIG,
    MIRROR_DIR,
    SKILL_KNOWLEDGE_DB,
    TTL,
    TTL_BY_SOURCE,
)


def cache_init():
    """Инициализация кэша и баз данных."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(MIRROR_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(SKILL_KNOWLEDGE_DB), exist_ok=True)

    with sqlite3.connect(CACHE_DB) as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS skills_search "
            "(q_hash TEXT PRIMARY KEY, query TEXT, result TEXT, ts REAL, source TEXT)")
        con.execute(
            "CREATE TABLE IF NOT EXISTS skills_read "
            "(key TEXT PRIMARY KEY, url TEXT, text TEXT, ts REAL)")
        con.execute(
            "CREATE TABLE IF NOT EXISTS circuit_breaker "
            "(source TEXT PRIMARY KEY, failures INTEGER, last_failure REAL)")

    # База знаний скиллов (SQLite FTS5)
    with sqlite3.connect(SKILL_KNOWLEDGE_DB) as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS skills "
            "(id TEXT PRIMARY KEY, name TEXT, owner TEXT, repo TEXT, source TEXT, "
            "description TEXT, installs INTEGER, content TEXT, fetched_at REAL)")
        con.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5("
            "name, description, content, content='skills', content_rowid='rowid')")
        con.execute(
            "CREATE TRIGGER IF NOT EXISTS skills_ai AFTER INSERT ON skills BEGIN "
            "INSERT INTO skills_fts(rowid, name, description, content) "
            "VALUES (new.rowid, new.name, new.description, new.content); END")
        con.execute(
            "CREATE TRIGGER IF NOT EXISTS skills_ad AFTER DELETE ON skills BEGIN "
            "INSERT INTO skills_fts(skills_fts, rowid, name, description, content) "
            "VALUES ('delete', old.rowid, old.name, old.description, old.content); END")
        con.execute(
            "CREATE TRIGGER IF NOT EXISTS skills_au AFTER UPDATE ON skills BEGIN "
            "INSERT INTO skills_fts(skills_fts, rowid, name, description, content) "
            "VALUES ('delete', old.rowid, old.name, old.description, old.content); "
            "INSERT INTO skills_fts(rowid, name, description, content) "
            "VALUES (new.rowid, new.name, new.description, new.content); END")

    # База интернет-контекста
    from .paths import CONTEXT_INTERNET_DB
    with sqlite3.connect(CONTEXT_INTERNET_DB) as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS pages "
            "(url TEXT PRIMARY KEY, title TEXT, content TEXT, query TEXT, "
            "domain TEXT, fetched_at REAL)")
        con.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5("
            "title, content, query, content='pages', content_rowid='rowid')")
        con.execute(
            "CREATE TRIGGER IF NOT EXISTS pages_ai AFTER INSERT ON pages BEGIN "
            "INSERT INTO pages_fts(rowid, title, content, query) "
            "VALUES (new.rowid, new.title, new.content, new.query); END")
        con.execute(
            "CREATE TRIGGER IF NOT EXISTS pages_ad AFTER DELETE ON pages BEGIN "
            "INSERT INTO pages_fts(pages_fts, rowid, title, content, query) "
            "VALUES ('delete', old.rowid, old.title, old.content, old.query); END")
        con.execute(
            "CREATE TRIGGER IF NOT EXISTS pages_au AFTER UPDATE ON pages BEGIN "
            "INSERT INTO pages_fts(pages_fts, rowid, title, content, query) "
            "VALUES ('delete', old.rowid, old.title, old.content, old.query); "
            "INSERT INTO pages_fts(rowid, title, content, query) "
            "VALUES (new.rowid, new.title, new.content, new.query); END")


def circuit_breaker_check(source):
    """Проверить circuit breaker для источника."""
    config = CIRCUIT_BREAKER_CONFIG.get(source, CIRCUIT_BREAKER_CONFIG["default"])
    try:
        with sqlite3.connect(CACHE_DB) as con:
            row = con.execute(
                "SELECT failures, last_failure FROM circuit_breaker WHERE source = ?",
                (source,)).fetchone()
            if row and row[0] >= config["threshold"]:
                if time.time() - row[1] < config["timeout"]:
                    return False  # circuit open
                # timeout прошёл — сброс
                con.execute("DELETE FROM circuit_breaker WHERE source = ?", (source,))
    except Exception:  # noqa: BLE001
        pass
    return True


def circuit_breaker_record_failure(source):
    """Записать отказ для circuit breaker."""
    try:
        with sqlite3.connect(CACHE_DB) as con:
            con.execute(
                "INSERT INTO circuit_breaker (source, failures, last_failure) "
                "VALUES (?, COALESCE((SELECT failures FROM circuit_breaker WHERE source = ?), 0) + 1, ?) "
                "ON CONFLICT(source) DO UPDATE SET failures = failures + 1, last_failure = ?",
                (source, source, time.time(), time.time()))
    except Exception:  # noqa: BLE001
        pass


def circuit_breaker_record_success(source):
    """Записать успех для circuit breaker (сброс)."""
    try:
        with sqlite3.connect(CACHE_DB) as con:
            con.execute("DELETE FROM circuit_breaker WHERE source = ?", (source,))
    except Exception:  # noqa: BLE001
        pass


def cache_get(key, source=None):
    """Получить из кэша."""
    try:
        with sqlite3.connect(CACHE_DB) as con:
            row = con.execute(
                "SELECT result, ts, source FROM skills_search WHERE q_hash = ?",
                (key,)).fetchone()
            if not row:
                return None
            result, ts, src = row
            ttl = TTL_BY_SOURCE.get(src or source, TTL)
            if time.time() - ts > ttl:
                return None
            return json.loads(result)
    except Exception:  # noqa: BLE001
        return None


def cache_set(key, query, result, source=None):
    """Записать в кэш."""
    try:
        with sqlite3.connect(CACHE_DB) as con:
            con.execute(
                "INSERT OR REPLACE INTO skills_search (q_hash, query, result, ts, source) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, query, json.dumps(result), time.time(), source))
    except Exception:  # noqa: BLE001
        pass


def http_get(url, timeout=15, use_github_token=False):
    """HTTP GET с опциональным GitHub токеном."""
    import urllib.request
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("внешний запрос должен использовать HTTPS URL")

    headers = {}
    if use_github_token:
        from .paths import GITHUB_TOKEN
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected — HTTPS scheme and host are validated above
        return resp.read().decode("utf-8")


def mirror_path(skill_id, subpath=""):
    """Путь к локальному зеркалу скилла."""
    safe_id = skill_id.replace("/", "_")
    if subpath:
        return os.path.join(MIRROR_DIR, safe_id, subpath)
    return os.path.join(MIRROR_DIR, safe_id)


def mirror_read(skill_id, subpath="", ttl=TTL):
    """Прочитать из локального зеркала."""
    path = mirror_path(skill_id, subpath)
    if not os.path.exists(path):
        return None
    if time.time() - os.path.getmtime(path) > ttl:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def mirror_write(skill_id, subpath, text):
    """Записать в локальное зеркало."""
    path = mirror_path(skill_id, subpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def check_maturity(skill_id):
    """Проверить зрелость скилла (есть ли в зеркале)."""
    path = mirror_path(skill_id)
    return os.path.exists(path)
