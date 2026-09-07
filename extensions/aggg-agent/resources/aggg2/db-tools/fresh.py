#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""fresh.py — УНИВЕРСАЛЬНЫЙ сторож свежести баз индексов.

Одна точка «пересобрать при рассинхроне» для всех потребителей
(MCP db-tools search, search.py, repomap.py, search_all.py, doctor,
CI). Сравнивает built_at из meta-таблицы базы с max-mtime файлов
корня; при рассинхроне — инкрементальная пересборка build.py
(спавнится ТОЛЬКО при рассинхроне — штатный поиск не тормозится).

Паттерны индустрии (ресёрч 16.08, 10 источников): refresh-on-read
(neo-localmcp context_prepare — stale-проверка на каждый вызов),
nexus-mcp ADR-015 (mtime-diff, lazy reindex вместо фонового демона),
oracle real-time RAG («freshness must be evaluated, not assumed»),
synthmetric (triggers: event-based — пересборка по факту изменений).

Использование:
    python3 fresh.py              # все известные базы: пересобрать рассинхронные
    python3 fresh.py wiki         # одну базу
    python3 fresh.py --check      # только отчёт, без пересборки (doctor/CI)

Программно:
    from fresh import ensure      # -> 'ok' | 'rebuilt' | 'no-meta' | 'no-root' | 'error'
"""
import argparse
import contextlib
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHULAN = HERE.parent

# Детерминированный discovery корня по конвенции (без хардкода имён
# проектов, паттерн индустрии: marker-based root detection, memo-init —
# «resolution is pure function of the filesystem»):
#   wiki    -> Wiki/
#   aggg2   -> корень чулана
#   <имя>   -> projects/<имя>/ (новый проект = папка в projects/ + база
#              db/<имя>.db — подхватывается сам, как index_project MCP)
# Источник №1 для существующих баз — meta.root в самой базе (после
# первой сборки база «помнит» свой корень — хоть с любого пути вне
# projects/, например /run/media/.../внешний-проект).
def discover_root(db: str) -> str | None:
    if db == "wiki":
        root = CHULAN / "Wiki"
        return str(root) if root.is_dir() else None
    if db == "aggg2":
        return str(CHULAN)
    proj = CHULAN / "projects" / db
    return str(proj) if proj.is_dir() else None
SKIP_DIRS = {"db", "venv", ".venv", "models", ".git", "__pycache__",
             "node_modules", "vendor", "build", "dist", "log-archive"}


def _meta(db_path: Path) -> dict:
    try:
        con = sqlite3.connect(db_path)
        try:
            rows = con.execute("SELECT key, value FROM meta").fetchall()
            return dict(rows)
        except sqlite3.OperationalError:
            return {}
        finally:
            con.close()
    except sqlite3.Error:
        return {}


def _newest_mtime(root: str, since: float) -> float:
    newest = since
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            with contextlib.suppress(OSError):
                mt = os.path.getmtime(os.path.join(dirpath, fn))
                if mt > newest:
                    newest = mt
    return newest


def _rebuild(db_path: Path, root: str) -> bool:
    cmd = [sys.executable, str(HERE / "build.py"), "-r", root,
           "-o", str(db_path)]
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        proc = subprocess.run(cmd, capture_output=True, timeout=600)
        return proc.returncode == 0
    return False


def ensure(db: str) -> str:
    """Проверить базу по имени; пересобрать при рассинхроне.
    Возвращает: ok / rebuilt / no-meta / no-root / error."""
    db_path = CHULAN / "db" / f"{db}.db"
    if not db_path.is_file():
        return "no-root" if not discover_root(db) else "error"
    meta = _meta(db_path)
    root = meta.get("root") or discover_root(db)
    if not root or not os.path.isdir(root):
        return "no-root"
    if not meta.get("built_at"):
        # Старая база без meta: пересборка создаст метаданные свежести
        return "rebuilt" if _rebuild(db_path, root) else "error"
    since = float(meta["built_at"])
    if _newest_mtime(root, since) <= since + 1:
        return "ok"
    return "rebuilt" if _rebuild(db_path, root) else "error"




def _known_dbs() -> list:
    """Базы db/*.db + имена папок projects/ (discovery-конвенция)."""
    names = set()
    db_dir = CHULAN / "db"
    if db_dir.is_dir():
        names.update(p.stem for p in db_dir.glob("*.db"))
    proj_dir = CHULAN / "projects"
    if proj_dir.is_dir():
        names.update(p.name for p in proj_dir.iterdir() if p.is_dir())
    names.discard("research")
    return sorted(names)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dbs", nargs="*", help="базы по имени (пусто — все известные)")
    ap.add_argument("--check", action="store_true",
                    help="только отчёт о рассинхроне, без пересборки")
    args = ap.parse_args()
    targets = args.dbs or _known_dbs()
    bad = 0
    for db in targets:
        if args.check:
            db_path = CHULAN / "db" / f"{db}.db"
            meta = _meta(db_path) if db_path.is_file() else {}
            root = meta.get("root") or discover_root(db) or ""
            if not root or not os.path.isdir(root):
                print(f"{db:16s} — корня нет (пропуск)")
                bad += 1
                continue
            since = float(meta.get("built_at", 0))
            stale = _newest_mtime(root, since) > since + 1
            print(f"{db:16s} {'СТАРАЯ — пересобери: python3 db-tools/fresh.py ' + db if stale else 'свежая'}")
            bad += stale
            continue
        result = ensure(db)
        print(f"{db:16s} {result}")
        bad += result in ("no-meta", "error")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
