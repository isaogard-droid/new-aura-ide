#!/usr/bin/env python3
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Единая самодиагностика AGGG2.0: одна команда — весь чек-лист чулана.

Паттерн wp-cli/doctor: серия проверок, каждая = name + status
(success/warning/error) + человекочитаемое message. Любая error → exit 1.

Запуск:
    python3 scripts/doctor/doctor.py            # все проверки
    python3 scripts/doctor/doctor.py --list     # список проверок
    python3 scripts/doctor/doctor.py mirrors    # только указанные проверки
    python3 scripts/doctor/doctor.py --json     # машинный вывод

Проверки:
    encoding    — проба кодировки (печать ✓ в stdout)
    mirrors     — зеркала AGENTS.md (3 копии идентичны)
    git-untracked — untracked-файлы канона вне git (гейт, research.db id=411)
    venv        — venv проекта и зависимости (mcp + sherpa)
    mcp-opencode— MCP-серверы в конфиге opencode
    mcp-codewhale — MCP-серверы в конфиге codewhale (если харнес есть)
    agent-lsp   — бинарь agent-lsp + LSP-серверы из config.json
    proshivka   — прошивка правил (core.txt/build.txt) == канон harness/
    proshivka-runtime — smoke: ядро реально в системном промпте (--proshivka-runtime)
    tests       — быстрый прогон run_tests.sh --mirrors
    db-phantoms — записи баз без файлов на диске (фантомы в поиске)
    crg-freshness — CRG-граф не отстал от кода (ревью по ложным данным)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _compat

_compat.fix_encoding()

ROOT = _compat.chulan_root()

from doctor_checks_core import (  # noqa: E402,F401 — CHECKS-контракт
    check_crg_freshness,
    check_db_connections,
    check_db_freshness,
    check_db_phantoms,
    check_encoding,
    check_git_untracked,
    check_mirrors,
)
from doctor_checks_ops import (  # noqa: E402,F401 — CHECKS-контракт
    check_agent_lsp,
    check_canon_projects,
    check_context_budget,
    check_dir_limits,
    check_file_sizes,
    check_layer_boundaries,
    check_mcp_codewhale,
    check_mcp_opencode,
    check_proshivka,
    check_proshivka_runtime,
    check_skills_lint,
    check_tests,
    check_venv,
)

CHECKS = [
    ("encoding", "проба кодировки (utf-8)", check_encoding),
    ("mirrors", "зеркала AGENTS.md идентичны", check_mirrors),
    ("git-untracked", "канон не расходится с git (untracked-гейт)", check_git_untracked),
    ("proshivka", "прошивка правил == канон harness/", check_proshivka),
    ("venv", "venv проекта и зависимости", check_venv),
    ("layer-boundaries", "слои не пересекаются (mcp/db-tools/scripts/agent)",
     check_layer_boundaries),
    ("context-budget", "контекст opencode в норме (< 30k токенов)",
     check_context_budget),
    ("dir-limits", "каталоги слоёв ≤ 15 файлов-братьев (docs/canon/ARCHITECTURE.md)",
     check_dir_limits),
    ("mcp-opencode", "MCP-серверы в opencode", check_mcp_opencode),
    ("mcp-codewhale", "MCP-серверы в codewhale", check_mcp_codewhale),
    ("agent-lsp", "agent-lsp и LSP-серверы", check_agent_lsp),
    ("db-freshness", "базы проекта не устарели (stale = ложный ответ)",
     check_db_freshness),
    ("db-phantoms", "в базах нет записей без файлов на диске (фантомы)",
     check_db_phantoms),
    ("db-connections", "мониторинг коннектов: дескрипторы, сироты wal/shm",
     check_db_connections),
    ("crg-freshness", "CRG-граф не отстал от кода (ревью по ложным данным)",
     check_crg_freshness),
    ("tests", "тесты sherpa-voice (mirrors)", check_tests),
    ("canon-projects", "канон без имён проектов (протокол универсален)",
     check_canon_projects),
    ("skills-lint", "скиллы канона валидны по спеке Agent Skills",
     check_skills_lint),
    ("file-sizes", "файлы не переросли лимиты (god-файлы)", check_file_sizes),
    ("proshivka-runtime", "smoke: ядро прошивки в системном промпте (--proshivka-runtime)",
     check_proshivka_runtime),
]


def main():
    ap = argparse.ArgumentParser(description="Диагностика AGGG2.0")
    ap.add_argument("names", nargs="*", help="только эти проверки")
    ap.add_argument("--list", action="store_true", help="список проверок")
    ap.add_argument("--json", action="store_true", help="вывод в JSON")
    ap.add_argument("--proshivka-runtime", action="store_true",
                    help="добавить runtime-smoke прошивки (медленно: opencode run)")
    args = ap.parse_args()

    if args.list:
        for name, desc, _ in CHECKS:
            print(f"{name:14s} {desc}")
        return

    selected = [c for c in CHECKS
                if (not args.names or c[0] in args.names)
                and (c[0] != "proshivka-runtime" or args.proshivka_runtime)]
    if args.json:
        results = []
        for name, _, fn in selected:
            status, msg = fn()
            results.append({"name": name, "status": status, "message": msg})
        print(json.dumps(results, ensure_ascii=False, indent=2))
        sys.exit(1 if any(r["status"] == "error" for r in results) else 0)

    bad = 0
    for name, _desc, fn in selected:
        status, msg = fn()
        mark = {"success": "[✓]", "warning": "[!]", "error": "[✗]"}.get(status, "[?]")
        print(f"{mark} {name:14s} {msg}")
        if status == "error":
            bad += 1
    print(f"\nитого: ошибок {bad}, проверок {len(selected)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)


# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
