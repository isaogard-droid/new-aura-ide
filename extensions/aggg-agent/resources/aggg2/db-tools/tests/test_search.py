#!/usr/bin/env python3
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты search.py: санитизация запросов, cmd_* на временной базе,
регрессия CLI (флаги после рефакторинга main → cmd_*).

Запуск (из корня AGGG2.0):
    python3 -m unittest discover -s db-tools/tests -t .
"""
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import argparse

import build
import search

PROJ = {
    "app.py": (
        "import os\n"
        "\n"
        "def greet(name):\n"
        "    return f\"hi {name}\"\n"
        "\n"
        "class Base:\n"
        "    pass\n"
        "\n"
        "class Child(Base):\n"
        "    def run(self):\n"
        "        return greet(\"x\")\n"
    ),
    "mod.py": (
        "from app import Child\n"
        "\n"
        "c = Child()\n"
        "c.run()\n"
    ),
    "broken.py": "def f(:\n",
}


class SanitizeTest(unittest.TestCase):
    def test_operators_untouched(self):
        self.assertEqual(search.sanitize_query("токен AND шкала"),
                         "токен AND шкала")
        self.assertEqual(search.sanitize_query("a OR b NOT c"),
                         "a OR b NOT c")
        self.assertEqual(search.sanitize_query("x NEAR(y)"), "x NEAR(y)")

    def test_special_chars_quoted(self):
        self.assertEqual(search.sanitize_query("agent-lsp"), '"agent-lsp"')
        # токен со скобками оборачивается; простой токен — нет
        self.assertEqual(search.sanitize_query("a (b)"), 'a "(b)"')
        self.assertEqual(search.sanitize_query('кавычка"внутри'),
                         '"кавычка""внутри"')

    def test_prefix_not_quoted(self):
        self.assertEqual(search.sanitize_query("подмешк*"), "подмешк*")
        # сложный префикс с дефисом всё же экранируем
        self.assertNotEqual(search.sanitize_query("agent-lsp*"),
                            "agent-lsp*")


class SearchCmdTest(unittest.TestCase):
    """cmd_* на временной базе, собранной build.py (без реальных БД)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "proj")
        os.makedirs(self.root)
        for rel, content in PROJ.items():
            with open(os.path.join(self.root, rel), "w",
                      encoding="utf-8") as f:
                f.write(content)
        self.db_path = os.path.join(self.tmp, "test.db")
        con = sqlite3.connect(self.db_path)
        build.full_build(con, self.root, set(), set())
        con.commit()
        con.close()
        self.con = search._connect(self.db_path)

    def tearDown(self):
        self.con.close()
        shutil.rmtree(self.tmp)

    def _ns(self, **kw):
        defaults = {"db": self.db_path, "json": False, "limit": 10,
                    "no_snippet": False, "no_log": True, "path": None,
                    "substring": False}
        defaults.update(kw)
        return argparse.Namespace(**defaults)

    def test_cmd_symbol(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_symbol(self.con, self._ns(symbol="greet"))
        self.assertIn("app.py:3", out.getvalue())
        self.assertIn("[function]", out.getvalue())

    def test_cmd_symbol_json(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_symbol(self.con, self._ns(symbol="greet", json=True))
        data = json.loads(out.getvalue())
        self.assertEqual(data[0]["name"], "greet")
        self.assertEqual(data[0]["rel_path"], "app.py")

    def test_cmd_symbol_missing(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_symbol(self.con, self._ns(symbol="nope"))
        self.assertIn("не найден", out.getvalue())

    def test_cmd_calls_and_imports(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_calls(self.con, self._ns(calls="greet"))
        self.assertIn("app.py:11", out.getvalue())
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_imports(self.con, self._ns(imports="os"))
        self.assertIn("app.py:1", out.getvalue())

    def test_cmd_deps(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_deps(self.con, self._ns(deps="mod.py"))
        self.assertIn("app", out.getvalue())

    def test_cmd_inherits_both_directions(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_inherits(self.con, self._ns(inherits="Base"))
        self.assertIn("Child", out.getvalue())
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_inherits(self.con, self._ns(inherits="=Child"))
        self.assertIn("Base", out.getvalue())

    def test_cmd_errors(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_errors(self.con, self._ns())
        self.assertIn("broken.py", out.getvalue())

    def test_cmd_search(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_search(self.con, self._ns(query="greet"))
        self.assertIn("app.py", out.getvalue())
        self.assertIn("найдено: 1", out.getvalue())

    def test_cmd_search_json(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_search(self.con, self._ns(query="greet", json=True))
        data = json.loads(out.getvalue())
        self.assertEqual(data[0]["rel_path"], "app.py")

    def test_cmd_search_path_filter(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_search(self.con, self._ns(query="Child", path="mod"))
        self.assertIn("mod.py", out.getvalue())
        self.assertNotIn("app.py", out.getvalue())

    def test_cmd_search_substring(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_search(self.con,
                              self._ns(query="gre", substring=True))
        self.assertIn("app.py", out.getvalue())

    def test_cmd_search_empty(self):
        out = io.StringIO()
        with redirect_stdout(out):
            search.cmd_search(self.con, self._ns(query="zzzqqq"))
        self.assertIn("ничего не найдено", out.getvalue())


class CliRegressionTest(unittest.TestCase):
    """Регрессия интерфейса: те же флаги, что зовёт MCP db-tools."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "proj")
        os.makedirs(self.root)
        for rel, content in PROJ.items():
            with open(os.path.join(self.root, rel), "w",
                      encoding="utf-8") as f:
                f.write(content)
        self.db_path = os.path.join(self.tmp, "test.db")
        self.search_py = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "search.py")
        subprocess.run(
            [sys.executable, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "build.py"),
             "-r", self.root, "-o", self.db_path],
            check=True, capture_output=True, text=True)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, self.search_py, "-b", self.db_path, *args],
            capture_output=True, text=True, check=False)

    def test_symbol_flag(self):
        r = self.run_cli("--symbol", "greet")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("app.py:3", r.stdout)

    def test_calls_flag(self):
        r = self.run_cli("--calls", "greet")
        self.assertIn("app.py:11", r.stdout)

    def test_imports_flag(self):
        r = self.run_cli("--imports", "os")
        self.assertIn("app.py:1", r.stdout)

    def test_errors_flag(self):
        r = self.run_cli("--errors")
        self.assertIn("broken.py", r.stdout)

    def test_json_flag(self):
        r = self.run_cli("--json", "--symbol", "greet")
        data = json.loads(r.stdout)
        self.assertEqual(data[0]["name"], "greet")

    def test_search_flag_without_db(self):
        r = subprocess.run(
            [sys.executable, self.search_py, "-b",
             os.path.join(self.tmp, "nope.db"), "привет"],
            capture_output=True, text=True, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("базы нет", r.stderr)

    def test_no_query_shows_hint(self):
        r = self.run_cli()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--symbol", r.stderr)


if __name__ == "__main__":
    unittest.main()

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
