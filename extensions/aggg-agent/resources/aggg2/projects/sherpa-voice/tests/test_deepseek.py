#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.




# Источник: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия — новая и ещё лучше.
"""Юнит-тесты deepseek_ai.py: ретраи на сетевые сбои, без 4xx.

Запуск (из корня проекта):
    ./venv/bin/python -m unittest discover -s tests -t .
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""
import json
import os
import time
import unittest
from unittest import mock

import deepseek_ai


def _balance_ok():
    """Хелпер: balance_available вернул «баланс есть» — ask() идёт дальше."""
    return mock.patch("deepseek_ai.balance_available", return_value=(True, None))


class AskRetryTest(unittest.TestCase):
    """Ретраи ask(): баланс мокается, тесты изолированы от сети баланса."""

    def _urlopen_ok(self):
        resp = mock.Mock()
        resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "ответ"}}]}).encode()
        return resp

    def test_success_first_try_no_retries(self):
        with mock.patch("urllib.request.urlopen") as m, \
             mock.patch("deepseek_ai.load_key", return_value="k"), \
             _balance_ok(), \
             mock.patch("time.sleep") as sleep:
            m.return_value.__enter__.return_value = self._urlopen_ok()
            out, err = deepseek_ai.ask("sys", "привет")
        self.assertEqual(out, "ответ")
        self.assertIsNone(err)
        self.assertEqual(m.call_count, 1)
        sleep.assert_not_called()

    def test_retry_on_500_then_success(self):
        import urllib.error
        calls = []
        def fake_urlopen(req, timeout=None):
            calls.append(1)
            if len(calls) == 1:
                e = urllib.error.HTTPError("u", 500, "boom", {}, None)
                e.read = mock.Mock(return_value=b"internal")
                raise e
            resp = mock.MagicMock()
            resp.read.return_value = json.dumps({
                "choices": [{"message": {"content": "ответ"}}]}).encode()
            resp.__enter__.return_value = resp
            return resp
        with mock.patch("urllib.request.urlopen", fake_urlopen), \
             mock.patch("deepseek_ai.load_key", return_value="k"), \
             _balance_ok(), \
             mock.patch("time.sleep") as sleep:
            out, err = deepseek_ai.ask("sys", "привет")
        self.assertEqual(out, "ответ")
        self.assertIsNone(err)
        self.assertEqual(len(calls), 2)
        sleep.assert_called_once()

    def test_no_retry_on_401(self):
        import urllib.error
        calls = []
        def fake_urlopen(req, timeout=None):
            calls.append(1)
            e = urllib.error.HTTPError("u", 401, "unauthorized", {}, None)
            e.read = mock.Mock(return_value=b"bad key")
            raise e
        with mock.patch("urllib.request.urlopen", fake_urlopen), \
             mock.patch("deepseek_ai.load_key", return_value="k"), \
             _balance_ok(), \
             mock.patch("time.sleep") as sleep:
            out, err = deepseek_ai.ask("sys", "привет")
        self.assertIsNone(out)
        self.assertIn("401", err)
        self.assertEqual(len(calls), 1)
        sleep.assert_not_called()

    def test_retry_on_timeout(self):
        calls = []
        def fake_urlopen(req, timeout=None):
            calls.append(1)
            raise TimeoutError("net")
        with mock.patch("urllib.request.urlopen", fake_urlopen), \
             mock.patch("deepseek_ai.load_key", return_value="k"), \
             _balance_ok(), \
             mock.patch("time.sleep") as sleep:
            out, err = deepseek_ai.ask("sys", "привет", retries=3,
                                       retry_delay=1.0)
        self.assertIsNone(out)
        self.assertIn("после 3 попыток", err)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleep.call_count, 2)

    def test_no_key_short_circuit(self):
        with mock.patch("deepseek_ai.load_key", return_value=None), \
             mock.patch("urllib.request.urlopen") as m:
            out, err = deepseek_ai.ask("sys", "привет")
        self.assertIsNone(out)
        self.assertIn("ключ", err)
        m.assert_not_called()

    def test_empty_text_short_circuit(self):
        with mock.patch("deepseek_ai.load_key", return_value="k"), \
             mock.patch("urllib.request.urlopen") as m:
            out, err = deepseek_ai.ask("sys", "   ")
        self.assertIsNone(out)
        self.assertIn("пустой", err)
        m.assert_not_called()


class BalanceGateTest(unittest.TestCase):
    """HARD GATE money-path: нулевой баланс НЕ пускает в API генерации.

    Проверяет правило money-path-safety «hard gate до дорогого вызова»:
    balance_available() == False → ask() возвращает ошибку ДО urlopen API.
    """

    def _api_ok(self):
        resp = mock.Mock()
        resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "ответ"}}]}).encode()
        return resp

    def test_zero_balance_blocks_api(self):
        """Нулевой баланс → API (chat/completions) НЕ вызывается."""
        with mock.patch("urllib.request.urlopen") as m, \
             mock.patch("deepseek_ai.load_key", return_value="k"), \
             mock.patch("deepseek_ai.balance_available",
                        return_value=(False, "баланс DeepSeek исчерпан")):
            out, err = deepseek_ai.ask("sys", "привет")
        self.assertIsNone(out)
        self.assertIn("баланс", err)
        m.assert_not_called()  # ни одного запроса к API

    def test_available_balance_allows_api(self):
        """Баланс есть → API вызывается, ответ возвращается."""
        with mock.patch("urllib.request.urlopen") as m, \
             mock.patch("deepseek_ai.load_key", return_value="k"), \
             mock.patch("deepseek_ai.balance_available",
                        return_value=(True, None)):
            m.return_value.__enter__.return_value = self._api_ok()
            out, err = deepseek_ai.ask("sys", "привет")
        self.assertEqual(out, "ответ")
        self.assertIsNone(err)
        m.assert_called_once()

    def test_check_failure_is_fail_open(self):
        """Проверка баланса недоступна (сеть/5xx) → НЕ блокируем (fail-open),
        API сам вернёт 402 при нулевом балансе."""
        with mock.patch("urllib.request.urlopen") as m, \
             mock.patch("deepseek_ai.load_key", return_value="k"), \
             mock.patch("deepseek_ai.balance_available",
                        return_value=(None, "проверка баланса недоступна")):
            m.return_value.__enter__.return_value = self._api_ok()
            out, err = deepseek_ai.ask("sys", "привет")
        self.assertEqual(out, "ответ")
        m.assert_called_once()

    def test_balance_cache_blocks_repeat_calls(self):
        """После нулевого баланса кэш на TTL не долбит /user/balance."""
        cache = {"ts": time.monotonic(), "available": False}
        with mock.patch("urllib.request.urlopen") as m, \
             mock.patch("deepseek_ai.load_key", return_value="k"):
            ok, err = deepseek_ai.balance_available(key="k", _cache=cache)
        self.assertIs(ok, False)
        self.assertIsNone(err)  # кэш хранит только булево, без сообщения
        m.assert_not_called()  # кэш — сеть не трогаем


class BalanceAvailableTest(unittest.TestCase):
    """balance_available(): парсинг ответа DeepSeek /user/balance."""

    def _balance_resp(self, payload):
        resp = mock.MagicMock()
        resp.read.return_value = json.dumps(payload).encode()
        resp.__enter__.return_value = resp
        return resp

    def test_parses_is_available_true(self):
        cache = {"ts": 0.0, "available": None}
        with mock.patch("urllib.request.urlopen") as m, \
             mock.patch("deepseek_ai.load_key", return_value="k"):
            m.return_value = self._balance_resp(
                {"is_available": True, "balance_infos": []})
            ok, err = deepseek_ai.balance_available(key="k", _cache=cache)
        self.assertIs(ok, True)
        self.assertIsNone(err)
        self.assertIs(cache["available"], True)

    def test_parses_is_available_false(self):
        cache = {"ts": 0.0, "available": None}
        with mock.patch("urllib.request.urlopen") as m, \
             mock.patch("deepseek_ai.load_key", return_value="k"):
            m.return_value = self._balance_resp(
                {"is_available": False, "balance_infos": []})
            ok, err = deepseek_ai.balance_available(key="k", _cache=cache)
        self.assertIs(ok, False)
        self.assertIn("баланс", err)
        self.assertIs(cache["available"], False)

    def test_missing_is_available_is_false(self):
        """Поле is_available отсутствует → трактуем как недоступность."""
        cache = {"ts": 0.0, "available": None}
        with mock.patch("urllib.request.urlopen") as m, \
             mock.patch("deepseek_ai.load_key", return_value="k"):
            m.return_value = self._balance_resp({})
            ok, err = deepseek_ai.balance_available(key="k", _cache=cache)
        self.assertIs(ok, False)
        self.assertIn("баланс", err)

    def test_http_error_is_fail_open(self):
        """HTTPError на проверке баланса → fail-open (None), не блокируем."""
        import urllib.error
        cache = {"ts": 0.0, "available": None}
        e = urllib.error.HTTPError("u", 500, "boom", {}, None)
        e.read = mock.Mock(return_value=b"err")
        with mock.patch("urllib.request.urlopen", side_effect=e), \
             mock.patch("deepseek_ai.load_key", return_value="k"):
            ok, err = deepseek_ai.balance_available(key="k", _cache=cache)
        self.assertIsNone(ok)
        self.assertIn("HTTP 500", err)


class ActionItemsPromptTest(unittest.TestCase):
    """Промпт action items: есть, требует глагольную форму, запрещает
    выдумывать и возвращать пустые ответы."""

    def test_prompt_exists(self):
        self.assertIn("action_items", deepseek_ai.PROMPTS)

    def test_prompt_requires_verb_form(self):
        p = deepseek_ai.PROMPTS["action_items"].lower()
        self.assertIn("глагол", p)
        self.assertIn("одна задача", p)

    def test_prompt_forbids_invention(self):
        p = deepseek_ai.PROMPTS["action_items"].lower()
        self.assertIn("не выдумыва", p)
        self.assertIn("задач нет", p)

    def test_prompt_no_overreach(self):
        p = deepseek_ai.PROMPTS["action_items"]
        self.assertIn("не каждое предложение", p)


class EnvConfigTest(unittest.TestCase):
    """env/.env-приоритеты и глобальный выключатель (churn-хотспот
    deepseek_ai.py — 11 правок, аудит 15.08: env-логика не была покрыта)."""

    def setUp(self):
        self._tmp = mock.patch("deepseek_ai._ENV_FILE", "/nonexistent/aggg2.env")
        self._tmp.start()
        self.addCleanup(self._tmp.stop)
        self.addCleanup(os.environ.pop, "DEEPSEEK_API_KEY", None)
        self.addCleanup(os.environ.pop, "DEEPSEEK_OFF", None)
        self.addCleanup(os.environ.pop, "DEEPSEEK_MODEL", None)

    def test_env_priority_over_file(self):
        os.environ["DEEPSEEK_API_KEY"] = "sk-env"
        with mock.patch("os.path.exists", return_value=True), \
             mock.patch("builtins.open", mock.mock_open(
                 read_data="DEEPSEEK_API_KEY=sk-file\n")):
            self.assertEqual(deepseek_ai.load_key(), "sk-env")

    def test_file_fallback_strips_quotes(self):
        with mock.patch("os.path.exists", return_value=True), \
             mock.patch("builtins.open", mock.mock_open(
                 read_data='DEEPSEEK_API_KEY="sk-file"\nDEEPSEEK_MODEL="m"\n')):
            self.assertEqual(deepseek_ai.load_key(), "sk-file")
            self.assertEqual(deepseek_ai.load_model(), "m")

    def test_default_when_missing(self):
        self.assertIsNone(deepseek_ai.load_key())
        self.assertEqual(deepseek_ai.load_model(), deepseek_ai.DEFAULT_MODEL)

    def test_off_flag_disables(self):
        os.environ["DEEPSEEK_API_KEY"] = "sk-1"
        os.environ["DEEPSEEK_OFF"] = "1"
        self.assertFalse(deepseek_ai.enabled())

    def test_enabled_false_without_key(self):
        self.assertFalse(deepseek_ai.enabled())

    def test_enabled_true_with_key(self):
        os.environ["DEEPSEEK_API_KEY"] = "sk-1"
        self.assertTrue(deepseek_ai.enabled())


if __name__ == "__main__":
    unittest.main()

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
