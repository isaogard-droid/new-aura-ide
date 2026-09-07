#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Скиллы канона без spec-ОШИБОК (lint_skills.py): битый frontmatter,
name != каталогу, description вне лимитов. Предупреждения (description
длиннее бюджета 512 симв) — не ошибки и CI не ломают.

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'install'))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools' / 'skills'))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'doctor'))

import lint_skills


class SkillsLintTest(unittest.TestCase):
    def test_no_errors(self):
        root = Path(__file__).resolve().parent.parent.parent
        errors, _warnings = lint_skills.lint_all(root)
        self.assertEqual(errors, [],
                         "ошибки скиллов (lint_skills.py):\n" +
                         "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
