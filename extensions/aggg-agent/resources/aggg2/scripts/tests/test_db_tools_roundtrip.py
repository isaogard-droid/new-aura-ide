"""Roundtrip-тесты db-tools: findings add→search→link на throwaway-базе
и build→search по временному проекту. Изоляция от prod-хранилища:
findings.py — env AGGG2_RESEARCH_DB; search/build — CLI-аргументы -b/-o.
Закрывает CRG-gaps «untested hotspots» (db-tools mains, аудит 15.08,
research.db id=540): --help-прогон в test_smoke_mains не проверял поведение.

Имена тестов = спека:
  test_findings_add_search_roundtrip — добавил → нашёл (FTS)
  test_findings_link_related — связал две находки → related видит
  test_findings_prod_untouched — после suite prod research.db неизменен
  test_build_then_symbol_search — собрал временную базу → symbol/поиск

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FINDINGS = ROOT / "db-tools" / "findings.py"
BUILD = ROOT / "db-tools" / "build.py"
SEARCH = ROOT / "db-tools" / "search.py"
PROD_DB = ROOT / "db" / "research.db"


def _run(argv, env=None):
    proc = subprocess.run(
        [sys.executable, *argv],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, **(env or {})}, cwd=ROOT, check=False)
    return proc.returncode, proc.stdout, proc.stderr


class FindingsRoundtrip(unittest.TestCase):
    """findings.py add→search→link на throwaway-базе (env override)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "t.db"
        self.env = {"AGGG2_RESEARCH_DB": str(self.db)}
        self._prod_count_before = self._count(PROD_DB)

    def tearDown(self):
        self.tmp.cleanup()
        self.assertEqual(self._count(PROD_DB), self._prod_count_before,
                         "prod research.db изменился — тест пишет в прод!")

    @staticmethod
    def _count(db):
        if not Path(db).exists():
            return 0
        con = sqlite3.connect(db)
        try:
            return con.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        finally:
            con.close()

    def test_findings_add_search_roundtrip(self):
        rc, out, err = _run(
            [str(FINDINGS), "add", "smoke-тема", "--text", "вывод зуммер-уникум",
             "--tags", "smoke test"], env=self.env)
        self.assertEqual(rc, 0, err)
        rc, out, _ = _run([str(FINDINGS), "search", "зуммер-уникум"],
                          env=self.env)
        self.assertEqual(rc, 0)
        self.assertIn("smoke-тема", out)

    def test_findings_link_related(self):
        _run([str(FINDINGS), "add", "т1", "--text", "x", "--tags", "s"],
             env=self.env)
        _run([str(FINDINGS), "add", "т2", "--text", "y", "--tags", "s"],
             env=self.env)
        rc, _, err = _run([str(FINDINGS), "link", "add", "1", "2",
                           "--kind", "related"], env=self.env)
        self.assertEqual(rc, 0, err)
        rc, out, _ = _run([str(FINDINGS), "related", "1"], env=self.env)
        self.assertEqual(rc, 0)
        self.assertIn("т2", out)


class BuildSearchRoundtrip(unittest.TestCase):
    """build.py -o временная база → search.py --symbol/поиск по ней."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proj = Path(self.tmp.name) / "proj"
        (self.proj).mkdir()
        (self.proj / "mod.py").write_text(
            "def load_mix():\n    return 42\n\ndef helper_xyz():\n"
            "    return load_mix() + 1\n", encoding="utf-8")
        self.db = Path(self.tmp.name) / "p.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_then_symbol_search(self):
        rc, _, err = _run([str(BUILD), "-r", str(self.proj),
                           "-o", str(self.db)])
        self.assertEqual(rc, 0, err)
        rc, out, _ = _run([str(SEARCH), "-b", str(self.db),
                           "--symbol", "load_mix"])
        self.assertEqual(rc, 0)
        self.assertIn("mod.py", out)
        rc, out, _ = _run([str(SEARCH), "-b", str(self.db), "helper"])
        self.assertEqual(rc, 0)
        self.assertIn("mod.py", out)

    @unittest.skipUnless((ROOT / "db" / "research.db").exists(),
                         "нет research.db — did-you-mean не из чего брать")
    def test_empty_search_did_you_mean(self):
        """Пустой результат в чужой базе → «искали похожее» из search_log."""
        rc, _, err = _run([str(BUILD), "-r", str(self.proj),
                           "-o", str(self.db)])
        self.assertEqual(rc, 0, err)
        rc, out, _ = _run([str(SEARCH), "-b", str(self.db), "настройка звука"])
        self.assertEqual(rc, 0)
        self.assertIn("искали похожее", out)


if __name__ == "__main__":
    unittest.main()
