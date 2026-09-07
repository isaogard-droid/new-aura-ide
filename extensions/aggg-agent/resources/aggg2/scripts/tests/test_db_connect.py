#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Регрессия db_connect (scripts/_compat.py): коннект закрывается в
finally — и на успехе, и при исключении внутри with. Для долгоживущих
процессов (MCP-сервер) это защита от утечки файловых дескрипторов
(ресёрч close-дисциплины sqlite, 16.08.2026, research.db id=689).

Запуск:
    python3 -m unittest discover -s scripts/tests -t scripts/tests
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from _compat import db_connect  # noqa: E402 — импорт после sys.path (паттерн)


class DbConnectTest(unittest.TestCase):
    """close в finally: утёкший коннект невозможен даже при ошибке."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "t.db")

    def tearDown(self):
        self.tmp.cleanup()

    def _assert_closed(self, con):
        with self.assertRaises(sqlite3.ProgrammingError):
            con.execute("SELECT 1")

    def test_close_on_success(self):
        with db_connect(self.db) as con:
            con.execute("CREATE TABLE t (x)")
            con.commit()
        self._assert_closed(con)

    def test_close_on_exception(self):
        con_ref = None
        with self.assertRaises(RuntimeError), db_connect(self.db) as con:
            con_ref = con
            con.execute("CREATE TABLE t (x)")
            raise RuntimeError("ошибка внутри with")
        self._assert_closed(con_ref)

    def test_row_factory(self):
        with db_connect(self.db, row_factory=sqlite3.Row) as con:
            con.execute("CREATE TABLE t (x)")
            con.execute("INSERT INTO t VALUES (1)")
            con.commit()
            row = con.execute("SELECT x FROM t").fetchone()
        self.assertEqual(row["x"], 1)


if __name__ == "__main__":
    unittest.main()
