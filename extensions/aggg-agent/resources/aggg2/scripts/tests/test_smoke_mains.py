#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Smoke-тесты main() CLI-скриптов чулана: --help/--list должны отработать
без ошибок (argparse-проводка живая, импорты на месте). Закрывает CRG-gaps
«untested hotspots» — main-функции установщиков/эвал-скриптов без тестов
(аудит 14.08.2026, research.db id=489). Не проверяем поведение — это зона
юнит-тестов соответствующих модулей.

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# (скрипт, аргументы) — минимальный прогон без побочных эффектов.
# --help/--list уходят в argparse и выходят до любой реальной работы.
# gen_index/lint_wiki argparse НЕ имеют (позиционный путь-к-Wiki, флаги
# фильтруются вручную) — их smoke: --dry-run (без записи) и дефолтный
# путь (lint не пишет, только читает).
SMOKE = [
    ("scripts/tools/judge/multimodel_judge.py", ["--help"]),
    ("scripts/install/install_agents.py", ["--help"]),
    ("scripts/setup.py", ["--help"]),
    ("scripts/doctor/doctor.py", ["--list"]),
    ("scripts/eval/eval_skill_triggers.py", ["--help"]),
    ("scripts/eval/eval_doc_triggers.py", ["--help"]),
    ("db-tools/findings.py", ["--help"]),
    ("db-tools/build.py", ["--help"]),
    ("db-tools/search.py", ["--help"]),
    ("skills/wiki-karpathy/scripts/gen_index.py", ["--dry-run"]),
    ("skills/wiki-karpathy/scripts/lint_wiki.py", []),
    ("scripts/tools/skills/lint_skills.py", ["--help"]),
    ("scripts/install/install_lsp_servers.py", ["--help"]),
    ("scripts/install/install_mcp.py", ["--help"]),
    ("scripts/tools/judge/multiorch.py", ["--help"]),
    ("scripts/tools/audit/check_file_sizes.py", ["--help"]),
    ("scripts/install/toggle_proshivka.py", ["--help"]),
    ("scripts/install/update_camoufox.py", ["--help"]),
    ("db-tools/tasks.py", ["--help"]),
    ("db-tools/githist.py", ["--help"]),
    ("db-tools/repomap.py", ["--help"]),
    ("db-tools/search_all.py", ["--help"]),
    ("db-tools/knowledge/extract_findings.py", ["--help"]),
]


class SmokeMainsTest(unittest.TestCase):
    """Каждый CLI-скрипт отвечает на --help/--list без падения."""

    def test_help_exits_zero(self):
        for rel, argv in SMOKE:
            script = ROOT / rel
            with self.subTest(script=rel):
                if not script.is_file():
                    self.fail(f"скрипт не найден: {rel}")
                try:
                    proc = subprocess.run(
                        [sys.executable, str(script)] + argv,
                        capture_output=True, text=True,
                        timeout=60, cwd=str(ROOT))
                except subprocess.TimeoutExpired:
                    self.fail(f"таймаут 60с: {rel}")
                out = (proc.stdout or "") + (proc.stderr or "")
                self.assertEqual(proc.returncode, 0,
                                 f"{rel} {argv}: rc={proc.returncode}\n"
                                 f"вывод: {out[:300]}")


if __name__ == "__main__":
    unittest.main()
