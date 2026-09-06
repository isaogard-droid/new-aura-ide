#!/usr/bin/env python3
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты multiorch.py: парсер плана планировщика (JSON, hard cap).

Модели НЕ вызываются — только логика плана.

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools' / 'judge'))
import multiorch as mo


class ParsePlanTest(unittest.TestCase):
    CAP = 5

    def test_valid_plan(self):
        text = ('{"tasks": [{"id": 1, "title": "А", "task": "сделай А"},'
                ' {"id": 2, "title": "Б", "task": "сделай Б"}]}')
        tasks, ok = mo.parse_plan(text, self.CAP)
        self.assertTrue(ok)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]["title"], "А")

    def test_garbage_not_json(self):
        tasks, ok = mo.parse_plan("плана нет", self.CAP)
        self.assertFalse(ok)
        self.assertEqual(tasks, [])

    def test_empty_tasks(self):
        tasks, ok = mo.parse_plan('{"tasks": []}', self.CAP)
        self.assertFalse(ok)

    def test_missing_fields_skipped(self):
        text = ('{"tasks": [{"id": 1, "title": "", "task": "x"},'
                ' {"id": 2, "title": "Ок", "task": "y"}]}')
        tasks, ok = mo.parse_plan(text, self.CAP)
        self.assertTrue(ok)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Ок")

    def test_cap_enforced(self):
        text = '{"tasks": [' + ",".join(
            f'{{"id": {i}, "title": "T{i}", "task": "t{i}"}}' for i in range(1, 10)
        ) + "]}"
        tasks, ok = mo.parse_plan(text, 3)
        self.assertTrue(ok)
        self.assertEqual(len(tasks), 3)

    def test_markdown_wrapped(self):
        text = '```json\n{"tasks": [{"id": 1, "title": "X", "task": "y"}]}\n```'
        tasks, ok = mo.parse_plan(text, self.CAP)
        self.assertTrue(ok)
        self.assertEqual(len(tasks), 1)

    def test_braces_inside_instructions(self):
        text = ('{"tasks": [{"id": 1, "title": "X", '
                '"task": "верни формат {\'issues\': []} и всё"}]}')
        tasks, ok = mo.parse_plan(text, self.CAP)
        self.assertTrue(ok)
        self.assertEqual(len(tasks), 1)
        self.assertIn("issues", tasks[0]["task"])


if __name__ == "__main__":
    unittest.main()

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
