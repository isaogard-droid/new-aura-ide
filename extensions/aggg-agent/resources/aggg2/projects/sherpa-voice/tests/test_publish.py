#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.




# Источник: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия — новая и ещё лучше.
"""Юнит-тесты publish_result (единый публикатор результата).

Запуск (из корня проекта):
    ./venv/bin/python -m unittest discover -s tests -t .
"""
import os

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import tempfile
import unittest
from unittest import mock

import store
import telegram
import transcribe
import ui_utils


class PublishResultTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        ui_utils.HISTORY_FILE = os.path.join(self.tmp, "history.txt")
        ui_utils.LAST_TEXT_FILE = os.path.join(self.tmp, "last.txt")
        patcher = mock.patch.object(ui_utils, "copy_to_clipboard",
                                    return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        for p in (ui_utils.HISTORY_FILE, ui_utils.LAST_TEXT_FILE):
            if os.path.exists(p):
                os.remove(p)

    def _tg_off(self):
        return mock.patch.object(telegram, "load_telegram",
                                 return_value=(False, "", ""))

    def test_full_path_clipboard_history_telegram(self):
        with mock.patch.object(store, "_append_history") as hist, \
             mock.patch.object(telegram, "load_telegram",
                               return_value=(True, "tok", "42")) as load, \
             mock.patch.object(telegram, "_tg_send_result",
                               return_value=(True, None)) as send:
            ok, _ = transcribe.publish_result("текст", "📝 Транскрипт")
        self.assertTrue(ok)
        hist.assert_called_once_with("текст")
        load.assert_called_once()
        send.assert_called_once_with("текст", "📝 Транскрипт",
                                     chat_id="42", reply_markup=None,
                                     footer=None)
        self.assertFalse(os.path.exists(ui_utils.LAST_TEXT_FILE))

    def test_clipboard_unavailable_writes_file(self):
        with mock.patch.object(ui_utils, "copy_to_clipboard",
                               return_value=False), \
             self._tg_off(), \
             mock.patch.object(telegram, "_tg_send_result",
                               return_value=(True, None)) as send:
            ok, _ = transcribe.publish_result("текст")
        self.assertTrue(ok)
        with open(ui_utils.LAST_TEXT_FILE, encoding="utf-8") as f:
            self.assertEqual(f.read(), "текст")
        send.assert_called_once_with("текст", None, chat_id="",
                                     reply_markup=None, footer=None)

    def test_tg_footer_passed_through(self):
        with mock.patch.object(ui_utils, "copy_to_clipboard",
                               return_value=True), \
             mock.patch.object(telegram, "load_telegram",
                               return_value=(True, "tok", "42")), \
             mock.patch.object(telegram, "_tg_send_result",
                               return_value=(True, None)) as send:
            transcribe.publish_result("текст", tg_footer="приписка")
        send.assert_called_once_with("текст", None, chat_id="42",
                                     reply_markup=None, footer="приписка")

    def test_to_history_false_skips_history(self):
        with mock.patch.object(store, "_append_history") as hist, \
             self._tg_off(), \
             mock.patch.object(telegram, "_tg_send_result", return_value=(True, None)) as _send:
            transcribe.publish_result("текст", to_history=False)
        hist.assert_not_called()

    def test_to_file_false_no_file(self):
        with mock.patch.object(ui_utils, "copy_to_clipboard",
                               return_value=False), \
             self._tg_off(), \
             mock.patch.object(telegram, "_tg_send_result", return_value=(True, None)) as _send:
            transcribe.publish_result("текст", to_file=False)
        self.assertFalse(os.path.exists(ui_utils.LAST_TEXT_FILE))

    def test_to_clipboard_false_skips_buffer_but_keeps_history(self):
        with mock.patch.object(ui_utils, "copy_to_clipboard") as copy, \
             mock.patch.object(store, "_append_history") as hist, \
             self._tg_off(), \
             mock.patch.object(telegram, "_tg_send_result",
                               return_value=(True, None)) as _send:
            transcribe.publish_result("текст", to_clipboard=False)
        copy.assert_not_called()
        hist.assert_called_once_with("текст")
        self.assertFalse(os.path.exists(ui_utils.LAST_TEXT_FILE))

    def test_telegram_error_reported(self):
        with mock.patch.object(telegram, "load_telegram",
                               return_value=(True, "tok", "42")), \
             mock.patch.object(telegram, "_tg_send_result",
                               return_value=(False, "Telegram: boom")) as send:
            ok, err = transcribe.publish_result("текст")
        self.assertFalse(ok)
        self.assertEqual(err, "Telegram: boom")
        send.assert_called_once()


if __name__ == "__main__":
    unittest.main()

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
