#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""База находок и выводов (research.db) — знания, к которым уже приходили.

Зачем: ресёрч (веб, Camoufox, эксперименты, разборы) даёт выводы, которые
теряются после разговора. Здесь они живут отдельно от файлов проекта и
находятся поиском, как и всё остальное.

Примеры:
    python3 findings.py add "MCP для LSP" --text "agent-lsp — самый зрелый мост..." --tags mcp lsp
    python3 findings.py search mcp
    python3 findings.py list
    python3 findings.py list --tags lsp
    python3 findings.py del 12
    python3 findings.py edit 12 --tags "lsp mcp"
    python3 findings.py supersede 12 --note "опровергнуто ресёрчем 17.08"
    python3 findings.py consolidate --days 30          # кандидаты на архив
    python3 findings.py consolidate --days 30 --apply  # заархивировать их
    python3 findings.py search mcp --status archived   # искать и в архиве

Карта после механической резки god-файла (код перенесён дословно, поведение
не менялось; импортёры модуля видят те же имена — re-export ниже):
    findings_cmds.py — cmd_add, _parse_ids, cmd_del, cmd_edit, cmd_search,
                       cmd_list, cmd_show, cmd_stats
    findings_links.py — _row_links, cmd_link_add, cmd_link_list, cmd_link_rm,
                        cmd_related, _print_chain
    здесь — ROOT, DB, SCHEMA, OPS, sanitize_query, connect, main (argparse).
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
import _compat

ROOT = _compat.chulan_root()

# Windows-консоль по умолчанию cp1251 — русский вывод падает с
# UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


# БД можно переопределить для тестов/песочницы (изоляция от prod-хранилища):
# AGGG2_RESEARCH_DB=/tmp/test.db python3 db-tools/findings.py ...
DB = os.environ.get("AGGG2_RESEARCH_DB", os.path.join(ROOT, "db", "research.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL,
    topic TEXT NOT NULL,
    text TEXT NOT NULL,
    tags TEXT DEFAULT '',
    source TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    updated TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id INTEGER NOT NULL,
    to_id INTEGER NOT NULL,
    kind TEXT NOT NULL DEFAULT 'related',
    note TEXT DEFAULT '',
    created TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_id);
CREATE INDEX IF NOT EXISTS idx_links_to ON links(to_id);
CREATE VIRTUAL TABLE IF NOT EXISTS findings_fts USING fts5(
    topic, text, content='findings', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS findings_ai AFTER INSERT ON findings BEGIN
    INSERT INTO findings_fts(rowid, topic, text)
    VALUES (new.id, new.topic, new.text);
END;
CREATE TRIGGER IF NOT EXISTS findings_ad AFTER DELETE ON findings BEGIN
    INSERT INTO findings_fts(findings_fts, rowid, topic, text)
    VALUES ('delete', old.id, old.topic, old.text);
END;
CREATE TRIGGER IF NOT EXISTS findings_au AFTER UPDATE ON findings BEGIN
    INSERT INTO findings_fts(findings_fts, rowid, topic, text)
    VALUES ('delete', old.id, old.topic, old.text);
    INSERT INTO findings_fts(rowid, topic, text)
    VALUES (new.id, new.topic, new.text);
END;
"""

OPS = {"AND", "OR", "NOT", "NEAR"}


def sanitize_query(query):
    """Экранирует FTS5-запрос: токены со спецсимволами (включая дефис —
    «agent-lsp» ломает FTS) оборачиваются в двойные кавычки; операторы и
    готовые фразы не трогаем."""
    out = []
    for tok in query.split():
        upper = tok.upper()
        if upper in OPS or upper.startswith("NEAR(") or \
                (tok.startswith('"') and tok.endswith('"')):
            out.append(tok)
        elif any(c in tok for c in '"-()*:^'):
            # Префиксный поиск (подмешк*) не оборачиваем: в кавычках
            # звёздочка становится литералом и префикс не работает.
            if tok.endswith("*") and not any(c in tok[:-1] for c in '"-():^'):
                out.append(tok)
            else:
                out.append('"' + tok.replace('"', '""') + '"')
        else:
            out.append(tok)
    return " ".join(out)


def connect():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    # Мягкая миграция старых баз: колонки, которых ещё не было
    cols = [r[1] for r in con.execute("PRAGMA table_info(findings)")]
    if "source" not in cols:
        con.execute("ALTER TABLE findings ADD COLUMN source TEXT DEFAULT ''")
    if "status" not in cols:
        con.execute(
            "ALTER TABLE findings ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    if "updated" not in cols:
        con.execute("ALTER TABLE findings ADD COLUMN updated TEXT DEFAULT ''")
    con.commit()
    return con


# findings.py может запускаться и как скрипт (__main__), и как модуль
# (tests/tasks). Модули-команды импортируют его как "findings": регистрируем
# себя под обоими именами, чтобы не было второго исполнения (ImportError
# при частичной инициализации в CLI-режиме).
sys.modules.setdefault("findings", sys.modules[__name__])

from findings_cmds import (
    _parse_ids,
    cmd_add,
    cmd_consolidate,
    cmd_del,
    cmd_edit,
    cmd_list,
    cmd_search,
    cmd_show,
    cmd_stats,
    cmd_supersede,
)
from findings_links import (
    cmd_link_add,
    cmd_link_list,
    cmd_link_rm,
    cmd_related,
)

__all__ = [
    "ROOT", "DB", "SCHEMA", "OPS", "sanitize_query", "connect",
    "cmd_add", "cmd_consolidate", "cmd_del", "cmd_edit", "cmd_search",
    "cmd_list", "cmd_show", "cmd_stats", "cmd_supersede", "_parse_ids",
    "cmd_link_add", "cmd_link_list", "cmd_link_rm", "cmd_related",
]


def main():
    ap = argparse.ArgumentParser(description="База находок и выводов")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="добавить находку")
    p_add.add_argument("topic", help="тема одной строкой")
    p_add.add_argument("--text", required=True, help="вывод/факт")
    p_add.add_argument("--tags", default="", help="теги через пробел")
    p_add.add_argument("--source", default="", help="откуда взято (путь/URL)")
    p_add.add_argument("--related", default="",
                       help="id связанных находок через запятую")
    p_add.set_defaults(fn=cmd_add)

    p_search = sub.add_parser("search", help="поиск по находкам")
    p_search.add_argument("query", help="FTS5-запрос")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--source", default="",
                          help="фильтр: источник (путь/URL) содержит подстроку")
    p_search.add_argument("--tag", default="",
                          help="фильтр: точный тег находки")
    p_search.add_argument("--status", default="live",
                          choices=["live", "active", "superseded",
                                   "archived", "all"],
                          help="фильтр по статусу (default: live = только active; "
                               "superseded/archived скрыты, --status all — все)")
    p_search.set_defaults(fn=cmd_search)

    p_list = sub.add_parser("list", help="список находок")
    p_list.add_argument("--tags", default="", help="фильтр по тегу (точное слово)")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--status", default="live",
                        choices=["live", "active", "superseded",
                                 "archived", "all"],
                        help="фильтр по статусу (default: live = только active)")
    p_list.set_defaults(fn=cmd_list)

    p_del = sub.add_parser("del", help="удалить находку по id")
    p_del.add_argument("id", type=int)
    p_del.set_defaults(fn=cmd_del)

    p_edit = sub.add_parser("edit", help="изменить находку по id")
    p_edit.add_argument("id", type=int)
    p_edit.add_argument("--topic")
    p_edit.add_argument("--text")
    p_edit.add_argument("--tags")
    p_edit.add_argument("--source")
    p_edit.set_defaults(fn=cmd_edit)

    p_show = sub.add_parser("show", help="полная запись находки + связи")
    p_show.add_argument("id", type=int)
    p_show.set_defaults(fn=cmd_show)

    p_super = sub.add_parser("supersede", help="пометить находку устаревшей "
                                               "(retract: не удалять, а снять с выдачи)")
    p_super.add_argument("id", type=int)
    p_super.add_argument("--note", default="",
                         help="почему устарела (добавляется к тексту)")
    p_super.set_defaults(fn=cmd_supersede)

    p_cons = sub.add_parser("consolidate", help="консолидация: кандидаты на архив "
                                                "(старые, без связей) и их архивация")
    p_cons.add_argument("--days", type=int, default=30,
                        help="старше N дней (default: 30)")
    p_cons.add_argument("--apply", action="store_true",
                        help="без флага — только показать кандидатов; "
                             "с флагом — пометить status=archived")
    p_cons.add_argument("--id", type=int, action="append",
                        help="архивировать конкретные id (можно несколько); "
                             "вместе с --apply")
    p_cons.add_argument("--dupes", action="store_true",
                        help="поиск почти-дубликатов активных находок "
                             "(SequenceMatcher по темам; --apply архивирует "
                             "старшие дубликаты)")
    p_cons.set_defaults(fn=cmd_consolidate)

    p_related = sub.add_parser("related", help="что связано с находкой")
    p_related.add_argument("id", type=int)
    p_related.add_argument("--depth", type=int, default=0,
                           help="глубина графа связей (0 — только соседи)")
    p_related.set_defaults(fn=cmd_related)

    p_link = sub.add_parser("link", help="связи находок (link add/list/rm)")
    link_sub = p_link.add_subparsers(dest="link_cmd", required=True)
    p_la = link_sub.add_parser("add", help="добавить связь")
    p_la.add_argument("from_id", type=int)
    p_la.add_argument("to_id", type=int)
    p_la.add_argument("--kind", default="related",
                      help="тип: related/extends/contradicts/source (по умолчанию related)")
    p_la.add_argument("--note", default="", help="комментарий к связи")
    p_la.set_defaults(fn=cmd_link_add)
    p_ll = link_sub.add_parser("list", help="связи находки (обе стороны)")
    p_ll.add_argument("id", type=int)
    p_ll.set_defaults(fn=cmd_link_list)
    p_lr = link_sub.add_parser("rm", help="удалить связь по id")
    p_lr.add_argument("id", type=int)
    p_lr.set_defaults(fn=cmd_link_rm)

    p_stats = sub.add_parser("stats", help="метрики: всего находок, за 7 дней, связи, топ тегов")
    p_stats.set_defaults(fn=cmd_stats)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()


# Оригинал от https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна и лучше предыдущей.

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
