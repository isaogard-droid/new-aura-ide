#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты Telegram-логики telegram.py — без сети и без ключа.

Запуск (из корня проекта, через venv — там numpy/sounddevice):
    ./venv/bin/python -m unittest discover -s tests -t .
"""

import unittest

import telegram


class TgSkipReasonTest(unittest.TestCase):
    def test_off(self):
        self.assertIsNotNone(telegram._tg_skip_reason(False, "tok", "1"))

    def test_no_token(self):
        self.assertIsNotNone(telegram._tg_skip_reason(True, "", "1"))

    def test_no_chat_id(self):
        self.assertIsNotNone(telegram._tg_skip_reason(True, "tok", ""))

    def test_ready(self):
        self.assertIsNone(telegram._tg_skip_reason(True, "tok", "1"))


class TgMdToHtmlTest(unittest.TestCase):
    def test_heading_h1(self):
        self.assertEqual(telegram._tg_md_to_html("# Заголовок"),
                         "<b>Заголовок</b>")

    def test_heading_h2_h3(self):
        self.assertEqual(telegram._tg_md_to_html("## Два\n### Три"),
                         "<b>Два</b>\n<b>Три</b>")

    def test_heading_with_leading_spaces(self):
        self.assertEqual(telegram._tg_md_to_html("  ## Отступ"),
                         "<b>Отступ</b>")

    def test_bold(self):
        self.assertEqual(telegram._tg_md_to_html("текст **жирный** конец"),
                         "текст <b>жирный</b> конец")

    def test_escape_ampersand_and_angle(self):
        out = telegram._tg_md_to_html("a & b < c > d")
        self.assertEqual(out, "a &amp; b &lt; c &gt; d")

    def test_bold_multiline(self):
        out = telegram._tg_md_to_html("строка1\n**строка2**")
        self.assertEqual(out, "строка1\n<b>строка2</b>")


if __name__ == "__main__":
    unittest.main()

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
