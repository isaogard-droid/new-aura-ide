#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты findings.py: CRUD находок, связи, поиск, статистика.

База подменяется на временную (findings.DB), реальный research.db не трогаем.

Запуск (из корня AGGG2.0):
    python3 -m unittest discover -s db-tools/tests -t .
"""
import argparse
import io
import os

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import findings


def ns(**kw):
    return argparse.Namespace(**kw)


def capture(fn, *args):
    """Вызывает fn(*args), возвращает (stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        fn(*args)
    return out.getvalue(), err.getvalue()


class FindingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        findings.DB = os.path.join(self.tmp, "research-test.db")
        # свежая база для каждого теста

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _add(self, topic="тема про тест", text="вывод: всё работает",
             tags="a b", source="", related=""):
        return capture(findings.cmd_add,
                       ns(topic=topic, text=text, tags=tags,
                          source=source, related=related))

    def test_add_and_search(self):
        out, _ = self._add()
        self.assertIn("id=1", out)
        out, _ = capture(findings.cmd_search, ns(query="тема", limit=10))
        self.assertIn("тема про тест", out)
        self.assertIn("[1]", out)

    def test_add_duplicate_warns(self):
        self._add()
        _, err = self._add(topic="тема про тест")
        self.assertIn("уже есть находка", err)

    def test_add_related_creates_link(self):
        self._add(topic="первая")
        self._add(topic="вторая", related="1")
        con = findings.connect()
        try:
            n = con.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        finally:
            con.close()
        self.assertEqual(n, 1)

    def test_list_and_filter_by_tags(self):
        self._add(tags="ai agents")
        self._add(topic="другая", tags="tools")
        out, _ = capture(findings.cmd_list, ns(tags="", limit=20))
        self.assertIn("всего: 2", out)
        out, _ = capture(findings.cmd_list, ns(tags="ai", limit=20))
        self.assertIn("тема про тест", out)
        self.assertNotIn("другая", out)

    def test_search_filter_by_source_and_tag(self):
        """Фильтры search: --source (подстрока) и --tag (точное слово)."""
        self._add(source="https://example.com/post-1")
        self._add(topic="другая находка", text="совсем иное",
                  tags="tools", source="docs/research/scratch.md")
        out, _ = capture(findings.cmd_search,
                         ns(query="находка", limit=10, source="", tag=""))
        self.assertIn("другая находка", out)
        out, _ = capture(findings.cmd_search,
                         ns(query="находка", limit=10, source="scratch",
                            tag=""))
        self.assertIn("другая находка", out)
        self.assertNotIn("тема про тест", out)
        out, _ = capture(findings.cmd_search,
                         ns(query="находка", limit=10, source="",
                            tag="tools"))
        self.assertIn("другая находка", out)
        self.assertNotIn("тема про тест", out)
        out, _ = capture(findings.cmd_search,
                         ns(query="находка", limit=10, source="",
                            tag="нет-такого"))
        self.assertIn("ничего не найдено", out)

    def test_edit(self):
        self._add()
        out, _ = capture(findings.cmd_edit,
                         ns(id=1, topic="новая тема", text=None,
                            tags=None, source=None))
        self.assertIn("обновлено: id=1", out)
        con = findings.connect()
        try:
            row = con.execute("SELECT topic FROM findings WHERE id=1").fetchone()
        finally:
            con.close()
        self.assertEqual(row["topic"], "новая тема")

    def test_show(self):
        self._add(text="детальный вывод про X")
        out, _ = capture(findings.cmd_show, ns(id=1))
        self.assertIn("детальный вывод про X", out)
        self.assertIn("теги: a b", out)

    def test_del(self):
        self._add()
        out, _ = capture(findings.cmd_del, ns(id=1))
        self.assertIn("удалено: id=1", out)
        out, _ = capture(findings.cmd_del, ns(id=1))
        self.assertIn("нет", out)
        con = findings.connect()
        try:
            n = con.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        finally:
            con.close()
        self.assertEqual(n, 0)

    def test_links_lifecycle(self):
        self._add(topic="первая")
        self._add(topic="вторая")
        out, _ = capture(findings.cmd_link_add,
                         ns(from_id=1, to_id=2, kind="related", note="связь"))
        self.assertIn("связь: 1 --related--> 2", out)
        out, _ = capture(findings.cmd_link_list, ns(id=1))
        self.assertIn("вторая", out)
        out, _ = capture(findings.cmd_related, ns(id=2))
        self.assertIn("первая", out)
        # удаление связи
        out, _ = capture(findings.cmd_link_rm, ns(id=1))
        self.assertIn("связь удалена", out)
        out, _ = capture(findings.cmd_link_list, ns(id=1))
        self.assertIn("связей нет", out)

    def test_link_to_missing_fails(self):
        self._add()
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit):
            findings.cmd_link_add(
                ns(from_id=1, to_id=99, kind="related", note=""))
        self.assertIn("находки с id=99 нет", err.getvalue())

    def test_stats(self):
        self._add()
        self._add(topic="вторая")
        self._add(topic="третья", related="1, 2")
        out, _ = capture(findings.cmd_stats, ns())
        self.assertIn("находок: 3", out)
        self.assertIn("связей: 2", out)

    def test_parse_ids(self):
        self.assertEqual(findings._parse_ids("1,2, 3"), [1, 2, 3])
        self.assertEqual(findings._parse_ids("a, 5, x"), [5])
        self.assertEqual(findings._parse_ids(""), [])

    def test_sanitize_query(self):
        # операторы не трогаем
        self.assertEqual(findings.sanitize_query("токен AND шкала"),
                         "токен AND шкала")
        # спецсимволы оборачиваем (грабля «agent-lsp»)
        self.assertEqual(findings.sanitize_query("agent-lsp"),
                         '"agent-lsp"')
        # префикс-поиск не оборачиваем
        self.assertEqual(findings.sanitize_query("подмешк*"), "подмешк*")


class FindingsStatusTest(unittest.TestCase):
    """supersede/consolidate/фильтры статуса (ретракшн и консолидация)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        findings.DB = os.path.join(self.tmp, "research-test.db")
        capture(findings.cmd_add, ns(topic="активная", text="текст",
                                     tags="t", source="", related=""))
        capture(findings.cmd_add, ns(topic="старая", text="текст",
                                     tags="t", source="", related=""))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_supersede_hides_from_live(self):
        out, _ = capture(findings.cmd_supersede,
                         ns(id=1, note="опровергнуто"))
        self.assertIn("superseded: id=1", out)
        out, _ = capture(findings.cmd_search, ns(query="активная",
                                                 limit=10, source="",
                                                 tag="", status="live"))
        self.assertNotIn("[1]", out)
        out, _ = capture(findings.cmd_search, ns(query="активная",
                                                 limit=10, source="",
                                                 tag="", status="all"))
        self.assertIn("[1]", out)

    def test_supersede_appends_note(self):
        capture(findings.cmd_supersede, ns(id=1, note="устарело"))
        out, _ = capture(findings.cmd_show, ns(id=1))
        self.assertIn("[superseded]", out)
        self.assertIn("устарело", out)

    def _backdate(self, fid, days=40):
        """Создаёт created находки в прошлом (для consolidate-тестов)."""
        con = findings.connect()
        try:
            con.execute(
                "UPDATE findings SET created = date('now', ?) WHERE id = ?",
                (f"-{days} days", fid))
            con.commit()
        finally:
            con.close()

    def test_consolidate_preview_no_apply(self):
        self._backdate(2)
        out, _ = capture(findings.cmd_consolidate, ns(days=30, apply=False,
                                                      id=None))
        self.assertIn("кандидаты на архив", out)
        self.assertIn("[2]", out)

    def test_consolidate_apply_archives(self):
        self._backdate(2)
        out, _ = capture(findings.cmd_consolidate, ns(days=30, apply=True,
                                                      id=None))
        self.assertIn("заархивировано", out)
        out, _ = capture(findings.cmd_search, ns(query="старая", limit=10,
                                                 source="", tag="",
                                                 status="live"))
        self.assertNotIn("[2]", out)
        out, _ = capture(findings.cmd_search, ns(query="старая", limit=10,
                                                 source="", tag="",
                                                 status="archived"))
        self.assertIn("[2]", out)

    def test_consolidate_by_id(self):
        out, _ = capture(findings.cmd_consolidate,
                         ns(days=30, apply=True, id=[2]))
        self.assertIn("archived: id=2", out)

    def test_list_shows_status_badge(self):
        capture(findings.cmd_supersede, ns(id=1, note=""))
        out, _ = capture(findings.cmd_list, ns(tags="", limit=20,
                                               status="all"))
        self.assertIn("[superseded]", out)


if __name__ == "__main__":
    unittest.main()

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
