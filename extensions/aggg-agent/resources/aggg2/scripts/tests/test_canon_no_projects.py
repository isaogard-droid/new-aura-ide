#!/usr/bin/env python3
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Канон без имён проектов: протокол AGGG не хардкодит конкретные проекты.

Ловит класс косяка 14.08.2026 (research.db id=484/485): правило/путь
конкретного проекта, прошитое в канон-док (пример косяка:
`projects/sherpa-voice/docs/PRODUCT.md` в docs/canon/DB-FIRST.md). Правило канона:
протокол — универсальный, без имён проектов; проект-специфика — только
в файлах самого проекта (CLAUDE.md/AGENTS.md «Думай ПЕРЕД правкой»).

Две проверки:
  A. Пути ВНУТРЬ проекта запрещены в каноне: `projects/<имя>/<подпуть>`
     для ЛЮБОГО имени (ловит и будущие проекты); разрешены только
     зеркальные файлы проекта (AGENTS.md, run_tests.sh).
  B. Упоминания sherpa-voice — только по белому списку контекстов
     (имя базы, кэш истории, зеркала, проза «проект sherpa-voice»,
     корень проекта в примерах команд).

Запуск: python3 scripts/tests/test_canon_no_projects.py
В doctor.py: check_canon_projects (subprocess этого файла).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANON_FILES = ["AGENTS.md", "CLAUDE.md", "CYCLE.md", "docs/canon/CAMOUFOX.md",
               "docs/canon/DB-FIRST.md", "docs/canon/AGENT-LSP.md", "docs/canon/CODE-GRAPH.md"]
# Разрешённые файлы проекта в путях канона (механика зеркал — структурная,
# не правила проекта):
ALLOWED_PROJECT_FILES = {"AGENTS.md", "run_tests.sh"}
# Белый список контекстов для «sherpa-voice»: подстроки (точные) + regex
# (склонения). Каждая запись — осознанное исключение: структурная ссылка,
# не правило проекта.
SHERPA_WHITELIST_SUB = [
    "sherpa-voice.db",                 # имя базы проекта (структура воркспейса)
    "~/.cache/sherpa-voice",           # кэш/история транскриптов
    "projects/sherpa-voice/AGENTS.md",     # зеркало канона
    "projects/sherpa-voice/run_tests.sh",  # проверка зеркал
    "(sherpa-voice)",                  # скобочное пояснение про зеркала
    "projects/sherpa-voice ",          # корень проекта в примерах команд
]
SHERPA_WHITELIST_RE = [
    # проза «что покрывает база»: «проект/проекта/проектом/... sherpa-voice»
    re.compile(r"проект[а-яё]{0,3}\s+sherpa-voice"),
]
DEEP_PATH = re.compile(r"projects/[A-Za-z0-9_.-]+/([A-Za-z0-9_.-]+)")


def _sherpa_allowed(line):
    return (any(w in line for w in SHERPA_WHITELIST_SUB)
            or any(r.search(line) for r in SHERPA_WHITELIST_RE))


def canon_lines():
    """(имя_файла, номер_строки, строка) по всем канон-докам."""
    for name in CANON_FILES:
        path = ROOT / name
        if not path.exists():
            continue
        for i, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1):
            yield name, i, line


class CanonNoProjectsTest(unittest.TestCase):
    def test_no_deep_project_paths(self):
        for name, i, line in canon_lines():
            for m in DEEP_PATH.finditer(line):
                sub = m.group(1)
                self.assertIn(
                    sub, ALLOWED_PROJECT_FILES,
                    f"{name}:{i}: путь внутрь проекта в каноне запрещён: "
                    f"{m.group(0)} — разрешены только зеркала "
                    f"(AGENTS.md/run_tests.sh); проект-специфика — в файлы "
                    f"самого проекта")

    def test_sherpa_mentions_whitelisted(self):
        for name, i, line in canon_lines():
            if "sherpa-voice" not in line:
                continue
            self.assertTrue(
                _sherpa_allowed(line),
                f"{name}:{i}: упоминание sherpa-voice вне белого списка: "
                f"{line.strip()[:90]} — канон это протокол без имён "
                f"проектов; осознанное исключение — в SHERPA_WHITELIST_*, "
                f"иначе правило переносится в файлы проекта")


if __name__ == "__main__":
    unittest.main()

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
