#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты telegram.ratelimit — входной antiflood per-user.

Запуск (из корня проекта, через venv — там numpy/sounddevice):
    ./venv/bin/python -m unittest discover -s tests -t .
"""

import unittest
from unittest import mock

from telegram import ratelimit


class VoiceAllowedTest(unittest.TestCase):
    def setUp(self):
        ratelimit.reset_for_tests()

    def test_allows_up_to_limit(self):
        for _ in range(ratelimit.TG_RATE_VOICE_PER_MIN):
            ok, retry = ratelimit.voice_allowed(1)
            self.assertTrue(ok)
            self.assertEqual(retry, 0)

    def test_blocks_over_limit_with_retry_after(self):
        for _ in range(ratelimit.TG_RATE_VOICE_PER_MIN):
            ratelimit.voice_allowed(1)
        ok, retry = ratelimit.voice_allowed(1)
        self.assertFalse(ok)
        self.assertGreater(retry, 0)

    def test_other_user_not_blocked(self):
        for _ in range(ratelimit.TG_RATE_VOICE_PER_MIN):
            ratelimit.voice_allowed(1)
        ok, _ = ratelimit.voice_allowed(2)
        self.assertTrue(ok)

    def test_window_slides_after_ttl(self):
        """Старые записи выпадают из окна — юзер снова пропускается."""
        with mock.patch("telegram.ratelimit.time.monotonic",
                        return_value=100.0):
            for _ in range(ratelimit.TG_RATE_VOICE_PER_MIN):
                ratelimit.voice_allowed(1)
            ok, _ = ratelimit.voice_allowed(1)
            self.assertFalse(ok)
        # время ушло за окно — записи выпадают, юзер пропускается
        with mock.patch("telegram.ratelimit.time.monotonic",
                        return_value=100.0 + ratelimit._WINDOW_SEC + 1):
            ok, _ = ratelimit.voice_allowed(1)
            self.assertTrue(ok)


class ActionAllowedTest(unittest.TestCase):
    def setUp(self):
        ratelimit.reset_for_tests()

    def test_action_limit_independent_of_voice(self):
        """Отдельный bucket: голосовые не тратят лимит действий."""
        for _ in range(ratelimit.TG_RATE_ACTION_PER_MIN):
            ok, _ = ratelimit.action_allowed(1)
            self.assertTrue(ok)
        ok, retry = ratelimit.action_allowed(1)
        self.assertFalse(ok)
        self.assertGreater(retry, 0)

    def test_zero_limit_is_unlimited(self):
        with mock.patch.object(ratelimit, "TG_RATE_ACTION_PER_MIN", 0):
            for _ in range(100):
                ok, _ = ratelimit.action_allowed(1)
                self.assertTrue(ok)


class CallbackAntifloodTest(unittest.TestCase):
    """Интеграция: menu._impl_tg_handle_callback не пускает в DeepSeek,
    если лимит действий исчерпан; бесплатные действия не лимитируются."""

    def setUp(self):
        # unittest исполняет методы в алфавитном порядке, а _TG_BUSY/_TG_LAST
        # — модульное состояние «занято/дебаунс»; без сброса второй экспорт
        # в том же чате выглядит «уже готовится» (загрязнение между тестами).
        from telegram.menu import _TG_BUSY, _TG_LAST
        _TG_BUSY.clear()
        _TG_LAST.clear()

    def _callback(self, data, user_id=None):
        cq = {"id": "q1", "data": data,
              "message": {"chat": {"id": 7}}}
        if user_id is not None:
            cq["from"] = {"id": user_id}
        return cq

    def test_summary_blocked_when_limit_hit(self):
        ratelimit.reset_for_tests()
        for _ in range(ratelimit.TG_RATE_ACTION_PER_MIN):
            ratelimit.action_allowed(9)
        with mock.patch("telegram.menu._tg_request") as req, \
             mock.patch("telegram.menu._tg_state_load", return_value={}):
            from telegram.menu import _impl_tg_handle_callback
            _impl_tg_handle_callback(self._callback("summary", 9), "tok")
        texts = [c.kwargs.get("text") or c.args[2].get("text", "")
                 for c in req.call_args_list if c.args[1] == "sendMessage"]
        self.assertTrue(any("Слишком часто" in t for t in texts),
                        f"нет понятного сообщения, вызовы: {req.call_args_list}")

    def test_export_not_limited(self):
        """Экспорт — бесплатное действие, antiflood его не режет."""
        ratelimit.reset_for_tests()
        with mock.patch("telegram.menu._tg_request") as req, \
             mock.patch("telegram.menu._tg_state_load",
                        return_value={"text": "текст"}), \
             mock.patch("telegram.menu._tg_do_export") as exp:
            from telegram.menu import _impl_tg_handle_callback
            _impl_tg_handle_callback(self._callback("export", 9), "tok")
        exp.assert_called_once()

    def test_export_limited_user_not_blocked_by_action_bucket(self):
        """Юзер с исчерпанным лимитом действий всё равно может экспорт."""
        ratelimit.reset_for_tests()
        for _ in range(ratelimit.TG_RATE_ACTION_PER_MIN):
            ratelimit.action_allowed(9)
        with mock.patch("telegram.menu._tg_request") as req, \
             mock.patch("telegram.menu._tg_state_load",
                        return_value={"text": "текст"}), \
             mock.patch("telegram.menu._tg_do_export") as exp:
            from telegram.menu import _impl_tg_handle_callback
            _impl_tg_handle_callback(self._callback("export", 9), "tok")
        exp.assert_called_once()


if __name__ == "__main__":
    unittest.main()

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
