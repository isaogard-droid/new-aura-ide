#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Карта связанности канон-файлов + backlink-поиск (паттерн индустрии:
blast radius для доков, wiki backlinks, CODEOWNERS enforcement).

Зачем: правка одного файла почти всегда тянет связанные (AGENTS.md — три
зеркала, core.txt — разнос по харнесам, db-tools — раздел в docs/canon/DB-FIRST.md).
Модель это забывает — поэтому не «помнить», а сверяться скриптом:
`doc_deps.py check <файл>` отвечает на «кто ссылается / куда разносится /
чем проверить», а backlink-поиск ловит и то, чего нет в карте.

Примеры:
    python3 scripts/tools/audit/doc_deps.py check CYCLE.md
    python3 scripts/tools/audit/doc_deps.py check harness/core.txt
    python3 scripts/tools/audit/doc_deps.py all
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))  # scripts/ — кирпичи канона (_compat)
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # tools/ — соседние кирпичи

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _compat

ROOT = _compat.chulan_root()

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


# Карта: относительный путь (от корня) -> что с ним связано.
# mirrors — файлы-зеркала (править в один заход), sync — скрипт разноса,
# docs — доки, где файл должен быть описан, checks — чем проверить.
DECL = {
    "AGENTS.md": {
        "mirrors": [
            "AGENTS.md",  # сам корень — якорь трёх копий
            "projects/sherpa-voice/AGENTS.md",
        ],
        "sync": "python3 scripts/install/install_agents.py --all",
        "checks": ["projects/sherpa-voice/run_tests.sh --mirrors",
                   "python3 scripts/doctor/doctor.py"],
        "note": "три зеркала (корень, sherpa-voice, ~/.config/opencode) — "
                "правка во всех + разнос по харнесам",
    },
    "CLAUDE.md": {
        "docs": ["AGENTS.md (указатель)", "harness/monolith.md (компакт, "
                 "если менялся характер/ядро)"],
        "sync": "python3 scripts/install/install_proshivka.py (монолит ~/AGENTS.md)",
    },
    "CYCLE.md": {
        "docs": ["AGENTS.md (указатель)", "docs/canon/DB-FIRST.md (ритуалы базы)"],
        "tools": ["db-tools/tasks.py", "db-tools/findings.py"],
    },
    "docs/canon/DB-FIRST.md": {
        "docs": ["AGENTS.md (указатель)"],
        "tools": ["db-tools/build.py", "db-tools/search.py",
                  "db-tools/findings.py", "db-tools/tasks.py"],
    },
    "docs/canon/CAMOUFOX.md": {
        "docs": ["AGENTS.md (указатель)"],
        "tools": ["mcp/camoufox_research.py"],
    },
    "harness/core.txt": {
        "sync": "python3 scripts/install/install_proshivka.py",
        "checks": ["python3 scripts/tests/test_core_integrity.py"],
        "note": "ядро прошивки — разносится во ВСЕ точки (плагин opencode, "
                "хуки, omp, codewhale, reasonix)",
    },
    "harness/hooks/aggg2_prompt_hook.py": {
        "sync": "python3 scripts/install/install_proshivka.py",
        "checks": ["python3 scripts/doctor/doctor.py"],
        "note": "блок-правила сторожа синхронны с harness/opencode/plugins/"
                "proshivka.js",
    },
    "harness/opencode/plugins/proshivka.js": {
        "sync": "python3 scripts/install/install_proshivka.py",
        "checks": ["python3 scripts/doctor/doctor.py"],
        "note": "блок-правила сторожа синхронны с harness/hooks/"
                "aggg2_prompt_hook.py",
    },
    "VERSION": {
        "tools": ["make_archive.sh", "scripts/setup.py"],
        "note": "единая точка версии — сборщик и установщик читают отсюда",
    },
    "make_archive.sh": {
        "checks": ["bash make_archive.sh --list"],
        "note": "сборщик раздаваемого архива — исключения (EXCLUDES) решают, "
                "что увидит получатель; перед правкой этого файла и любых "
                "файлов из потока раздачи — CLAUDE.md п.17",
    },
    "db-tools/tasks.py": {
        "docs": ["docs/canon/DB-FIRST.md (раздел «Журнал задач»)", "CYCLE.md (фазы 0, 8)"],
        "checks": ["ruff check db-tools/tasks.py"],
    },
    "db-tools/findings.py": {
        "docs": ["docs/canon/DB-FIRST.md (раздел находок)"],
        "checks": ["ruff check db-tools/findings.py"],
    },
}

# Где искать backlinks: (корневой путь, маска). Порядок = полнота.
SCAN = [
    ("", "*.md"),
    ("harness", "*.*"),
    ("db-tools", "*.py"),
    ("scripts", "*.py"),
    ("docs", "*.md"),
    ("skills", "*.md"),
]

SKIP_DIRS = {".git", "db", "dist", "venv", "__pycache__", "node_modules",
             ".ruff_cache", "models"}


def _rel(path):
    """Абсолютный или относительный путь -> относительный от корня."""
    path = os.path.abspath(path)
    try:
        rel = os.path.relpath(path, ROOT)
    except ValueError:
        return None
    return rel


def _exists(rel):
    return rel and os.path.isfile(os.path.join(ROOT, rel))


def cmd_check(args):
    rel = _rel(args.file)
    if not rel:
        print(f"[✗] файл вне корня AGGG2.0: {args.file}")
        sys.exit(1)
    if not _exists(rel):
        print(f"[✗] файла нет: {rel}")
        sys.exit(1)
    print(f"СВЯЗАННОЕ для {rel}:\n")
    entry = DECL.get(rel)
    if entry:
        for key, label in (("mirrors", "ЗЕРКАЛА (править в один заход)"),
                           ("sync", "РАЗНОС (запустить)"),
                           ("docs", "ДОКИ (проверить, не надо ли обновить)"),
                           ("tools", "КОД (зависит от этого файла)"),
                           ("checks", "ПРОВЕРКИ (прогнать)")):
            if key in entry:
                print(f"  {label}:")
                vals = entry[key] if isinstance(entry[key], list) \
                    else [entry[key]]
                for v in vals:
                    print(f"    - {v}")
        if "note" in entry:
            print(f"  ПРИМЕЧАНИЕ: {entry['note']}")
    else:
        print("  (в карте нет — только backlinks ниже)")
    print("\n  BACKLINKS (кто упоминает этот файл):")
    name = os.path.basename(rel)
    found = []
    for scan_root, _mask in SCAN:
        base = os.path.join(ROOT, scan_root)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if fn == name:
                    continue  # сам файл — не backlink
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except OSError:
                    continue
                if name in text or rel in text:
                    found.append(_rel(path))
    if found:
        for f in sorted(set(found)):
            print(f"    - {f}")
    else:
        print("    - нет")
    print("\n  В РАЗДАЧЕ (архив получателя):")
    try:
        listing = subprocess.run(
            ["bash", os.path.join(ROOT, "make_archive.sh"), "--list"],
            capture_output=True, text=True, timeout=120)
        shipped = listing.stdout.splitlines()
        if rel.replace("\\", "/") in shipped:
            print("    ⚠ ДА — файл ПОПАДЁТ в раздаваемый архив. Конфиденциальные"
                  " детали и внутренние механизмы — НЕЛЬЗЯ (CLAUDE.md п.17).")
        else:
            print("    нет (исключён сборщиком) — можно писать внутреннее")
    except (OSError, subprocess.TimeoutExpired):
        print("    неизвестно (make_archive.sh не отработал)")
    print("\n  Каждый из списка — кандидат на правку. «Помню» не считается: "
          "открыл, глянул, обновил.")


def cmd_all(args):
    print("КАРТА СВЯЗАННОСТИ КАНОНА:\n")
    for rel, entry in sorted(DECL.items()):
        bits = []
        if "mirrors" in entry:
            bits.append("зеркала")
        if "sync" in entry:
            bits.append("разнос")
        if "docs" in entry:
            bits.append("доки")
        if "tools" in entry:
            bits.append("код")
        print(f"  {rel:45} → {', '.join(bits) if bits else 'backlinks'}")
    print("\nЛюбой файл (не из карты) — `check` даст backlinks по "
          "упоминаниям.\n")


def main():
    ap = argparse.ArgumentParser(
        description="Связанность канон-файлов: кто ссылается, куда разносить")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_check = sub.add_parser("check", help="связанное для одного файла")
    p_check.add_argument("file", help="путь к файлу (от корня или абсолютный)")
    p_check.set_defaults(fn=cmd_check)
    p_all = sub.add_parser("all", help="вся карта связанности")
    p_all.set_defaults(fn=cmd_all)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()


# Оригинал от https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна и лучше предыдущей.

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
