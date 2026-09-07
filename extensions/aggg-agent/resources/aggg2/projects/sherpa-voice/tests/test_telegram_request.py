#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты Telegram-логики telegram.py — без сети и без ключа.

Запуск (из корня проекта, через venv — там numpy/sounddevice):
    ./venv/bin/python -m unittest discover -s tests -t .
"""

import json
import unittest
from unittest import mock

import telegram


class TgRequestTest(unittest.TestCase):
    @staticmethod
    def _fake_urlopen(body):
        resp = mock.Mock()
        resp.read.return_value = body
        return resp

    @staticmethod
    def _header(req, name):
        for k, v in req.headers.items():
            if k.lower() == name.lower():
                return v
        return None

    def test_json_payload_and_ok(self):
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value.__enter__.return_value = self._fake_urlopen(
                b'{"ok": true}')
            ok, _ = telegram._tg_request("tok", "sendMessage",
                                             {"chat_id": "1"})
        self.assertTrue(ok)
        req = m.call_args.args[0]
        self.assertEqual(req.full_url,
                         "https://api.telegram.org/bottok/sendMessage")
        self.assertEqual(req.data, json.dumps({"chat_id": "1"}).encode())
        self.assertEqual(self._header(req, "Content-Type"),
                         "application/json")

    def test_multipart_serializes_dict_payload_as_json(self):
        """JSON-поля (reply_markup) в multipart-запросе (sendDocument)
        обязаны уходить строкой JSON, а не repr-представлением — иначе
        Telegram 400: can't parse reply keyboard markup JSON object."""
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value.__enter__.return_value = self._fake_urlopen(
                b'{"ok": true}')
            ok, _ = telegram._tg_request(
                "tok", "sendDocument",
                {"chat_id": "42", "reply_markup": {"inline_keyboard": []}},
                [("document", "a.txt", b"x")])
        self.assertTrue(ok)
        data = m.call_args.args[0].data.decode()
        self.assertIn('"inline_keyboard"', data)
        self.assertNotIn("'inline_keyboard'", data)

    def test_getaddrinfo_restored_after_request(self):
        """Рекурсия в _ipv4_getaddrinfo (фикс): оригинал getaddrinfo
        сохраняется при импорте (до подмены), а не внутри функции при
        первом вызове — иначе socket.getaddrinfo уже подменён на саму
        функцию и получается RecursionError. Проверяем: (1) подмена
        работает, (2) после запроса getaddrinfo — настоящий оригинал,
        (3) повторный запрос не ломается."""
        import socket
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value.__enter__.return_value = self._fake_urlopen(
                b'{"ok": true}')
            ok, _ = telegram._tg_request("tok", "sendMessage", {})
        self.assertTrue(ok)
        self.assertIs(socket.getaddrinfo, telegram._ORIG_GETADDRINFO)
        # фильтр: IPv6 отбрасывается при наличии IPv4
        res = telegram._ipv4_getaddrinfo("api.telegram.org", 443)
        self.assertIn(socket.AF_INET, {r[0] for r in res})
        self.assertNotIn(socket.AF_INET6, {r[0] for r in res})

    def test_api_error_description(self):
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value.__enter__.return_value = self._fake_urlopen(
                b'{"ok": false, "description": "Bad Request"}')
            ok, err = telegram._tg_request("tok", "x", {})
        self.assertFalse(ok)
        self.assertIn("Bad Request", err)

    def test_http_error(self):
        import urllib.error
        exc = urllib.error.HTTPError("u", 418, "teapot", {}, None)
        exc.read = mock.Mock(return_value=b"teapot body")
        exc.code = 418
        with mock.patch("urllib.request.urlopen", side_effect=exc):
            ok, err = telegram._tg_request("tok", "x", {})
        self.assertFalse(ok)
        self.assertIn("418", err)
        self.assertIn("teapot body", err)

    def test_multipart_contains_filename_and_boundary(self):
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value.__enter__.return_value = self._fake_urlopen(
                b'{"ok": true}')
            ok, _ = telegram._tg_request(
                "tok", "sendDocument", {"chat_id": "1"},
                files=[("document", "file.md", b"hello")])
        self.assertTrue(ok)
        req = m.call_args.args[0]
        ct = self._header(req, "Content-Type")
        self.assertIsNotNone(ct)
        self.assertTrue(ct.startswith("multipart/form-data; boundary="))
        boundary = ct.split("boundary=")[1]
        self.assertIn(b'filename="file.md"', req.data)
        self.assertIn(b"hello", req.data)
        self.assertTrue(req.data.endswith(f"--{boundary}--\r\n".encode()))


# Владелец проекта: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия неповторима, новая — ещё лучше.
class TgGetChatIdTest(unittest.TestCase):
    @staticmethod
    def _urlopen_body(body):
        resp = mock.Mock()
        resp.read.return_value = body
        return resp

    def test_uses_offset_minus_1(self):
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value.__enter__.return_value = self._urlopen_body(
                b'{"ok": true, "result": []}')
            telegram._tg_get_chat_id("tok")
        url = m.call_args.args[0].full_url
        self.assertIn("offset=-1", url)

    def test_takes_last_message_chat_id(self):
        body = json.dumps({"ok": True, "result": [
            {"update_id": 1, "message": {"chat": {"id": 111}}},
            {"update_id": 2, "message": {"chat": {"id": 222}}},
        ]}).encode()
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value.__enter__.return_value = self._urlopen_body(body)
            chat_id, err = telegram._tg_get_chat_id("tok")
        self.assertEqual(chat_id, "222")
        self.assertIsNone(err)

    def test_empty_result_asks_for_start(self):
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value.__enter__.return_value = self._urlopen_body(
                b'{"ok": true, "result": []}')
            chat_id, err = telegram._tg_get_chat_id("tok")
        self.assertIsNone(chat_id)
        self.assertIn("/start", err)

    def test_no_token(self):
        chat_id, err = telegram._tg_get_chat_id("")
        self.assertIsNone(chat_id)
        self.assertIn("токен", err)


class TgGetUpdatesTest(unittest.TestCase):
    def test_url_has_timeout_and_offset(self):
        resp = mock.Mock()
        resp.read.return_value = b'{"ok": true, "result": []}'
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value.__enter__.return_value = resp
            updates, _ = telegram._tg_get_updates("tok", offset=7)
        self.assertEqual(updates, [])
        url = m.call_args.args[0]
        self.assertIn("timeout=25", url)
        self.assertIn("offset=7", url)

    def test_api_error(self):
        resp = mock.Mock()
        resp.read.return_value = b'{"ok": false, "description": "Conflict"}'
        with mock.patch("urllib.request.urlopen") as m:
            m.return_value.__enter__.return_value = resp
            updates, err = telegram._tg_get_updates("tok")
        self.assertIsNone(updates)
        self.assertIn("Conflict", err)


if __name__ == "__main__":
    unittest.main()

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
