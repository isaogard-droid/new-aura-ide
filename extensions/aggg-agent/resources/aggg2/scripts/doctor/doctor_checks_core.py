# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie

"""doctor_checks_core — базовые проверки AGGG2.0: encoding, зеркала,
git-untracked, свежесть баз, фантомы, CRG-граф.

Вынесено из doctor.py механически (verbatim) — гейт god-файлов."""
import os
import shutil
import sqlite3
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
from pathlib import Path

import _compat  # noqa: F401 — ROOT + fix_encoding

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_compat.fix_encoding()
ROOT = _compat.chulan_root()

def _sh(cmd, timeout=120):
    try:
        r = _compat.run(cmd, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


def check_encoding():
    return "success", "stdout utf-8: ✓ кириллица работает"


def check_mirrors():
    mirrors = [
        ROOT / "AGENTS.md",
        Path.home() / ".config" / "opencode" / "AGENTS.md",
    ]
    # 3-е зеркало живёт во ВЛОЖЕННОМ репо (projects/sherpa-voice/),
    # который корневой .gitignore исключает из checkout: на CI каталога
    # нет — зеркало сверяем только при его наличии (кейс setup-test 14.08).
    sv = ROOT / "projects" / "sherpa-voice" / "AGENTS.md"
    if (ROOT / "projects" / "sherpa-voice").is_dir():
        mirrors.append(sv)
    missing = [str(p) for p in mirrors if not p.is_file()]
    if missing:
        return "error", f"нет файлов: {', '.join(missing)}"
    first = mirrors[0].read_bytes()
    for p in mirrors[1:]:
        if p.read_bytes() != first:
            return "error", f"расходится: {p}"
    return "success", f"{len(mirrors)} зеркала идентичны"


def _canon_like(path: str) -> bool:
    """Похоже на файл канона, который должен жить в git (а не на мусор)."""
    if "/" in path:
        return path.split("/", 1)[0] in {"skills", "scripts", "harness",
                                         "agent", "mcp", "db-tools", "docs",
                                         "Wiki", "projects", "tests"}
    return path.endswith((".md", ".py", ".sh", ".ps1", ".toml", ".txt",
                          ".yml", ".yaml", ".jsonc", ".js")) \
        or path in {".gitignore", "VERSION"}


def check_git_untracked():
    """Гейт: untracked-файлы канона вне git. Воркспейс рос быстрее git —
    скиллы/скрипты/доки добавлялись без git add (аудит 13.08.2026,
    research.db id=411). Ловит «?? файлы», похожие на канон: их либо
    git add, либо в .gitignore. git не найден/не репозиторий — пропуск
    (git опционален, docs/canon/SETUP.md «Требования к системе»)."""
    git = shutil.which("git")
    if not git:
        return "warning", "git не найден — проверка untracked пропущена"
    repos = [ROOT]
    child = ROOT / "projects" / "sherpa-voice"
    if (child / ".git").exists():
        repos.append(child)
    caught = []
    for repo in repos:
        rc, out = _sh([git, "-C", str(repo), "status", "--porcelain"], timeout=30)
        if rc != 0:
            continue  # не репозиторий — пропускаем тихо
        prefix = "" if repo == ROOT else f"{repo.name}/"
        for ln in out.splitlines():
            if ln.startswith("?? ") and _canon_like(ln[3:].strip().rstrip("/")):
                caught.append(prefix + ln[3:].strip().rstrip("/"))
    if caught:
        shown = ", ".join(caught[:6]) + ("…" if len(caught) > 6 else "")
        return ("warning",
                f"{len(caught)} untracked-файлов канона вне git → git add или "
                f"в .gitignore: {shown}")
    return "success", "untracked-файлов канона нет — всё в git"


def check_db_freshness():
    """Базы проекта не устарели относительно файлов: mtime базы vs самый
    новый файл её корня. Устаревшая база = ложный ответ (канон DB-FIRST,
    паттерн Zoekt-indexserver: актуальность поддерживается переиндексацией,
    а не по памяти)."""
    pairs = [
        ("db/aggg2.db", "."),
        ("db/sherpa-voice.db", "projects/sherpa-voice"),
        ("db/wiki.db", "Wiki"),
    ]
    skip = {".git", "db", "venv", "dist", "__pycache__", "node_modules",
            ".ruff_cache", "models", ".code-review-graph"}
    stale = []
    for db_rel, scan_root in pairs:
        db = ROOT / db_rel
        if not db.is_file():
            continue  # базы может ещё не быть — не ошибка
        newest = 0.0
        base = ROOT / scan_root
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for fn in filenames:
                try:
                    newest = max(newest, os.path.getmtime(
                        os.path.join(dirpath, fn)))
                except OSError:
                    continue
        if newest and db.stat().st_mtime + 120 < newest:
            stale.append(f"{db_rel} (старше самого нового файла на "
                         f"{int((newest - db.stat().st_mtime) / 60)} мин)")
    if stale:
        return "warning", "; ".join(stale) + " → python3 db-tools/search.py --refresh"
    # githist: последний коммит в базе vs HEAD (stale история = ложный ответ)
    hist_stale = []
    try:
        con = sqlite3.connect(os.path.join(ROOT, "db", "research.db"))
        try:
            max_date = con.execute(
                "SELECT MAX(date) FROM commits").fetchone()[0]
        finally:
            con.close()
        if max_date:
            head = _compat.run(
                ["git", "-C", str(ROOT), "log", "-1",
                 "--pretty=format:%ai"], timeout=30)
            if head.returncode == 0 and head.stdout.strip()[:19] > max_date:
                hist_stale.append(
                    f"githist (база: {max_date[:10]}, HEAD: "
                    f"{head.stdout.strip()[:10]})")
    except (sqlite3.Error, OSError):
        pass
    if hist_stale:
        return "warning", "; ".join(hist_stale) + \
            " → python3 db-tools/githist.py refresh"
    return "success", "базы проекта свежие (не старше файлов)"


def check_db_phantoms():
    """Фантомы в базах: запись есть, а файла на диске нет. mtime-проверка
    (db-freshness) их не видит — база новее файлов проходит, а призрачные
    записи остаются в поиске (кейс: Wiki/index.md.bak пережил удаление файла
    в wiki.db, аудит 14.08.2026, research.db id=489).
    Починка: python3 db-tools/search.py --refresh (инкрементально удаляет
    исчезнувшие файлы)."""
    pairs = [
        ("db/aggg2.db", ROOT),
        ("db/sherpa-voice.db", ROOT / "projects" / "sherpa-voice"),
        ("db/wiki.db", ROOT / "Wiki"),
    ]
    phantoms = []
    for db_rel, base in pairs:
        db = ROOT / db_rel
        if not db.is_file():
            continue  # базы может ещё не быть — не ошибка
        try:
            con = sqlite3.connect(str(db))
            try:
                rows = con.execute("SELECT rel_path FROM files").fetchall()
            finally:
                con.close()
        except sqlite3.Error as e:
            return "error", f"{db_rel}: {e}"
        for (rel_path,) in rows:
            p = Path(rel_path)
            candidate = p if p.is_absolute() else base / p
            if not candidate.is_file():
                phantoms.append(f"{db_rel}: {rel_path}")
    if phantoms:
        shown = ", ".join(phantoms[:5]) + ("…" if len(phantoms) > 5 else "")
        return ("warning",
                f"{len(phantoms)} фантомов (файла нет на диске): {shown} "
                "→ python3 db-tools/search.py --refresh")
    return "success", "фантомов в базах нет (записи ⊆ файлы на диске)"


def _scan_holders(dbs):
    """Кто из живых процессов держит дескрипторы баз (включая -wal/-shm).
    /proc/<pid>/fd без внешних зависимостей (паттерн Substrata9
    find_fd_leak.sh). Возвращает {база: {pid, ...}}."""
    held = {}
    for pid_dir in Path("/proc").glob("[0-9]*"):
        fd_dir = pid_dir / "fd"
        try:
            links = os.listdir(fd_dir)
        except OSError:
            continue  # чужой процесс — не видим, не наша зона
        for fd in links:
            try:
                target = os.readlink(fd_dir / fd)
            except OSError:
                continue
            base = os.path.basename(target.removesuffix(" (deleted)"))
            if base.endswith(("-wal", "-shm")):
                base = base[:-4]  # держат журнал/индекс — тот же коннект
            if base in dbs:
                held.setdefault(base, set()).add(pid_dir.name)
    return held


def check_db_connections():
    """Мониторинг коннектов к базам db/: какие живые процессы держат
    дескрипторы, есть ли сиротские -wal/-shm (нет держателя = след
    нечистого завершения), не разросся ли -wal (незакоммиченные кадры).
    Паттерн ОС-мониторинга (Substrata9 find_fd_leak.sh, кейс hermes-agent:
    EMFILE на 981/1024 утёкших дескрипторов) — /proc/<pid>/fd без внешних
    зависимостей. Держатель считается только при ПОВТОРНОМ обнаружении
    (двойной скан через 150мс): короткоживущие коннекты наших же
    пересборок (fresh.py/build.py — миллисекунды) не дают ложных
    предупреждений. Windows/macOS (/proc нет) — проверка не применима."""
    if os.name == "nt" or not Path("/proc").is_dir():
        return "info", "не применимо (нет /proc — только Linux)"
    db_dir = ROOT / "db"
    if not db_dir.is_dir():
        return "success", "каталог db/ ещё не создан"
    dbs = {f for f in os.listdir(db_dir) if f.endswith(".db")}
    held = _scan_holders(dbs)
    if held:
        time.sleep(0.15)
        held2 = _scan_holders(dbs)
        held = {db: pids & held2.get(db, set())
                for db, pids in held.items() if db in held2 and pids}
        held = {db: pids for db, pids in held.items() if pids}
    orphans = []
    big_wal = []
    for f in sorted(os.listdir(db_dir)):
        if ((f.endswith(".db-wal") or f.endswith(".db-shm"))
                and f[:-4] not in held):
            orphans.append(f)
        if f.endswith(".db-wal"):
            p = db_dir / f
            if p.stat().st_size > 5 * 1024 * 1024:
                big_wal.append(f"{f} ({p.stat().st_size // 1024} КБ)")
    msgs = []
    if held:
        shown = "; ".join(
            f"{db}: pid {','.join(sorted(pids))}" for db, pids in
            sorted(held.items())[:5])
        msgs.append(f"открытые дескрипторы: {shown}")
    if orphans:
        msgs.append("сиротские wal/shm (нет держателя, счистятся при "
                    f"следующем чистом открытии): {', '.join(orphans[:5])}")
    if big_wal:
        msgs.append("разросшийся WAL: " + ", ".join(big_wal))
    if not msgs:
        return "success", (f"коннектов нет: 0 дескрипторов на "
                           f"{len(dbs)} баз, сиротских wal/shm нет")
    if big_wal:
        return "warning", " | ".join(msgs) + " → check db-connections"
    return "info", " | ".join(msgs)


def _crg_graph_state(repo):
    """(store, git_head_sha, last_updated) из метаданных CRG-графа репо.
    Граф лежит в <repo>/.code-review-graph/graph.db (CRG хранит граф рядом
    с корнем репо, ~/.code-review-graph/graph.db — пустой дефолт)."""
    store = repo / ".code-review-graph" / "graph.db"
    if not store.is_file():
        return store, None, None
    try:
        con = sqlite3.connect(str(store))
        try:
            meta = dict(con.execute(
                "SELECT key, value FROM metadata").fetchall())
        finally:
            con.close()
    except sqlite3.Error:
        return store, None, None
    return store, meta.get("git_head_sha"), meta.get("last_updated")


def check_crg_freshness():
    """CRG-граф не отстал от кода: ревью диффа по устаревшему графу = ложный
    анализ (docs/canon/CODE-GRAPH.md «граф пересобран — данные устарели = ложный
    анализ»). Сигналы: (1) git_head_sha графа vs HEAD репо — ловит
    закоммиченные изменения; (2) mtime графа vs самый новый из
    ПРОИНДЕКСИРОВАННЫХ графом файлов — ловит незакоммиченные правки.
    Кейс 14.08.2026 (research.db id=489): граф отставал от HEAD на день,
    head_matches_build=false.
    Починка: MCP code-review-graph → build_or_update_graph_tool."""
    git = shutil.which("git")
    repos = [ROOT]
    child = ROOT / "projects" / "sherpa-voice"
    if (child / ".git").exists():
        repos.append(child)
    stale = []
    for repo in repos:
        store, graph_sha, _updated = _crg_graph_state(repo)
        if not store.is_file():
            continue  # граф ещё не построен — не ошибка
        # (1) закоммиченное: sha графа vs HEAD
        if git and graph_sha:
            rc, out = _sh([git, "-C", str(repo), "rev-parse", "HEAD"],
                          timeout=30)
            if rc == 0 and out.strip() != graph_sha:
                stale.append(f"{repo.name}: граф от sha {graph_sha[:8]}, "
                             f"HEAD {out.strip()[:8]}")
                continue
        # (2) незакоммиченное: mtime графа vs проиндексированные файлы
        newest = 0.0
        try:
            con = sqlite3.connect(str(store))
            try:
                paths = [r[0] for r in con.execute(
                    "SELECT DISTINCT file_path FROM nodes").fetchall()]
            finally:
                con.close()
            for p in paths:
                try:
                    newest = max(newest, os.path.getmtime(p))
                except OSError:
                    continue
        except sqlite3.Error:
            continue
        if newest and store.stat().st_mtime + 120 < newest:
            stale.append(f"{repo.name}: граф старше кода на "
                         f"{int((newest - store.stat().st_mtime) / 60)} мин")
    if stale:
        return ("warning", "; ".join(stale) +
                " → code-review-graph mcp: build_or_update_graph_tool")
    return "success", "CRG-графы свежие (не отстали от кода)"

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
