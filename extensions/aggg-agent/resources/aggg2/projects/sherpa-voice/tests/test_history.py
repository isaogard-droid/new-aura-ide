#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты истории (history.md): markdown-формат, смена дня, поиск.

Запуск (из корня проекта):
    ./venv/bin/python -m unittest discover -s tests -t .
"""
import os
import tempfile
import unittest
from unittest import mock

import chat
import deepseek_ai

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import transcribe
import ui_utils


class HistoryMdTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old = ui_utils.HISTORY_FILE
        ui_utils.HISTORY_FILE = os.path.join(self.tmp, "history.md")
        self.addCleanup(setattr, ui_utils, "HISTORY_FILE", self.old)

    def _md(self):
        with open(ui_utils.HISTORY_FILE, encoding="utf-8") as f:
            return f.read()

    def test_writes_day_header_and_entries(self):
        transcribe._append_history("первая")
        transcribe._append_history("вторая")
        md = self._md()
        self.assertEqual(md.count("## "), 1)
        self.assertEqual(md.count("- `"), 2)
        self.assertIn("первая", md)
        self.assertIn("вторая", md)

    def test_new_day_gets_new_header(self):
        with mock.patch("store.time.strftime",
                        return_value="2026-08-09 10:00:00"):
            transcribe._append_history("день первый")
        with mock.patch("store.time.strftime",
                        return_value="2026-08-10 10:00:00"):
            transcribe._append_history("день второй")
        md = self._md()
        self.assertEqual(md.count("## "), 2)
        self.assertIn("## 2026-08-09", md)
        self.assertIn("## 2026-08-10", md)

    def test_no_limit(self):
        for i in range(300):
            transcribe._append_history(f"запись {i}")
        md = self._md()
        self.assertEqual(md.count("- `"), 300)


class HistorySearchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old = ui_utils.HISTORY_FILE
        ui_utils.HISTORY_FILE = os.path.join(self.tmp, "history.md")
        self.addCleanup(setattr, ui_utils, "HISTORY_FILE", self.old)
        transcribe._append_history("про покупку машины")
        transcribe._append_history("про отпуск в горах")

    def test_finds_substring(self):
        with mock.patch("builtins.input", side_effect=["машины", "1"]), \
             mock.patch.object(chat, "publish_result") as pub:
            transcribe._history_search()
        pub.assert_called_once_with("про покупку машины", to_tg=False,
                                    to_history=False)

    def test_no_match_prints_nothing_found(self):
        with mock.patch("builtins.input", side_effect=["несуществующее"]), \
             mock.patch.object(chat, "publish_result") as pub, \
             mock.patch("builtins.print") as pr:
            transcribe._history_search()
        pub.assert_not_called()
        texts = [str(a.args[0]) for a in pr.call_args_list]
        self.assertTrue(any("Ничего" in t for t in texts))

    def test_missing_history_file(self):
        os.remove(ui_utils.HISTORY_FILE)
        with mock.patch("builtins.input") as inp, \
             mock.patch("builtins.print") as pr:
            transcribe._history_search()
        inp.assert_not_called()
        texts = [str(a.args[0]) for a in pr.call_args_list]
        self.assertTrue(any("пуста" in t for t in texts))


class HistoryMigrateTest(unittest.TestCase):
    def test_migrates_old_txt(self):
        import pathlib
        tmp = tempfile.mkdtemp()
        old = pathlib.Path(tmp) / "history.txt"
        old.write_text("[2026-08-08 13:05:15] запись а\n"
                       "[2026-08-09 09:00:00] запись б\n",
                       encoding="utf-8")
        md_path = pathlib.Path(tmp) / "history.md"
        with mock.patch("ui_utils.HISTORY_FILE", str(md_path)), \
             mock.patch("os.path.expanduser", return_value=str(old)):
            transcribe._migrate_history()
        md = md_path.read_text(encoding="utf-8")
        self.assertIn("## 2026-08-08", md)
        self.assertIn("## 2026-08-09", md)
        self.assertIn("запись а", md)
        self.assertIn("запись б", md)


class DaySummaryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old = ui_utils.HISTORY_FILE
        ui_utils.HISTORY_FILE = os.path.join(self.tmp, "history.md")
        self.addCleanup(setattr, ui_utils, "HISTORY_FILE", self.old)

    def _history(self, day, texts):
        with open(ui_utils.HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write(f"## {day}\n")
            f.writelines(f"- `{day} 10:00:00` {t}\n" for t in texts)
            f.write("## 2026-08-01\n- `2026-08-01 10:00:00` чужая запись\n")

    def test_collects_entries_and_calls_ask(self):
        self._history("2026-08-09", ["про тесты", "про подмешку"])
        with mock.patch.object(deepseek_ai, "enabled",
                               return_value=True), \
             mock.patch.object(deepseek_ai, "ask",
                               return_value=("Итог дня", None)) as ask:
            out = transcribe._day_summary("2026-08-09")
        self.assertEqual(out, "Итог дня")
        # два вызова: итог дня (day_summary) + задачи дня (action_items)
        self.assertEqual(ask.call_count, 2)
        args = ask.call_args_list[0].args
        self.assertIn("про тесты", args[1])
        self.assertIn("про подмешку", args[1])
        self.assertNotIn("чужая запись", args[1])
        # второй вызов — задачи дня с тем же телом записей
        args2 = ask.call_args_list[1].args
        self.assertIn("про тесты", args2[1])
        self.assertEqual(ask.call_args_list[1].kwargs.get("temperature"), 0)

    def test_no_entries_returns_none(self):
        with mock.patch("builtins.print") as _pr, \
             mock.patch.object(deepseek_ai, "ask") as ask:
            out = transcribe._day_summary("2026-08-10")
        self.assertIsNone(out)
        ask.assert_not_called()

    def test_no_key_returns_none(self):
        self._history("2026-08-09", ["запись"])
        with mock.patch.object(deepseek_ai, "enabled",
                               return_value=False), \
             mock.patch.object(deepseek_ai, "ask") as ask:
            out = transcribe._day_summary("2026-08-09")
        self.assertIsNone(out)
        ask.assert_not_called()

    def test_ask_error_returns_none(self):
        self._history("2026-08-09", ["запись"])
        with mock.patch.object(deepseek_ai, "enabled",
                               return_value=True), \
             mock.patch.object(deepseek_ai, "ask",
                               return_value=(None, "DeepSeek: boom")):
            out = transcribe._day_summary("2026-08-09")
        self.assertIsNone(out)


class TagsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old = ui_utils.HISTORY_FILE
        ui_utils.HISTORY_FILE = os.path.join(self.tmp, "history.md")
        self.addCleanup(setattr, ui_utils, "HISTORY_FILE", self.old)
        with open(ui_utils.HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write("## 2026-08-09\n"
                    "- `2026-08-09 10:00:00` запись про кодинг\n")

    def _md(self):
        with open(ui_utils.HISTORY_FILE, encoding="utf-8") as f:
            return f.read()

    def test_tags_appended_to_entry(self):
        with mock.patch.object(deepseek_ai, "auto_tags_enabled",
                               return_value=True), \
             mock.patch.object(deepseek_ai, "enabled", return_value=True), \
             mock.patch.object(deepseek_ai, "ask",
                               return_value=("кодинг, тесты", None)):
            transcribe._tag_last_entry("2026-08-09 10:00:00",
                                       "запись про кодинг")
        md = self._md()
        self.assertIn("запись про кодинг #кодинг #тесты", md)

    def test_no_retag_already_tagged(self):
        with mock.patch.object(deepseek_ai, "auto_tags_enabled",
                               return_value=True), \
             mock.patch.object(deepseek_ai, "enabled", return_value=True), \
             mock.patch.object(deepseek_ai, "ask",
                               return_value=("кодинг, тесты", None)) as ask:
            transcribe._tag_last_entry("2026-08-09 10:00:00",
                                       "запись про кодинг")
            transcribe._tag_last_entry("2026-08-09 10:00:00",
                                       "запись про кодинг")
        # повторный вызов не спрашивает DeepSeek повторно (строка уже с #)
        ask.assert_called_once()

    def test_disabled_skips(self):
        with mock.patch.object(deepseek_ai, "auto_tags_enabled",
                               return_value=False), \
             mock.patch.object(deepseek_ai, "ask") as ask:
            transcribe._tag_last_entry("2026-08-09 10:00:00", "текст")
        ask.assert_not_called()
        self.assertNotIn("#", self._md().split("\n")[1])

    def test_tag_menu_lists_and_copies(self):
        with open(ui_utils.HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write("## 2026-08-09\n"
                    "- `2026-08-09 10:00:00` запись про кодинг #кодинг\n")
        with mock.patch("builtins.input", side_effect=["1", "1"]), \
             mock.patch.object(chat, "publish_result") as pub:
            transcribe._tag_menu()
        pub.assert_called_once_with("запись про кодинг", to_tg=False,
                                    to_history=False)


if __name__ == "__main__":
    unittest.main()


# Оригинал от https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна и лучше предыдущей.

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
