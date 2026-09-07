#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Регрессия «Wiki ищется ВСЕГДА»: секция «📚 Wiki (ищи всегда)»
присоединяется к каждому поиску search.py — и в ветке результатов, и в
ветке «ничего не найдено»; при поиске в самой wiki.db — нет (дедуп).
Изоляция: AGGG2_ROOT в throwaway-дерево (VERSION + db-tools/ +
scripts/_compat.py — маркеры chulan_root), базы собираются build.py
по временным каталогам. Продакшн-базы не читаются и не пишутся.

Имена тестов = спека:
  test_wiki_section_in_found_result — нашлось и в проекте, и в Wiki →
      секция есть, заголовок поста из frontmatter
  test_wiki_section_in_empty_result — нашлось только в Wiki →
      секция есть в ветке «ничего не найдено»
  test_wiki_db_itself_no_section — поиск в самой wiki.db → секции нет

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SEARCH = ROOT / "db-tools" / "search.py"
BUILD = ROOT / "db-tools" / "build.py"

WIKI_SECTION = "📚 Wiki (ищи всегда):"
QUERY_BOTH = "виксекция"
QUERY_WIKI_ONLY = "куккаредо"
POST_TITLE = "Тестовый пост виксекция"


def _run(script, argv, root):
    proc = subprocess.run(
        [sys.executable, str(script)] + argv,
        capture_output=True, text=True, timeout=60, cwd=str(ROOT),
        env={**os.environ, "AGGG2_ROOT": str(root)}, check=False)
    return proc.returncode, proc.stdout, proc.stderr


class WikiSectionTest(unittest.TestCase):
    """Секция Wiki в выводе search.py на изолированном дереве."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "VERSION").write_text("test\n", encoding="utf-8")
        (self.root / "db-tools").mkdir()
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "_compat.py").write_text(
            "# маркер корня (реальный _compat импортируется из scripts/)\n",
            encoding="utf-8")
        wiki_dir = self.root / "Wiki" / "tools"
        wiki_dir.mkdir(parents=True)
        (wiki_dir / "test-post.md").write_text(
            "---\n"
            "type: Post\n"
            f"title: {POST_TITLE}\n"
            "description: регрессионный тест wiki-секции\n"
            "date: 2026-08-16\n"
            "tags: [tools, test]\n"
            "---\n"
            f"Текст поста: {QUERY_BOTH} и {QUERY_WIKI_ONLY}.\n",
            encoding="utf-8")
        proj_dir = self.root / "proj"
        proj_dir.mkdir()
        (proj_dir / "readme.md").write_text(
            f"# Проект\nфайл проекта с токеном {QUERY_BOTH}.\n",
            encoding="utf-8")
        db_dir = self.root / "db"
        db_dir.mkdir()
        for src, name in ((self.root / "Wiki", "wiki"), (proj_dir, "proj")):
            rc, out, err = _run(
                BUILD,
                ["-r", str(src), "-o", str(db_dir / f"{name}.db")],
                self.root)
            self.assertEqual(rc, 0, f"build {name}: {err or out[:300]}")

    def tearDown(self):
        self.tmp.cleanup()

    def test_wiki_section_in_found_result(self):
        rc, out, err = _run(
            SEARCH,
            ["-b", str(self.root / "db" / "proj.db"), "--no-log", QUERY_BOTH],
            self.root)
        self.assertEqual(rc, 0, f"search: {err}")
        self.assertIn("найдено", out)
        self.assertIn(WIKI_SECTION, out,
                      "секция Wiki обязана быть в ветке результатов")
        self.assertIn(POST_TITLE, out,
                      "заголовок поста берётся из frontmatter (title:)")

    def test_wiki_section_in_empty_result(self):
        rc, out, err = _run(
            SEARCH,
            ["-b", str(self.root / "db" / "proj.db"), "--no-log",
             QUERY_WIKI_ONLY],
            self.root)
        self.assertEqual(rc, 0, f"search: {err}")
        self.assertIn("ничего не найдено", out)
        self.assertIn(WIKI_SECTION, out,
                      "секция Wiki обязана быть и в ветке пустого результата")

    def test_wiki_db_itself_no_section(self):
        rc, out, err = _run(
            SEARCH,
            ["-b", str(self.root / "db" / "wiki.db"), "--no-log", QUERY_BOTH],
            self.root)
        self.assertEqual(rc, 0, f"search: {err}")
        self.assertIn("test-post.md", out, "пост должен найтись в самой wiki")
        self.assertNotIn(WIKI_SECTION, out,
                         "в самой wiki.db секция не дублируется")


if __name__ == "__main__":
    unittest.main()
