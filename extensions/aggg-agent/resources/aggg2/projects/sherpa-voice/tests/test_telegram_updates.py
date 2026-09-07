#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты Telegram-логики telegram.py — без сети и без ключа.

Запуск (из корня проекта, через venv — там numpy/sounddevice):
    ./venv/bin/python -m unittest discover -s tests -t .
"""

import unittest
from unittest import mock

import telegram


class TgHandleUpdateTest(unittest.TestCase):
    def test_callback_query_advances_offset(self):
        upd = {"update_id": 10,
               "callback_query": {"id": "1", "data": "summary",
                                  "message": {"chat": {"id": 1}}}}
        with mock.patch.object(telegram, "_tg_handle_callback") as h:
            off = telegram._tg_handle_update(upd, "tok", None, False,
                                               copy_to_buf=False)
        self.assertEqual(off, 11)
        h.assert_called_once()

    def test_text_message_advances_offset(self):
        upd = {"update_id": 20,
               "message": {"chat": {"id": 1}, "text": "саммари"}}
        with mock.patch.object(telegram, "_tg_handle_text_command") as h:
            off = telegram._tg_handle_update(upd, "tok", None, False,
                                               copy_to_buf=False)
        self.assertEqual(off, 21)
        h.assert_called_once()

    def test_broken_update_still_advances_offset(self):
        upd = {"update_id": 30}
        off = telegram._tg_handle_update(upd, "tok", None, False,
                                           copy_to_buf=False)
        self.assertEqual(off, 31)

    def test_voice_download_error_advances_offset(self):
        upd = {"update_id": 40,
               "message": {"chat": {"id": 1},
                           "message_id": 5,
                           "voice": {"file_id": "f1"},
                           "from": {"first_name": "Тест"}}}
        with mock.patch.object(telegram, "_tg_download",
                               return_value=(False, "нет файла")), \
             mock.patch.object(telegram, "_tg_chat_action"), \
             mock.patch.object(telegram, "_tg_set_reaction"):
            off = telegram._tg_handle_update(upd, "tok", None, False,
                                               copy_to_buf=False)
        self.assertEqual(off, 41)


class TgTextCommandTest(unittest.TestCase):
    def test_russian_command_calls_callback(self):
        with mock.patch.object(telegram, "_tg_handle_callback") as h:
            telegram._tg_handle_text_command(
                {"chat": {"id": 7}, "text": "саммари"}, "tok")
        h.assert_called_once_with(
            {"id": None, "data": "саммари", "from": None,
             "message": {"chat": {"id": 7}}}, "tok")

    def test_slash_help_calls_callback(self):
        with mock.patch.object(telegram, "_tg_handle_callback") as h:
            telegram._tg_handle_text_command(
                {"chat": {"id": 7}, "text": "/help"}, "tok")
        h.assert_called_once()
        self.assertEqual(h.call_args.args[0]["data"], "help")

    def test_unknown_text_ignored(self):
        with mock.patch.object(telegram, "_tg_handle_callback") as h:
            telegram._tg_handle_text_command(
                {"chat": {"id": 7}, "text": "привет"}, "tok")
        h.assert_not_called()

    def test_ping_answers_pong(self):
        with mock.patch.object(telegram, "_tg_request") as req:
            telegram._tg_handle_text_command(
                {"chat": {"id": 7}, "text": "/ping"}, "tok")
        req.assert_called_once_with(
            "tok", "sendMessage", {"chat_id": 7, "text": "pong 🏓"})

    def test_empty_text_ignored(self):
        with mock.patch.object(telegram, "_tg_handle_callback") as h:
            telegram._tg_handle_text_command({"chat": {"id": 7}}, "tok")
        h.assert_not_called()


if __name__ == "__main__":
    unittest.main()

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
