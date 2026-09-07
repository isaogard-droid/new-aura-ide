#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты build.py: извлечение символов/рёбер, сборка, инкремент.

Запуск (из корня AGGG2.0):
    python3 -m unittest discover -s db-tools/tests -t .
"""
import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build

# Мини-проект для интеграционных тестов: 5 файлов, все типы извлечения
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
    "notes.md": "# Заголовок один\n\n## Подзаголовок\n",
    "script.sh": "deploy() {\n  echo hi\n}\n",
    "app.js": (
        "import { helper } from './util.js';\n"
        "class Base {\n"
        "  go(x) { return x; }\n"
        "}\n"
        "export class Child extends Base {\n"
        "  constructor() { super(); }\n"
        "  run() { return helper(this.go(1)); }\n"
        "}\n"
        "const arrow = (a) => a * 2;\n"
        "function plain(a, b) { return a + b; }\n"
        "chrome.tabs.query({});\n"
    ),
    "broken.js": "function f( {\n",
}


def make_project(root):
    """Раскладывает PROJ в root, возвращает список rel-путей."""
    for rel, content in PROJ.items():
        full = os.path.join(root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    return list(PROJ)


class ExtractSymbolsTest(unittest.TestCase):
    def test_py_functions_classes_methods(self):
        syms = build.extract_symbols("app.py", PROJ["app.py"])
        names = [s[0] for s in syms]
        self.assertIn("greet", names)
        self.assertIn("Base", names)
        self.assertIn("Child", names)
        self.assertIn("run", names)
        # типы
        kinds = {s[0]: s[1] for s in syms}
        self.assertEqual(kinds["greet"], "function")
        self.assertEqual(kinds["Base"], "class")
        self.assertEqual(kinds["Child"], "class")
        self.assertEqual(kinds["run"], "method")
        # сигнатура функции с параметром
        sig = {s[0]: s[3] for s in syms}
        self.assertEqual(sig["greet"], "def greet(name)")
        self.assertEqual(sig["run"], "def run(self)")
        # наследование в сигнатуре класса
        self.assertEqual(sig["Child"], "class Child(Base)")
        self.assertEqual(sig["Base"], "class Base")

    def test_md_headings(self):
        syms = build.extract_symbols("notes.md", PROJ["notes.md"])
        self.assertEqual([(s[0], s[1], s[2]) for s in syms],
                         [("Заголовок один", "h1", 1),
                          ("Подзаголовок", "h2", 3)])

    def test_sh_functions(self):
        syms = build.extract_symbols("script.sh", PROJ["script.sh"])
        self.assertEqual([(s[0], s[1]) for s in syms], [("deploy", "function")])

    def test_syntax_error_returns_empty(self):
        syms = build.extract_symbols("broken.py", PROJ["broken.py"])
        self.assertEqual(syms, [])

    def test_non_py_ignored(self):
        self.assertEqual(build.extract_symbols("x.txt", "def f():\n"), [])

    def test_js_functions_classes_methods(self):
        syms = build.extract_symbols("app.js", PROJ["app.js"])
        names = [s[0] for s in syms]
        self.assertIn("Base", names)
        self.assertIn("Child", names)
        self.assertIn("go", names)
        self.assertIn("run", names)
        self.assertIn("plain", names)
        self.assertIn("arrow", names)
        kinds = {s[0]: s[1] for s in syms}
        self.assertEqual(kinds["Base"], "class")
        self.assertEqual(kinds["Child"], "class")
        self.assertEqual(kinds["go"], "method")
        self.assertEqual(kinds["run"], "method")
        self.assertEqual(kinds["plain"], "function")
        self.assertEqual(kinds["arrow"], "function")
        # сигнатуры: параметры функции и наследование класса
        sig = {s[0]: s[3] for s in syms}
        self.assertEqual(sig["plain"], "function plain(a, b)")
        self.assertEqual(sig["Child"], "class Child(Base)")
        self.assertEqual(sig["go"], "method go(x)")

    def test_js_syntax_error_returns_empty(self):
        self.assertEqual(build.extract_symbols("broken.js", PROJ["broken.js"]),
                         [])


class ExtractEdgesTest(unittest.TestCase):
    def test_imports(self):
        self.assertEqual(build.extract_imports("app.py", PROJ["app.py"]),
                         [("os", 1)])
        self.assertEqual(build.extract_imports("mod.py", PROJ["mod.py"]),
                         [("app", 1)])

    def test_calls(self):
        # greet("x") — Name (строка 11); c.run() — Attribute -> run
        self.assertIn(("greet", 11), build.extract_calls("app.py", PROJ["app.py"]))
        calls_mod = build.extract_calls("mod.py", PROJ["mod.py"])
        self.assertIn(("Child", 3), calls_mod)
        self.assertIn(("run", 4), calls_mod)

    def test_inherits(self):
        self.assertEqual(build.extract_inherits("app.py", PROJ["app.py"]),
                         [("Child", "Base", 9)])

    def test_errors(self):
        errs = build.extract_errors("broken.py", PROJ["broken.py"])
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0][0], 1)  # строка ошибки

    def test_edges_only_py(self):
        self.assertEqual(build.extract_imports("notes.md", "# x"), [])
        self.assertEqual(build.extract_calls("notes.md", "# x"), [])

    def test_js_imports_calls_inherits_errors(self):
        js = PROJ["app.js"]
        self.assertEqual(build.extract_imports("app.js", js),
                         [("util.js", 1)])
        calls = build.extract_calls("app.js", js)
        # helper(this.go(1)) -> helper, go; chrome.tabs.query -> query
        self.assertIn(("helper", 7), calls)
        self.assertIn(("go", 7), calls)
        self.assertIn(("query", 11), calls)
        self.assertEqual(build.extract_inherits("app.js", js),
                         [("Child", "Base", 5)])
        errs = build.extract_errors("broken.js", PROJ["broken.js"])
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0][0], 1)


class HelpersTest(unittest.TestCase):
    def test_is_artifact(self):
        self.assertTrue(build.is_artifact("a.db"))
        self.assertTrue(build.is_artifact("x.db-wal"))
        self.assertTrue(build.is_artifact("pic.png"))
        self.assertTrue(build.is_artifact("index.md.bak"))
        self.assertTrue(build.is_artifact("notes.md.orig"))
        self.assertFalse(build.is_artifact("app.py"))
        self.assertFalse(build.is_artifact("notes.md"))

    def test_read_hashed(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "f.txt")
            with open(p, "w", encoding="utf-8") as f:
                f.write("hello")
            h, content = build.read_hashed(p)
            self.assertEqual(content, "hello")
            self.assertEqual(h, hashlib.sha256(b"hello").hexdigest())
        finally:
            shutil.rmtree(tmp)

    def test_scan_files_skips(self):
        tmp = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmp, "venv"))
            with open(os.path.join(tmp, "venv", "x.py"), "w") as f:
                f.write("x")
            with open(os.path.join(tmp, "main.py"), "w") as f:
                f.write("x")
            with open(os.path.join(tmp, "data.db"), "w") as f:
                f.write("x")
            found = build.scan_files(tmp, {"venv"}, set())
            self.assertIn("main.py", found)
            self.assertNotIn("venv/x.py", found)
            self.assertNotIn("data.db", found)
        finally:
            shutil.rmtree(tmp)

    def test_default_skip_dirs_isolation(self):
        """Изоляция от общей индексации (решение владельца 12.08.2026):
        agent/ — внутренние агенты (своя база
        db/agent.db, skip по имени везде); fable-method — вендор в КОРНЕ
        (ROOT_SKIP_DIRS): канон skills/fable-method/ индексируется.
        Регрессионная защита: если директорию уберут из скипов — тест упадёт."""
        self.assertIn("agent", build.DEFAULT_SKIP_DIRS)
        self.assertIn("fable-method", build.ROOT_SKIP_DIRS)
        self.assertNotIn("fable-method", build.DEFAULT_SKIP_DIRS)

    def test_scan_files_skips_isolation_dirs(self):
        """Сборка не подхватывает agent/ (везде) и fable-method/ (в корне),
        НО индексирует вложенный канон skills/fable-method/."""
        tmp = tempfile.mkdtemp()
        try:
            for d in ("agent", "fable-method"):
                os.makedirs(os.path.join(tmp, d))
                with open(os.path.join(tmp, d, "x.py"), "w") as f:
                    f.write("def hidden():\n    pass\n")
            # канон скилла — вложенный fable-method должен индексироваться
            os.makedirs(os.path.join(tmp, "skills", "fable-method"))
            with open(os.path.join(tmp, "skills", "fable-method", "SKILL.md"),
                      "w") as f:
                f.write("# fable-method canon\n")
            with open(os.path.join(tmp, "main.py"), "w") as f:
                f.write("def visible():\n    pass\n")
            found = build.scan_files(tmp, build.DEFAULT_SKIP_DIRS, set(),
                                     root_skip_dirs=build.ROOT_SKIP_DIRS)
            self.assertIn("main.py", found)
            self.assertNotIn("agent/x.py", found)
            self.assertNotIn("fable-method/x.py", found)
            self.assertIn("skills/fable-method/SKILL.md", found)
        finally:
            shutil.rmtree(tmp)


class BuildIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "proj")
        os.makedirs(self.root)
        make_project(self.root)
        self.db_path = os.path.join(self.tmp, "test.db")
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.executescript(build.SCHEMA)
        self.con = con

    def tearDown(self):
        self.con.close()
        shutil.rmtree(self.tmp)

    def test_full_build_populates_tables(self):
        stats = build.full_build(self.con, self.root, set(), set())
        self.assertEqual(stats["new"], 7)

        def count(sql):
            return self.con.execute(sql).fetchone()[0]

        self.assertEqual(count("SELECT COUNT(*) FROM files"), 7)
        # py: greet/Base/Child/run; md: 2 заголовка; sh: 1; js: 7 (Base/go/
        # Child/constructor/run/arrow/plain)
        self.assertEqual(count("SELECT COUNT(*) FROM symbols"), 14)
        self.assertEqual(count("SELECT COUNT(*) FROM imports"), 3)   # os, app, util.js
        self.assertEqual(count("SELECT COUNT(*) FROM calls"), 7)     # greet, Child, run, helper, go, query + echo (sh)
        self.assertEqual(count("SELECT COUNT(*) FROM inherits"), 2)  # Child->Base (py, js)
        self.assertEqual(count("SELECT COUNT(*) FROM errors"), 2)    # broken.py, broken.js
        # контент в базе + хеш
        row = self.con.execute(
            "SELECT content_hash, content FROM files WHERE rel_path='app.py'"
        ).fetchone()
        self.assertEqual(row["content"], PROJ["app.py"])
        self.assertEqual(row["content_hash"],
                         hashlib.sha256(PROJ["app.py"].encode()).hexdigest())

    def test_extra_roots_indexed_with_prefix(self):
        """--extra-root: доп. каталог индексируется с префиксом имени."""
        shelf = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, shelf)
        with open(os.path.join(shelf, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: shelf-skill\n---\n# Полка\n")
        extra_roots = build.collect_extra_roots([shelf])
        self.assertEqual(len(extra_roots), 1)
        prefix, abs_r = extra_roots[0]
        self.assertEqual(prefix, os.path.basename(shelf.rstrip(os.sep)))
        self.assertEqual(abs_r, os.path.abspath(shelf))
        build.full_build(self.con, self.root, set(), set(),
                         extra_roots=extra_roots)
        row = self.con.execute(
            "SELECT rel_path FROM files WHERE rel_path LIKE ?",
            (f"{prefix}/SKILL.md",)).fetchone()
        self.assertIsNotNone(row)
        build.incremental_build(self.con, self.root, set(), set(),
                                extra_roots=extra_roots)
        row = self.con.execute(
            "SELECT rel_path FROM files WHERE rel_path = ?",
            (f"{prefix}/SKILL.md",)).fetchone()
        self.assertIsNotNone(row)
        # удаление файла из extra-root убирает его из базы
        os.unlink(os.path.join(shelf, "SKILL.md"))
        build.incremental_build(self.con, self.root, set(), set(),
                                extra_roots=extra_roots)
        row = self.con.execute(
            "SELECT rel_path FROM files WHERE rel_path = ?",
            (f"{prefix}/SKILL.md",)).fetchone()
        self.assertIsNone(row)

    def test_collect_extra_roots_missing_dir_warns(self):
        # несуществующий каталог — пропускается, не падает
        out = build.collect_extra_roots(["/nonexistent/skills-shelf"])
        self.assertEqual(out, [])

    def test_fts_search(self):
        build.full_build(self.con, self.root, set(), set())
        rows = self.con.execute(
            "SELECT rel_path FROM files_fts WHERE files_fts MATCH 'greet'"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], ["app.py"])
        # триграмный индекс тоже работает
        rows = self.con.execute(
            "SELECT rel_path FROM files_fts_trigram "
            "WHERE files_fts_trigram MATCH 'олов'"
        ).fetchall()
        self.assertIn("notes.md", [r[0] for r in rows])

    def test_incremental_same_then_changed_then_deleted(self):
        build.full_build(self.con, self.root, set(), set())
        # без изменений — всё same
        stats = build.incremental_build(self.con, self.root, set(), set())
        self.assertEqual(stats["same"], 7)
        self.assertEqual(stats["changed"], 0)
        # изменили app.py (добавили функцию) — changed 1
        app = os.path.join(self.root, "app.py")
        with open(app, "a", encoding="utf-8") as f:
            f.write("\ndef extra():\n    pass\n")
        stats = build.incremental_build(self.con, self.root, set(), set())
        self.assertEqual(stats["changed"], 1)
        self.assertEqual(stats["same"], 6)
        n = self.con.execute(
            "SELECT COUNT(*) FROM symbols WHERE rel_path='app.py'"
        ).fetchone()[0]
        self.assertEqual(n, 5)  # добавилась extra
        # удалили broken.py — del 1, ошибка broken.js остаётся
        os.remove(os.path.join(self.root, "broken.py"))
        stats = build.incremental_build(self.con, self.root, set(), set())
        self.assertEqual(stats["del"], 1)
        n = self.con.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
        self.assertEqual(n, 1)

    def test_schema_ok(self):
        self.assertTrue(build.schema_ok(self.con))
        # пустая/чужая база — False
        other = sqlite3.connect(os.path.join(self.tmp, "other.db"))
        try:
            other.execute("CREATE TABLE files (id INTEGER)")
            self.assertFalse(build.schema_ok(other))
        finally:
            other.close()

    def test_main_cli(self):
        # отдельная база от setUp (там схема уже создана — main выбрал бы инкремент)
        cli_db = os.path.join(self.tmp, "cli.db")
        out = subprocess.run(
            [sys.executable, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "build.py"),
             "-r", self.root, "-o", cli_db],
            capture_output=True, text=True, check=False)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ok [полная]", out.stdout)
        # второй запуск — инкрементальный
        out2 = subprocess.run(
            [sys.executable, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "build.py"),
             "-r", self.root, "-o", cli_db],
            capture_output=True, text=True, check=False)
        self.assertIn("ok [инкрементальная]", out2.stdout)
        self.assertIn("без изменений: 7", out2.stdout)


if __name__ == "__main__":
    unittest.main()

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
