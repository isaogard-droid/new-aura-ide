#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты Telegram-логики telegram.py — без сети и без ключа.

Резка god-файла (528 строк) — карта «где какие тесты»:
- test_telegram_format.py — TgSkipReasonTest, TgMdToHtmlTest;
- test_telegram_send.py — TgSendTextTest, TgSendRichTextTest, TgSendResultTest;
- test_telegram_request.py — TgRequestTest, TgGetChatIdTest, TgGetUpdatesTest;
- test_telegram_updates.py — TgHandleUpdateTest, TgTextCommandTest.

Запуск (из корня проекта, через venv — там numpy/sounddevice):
    ./venv/bin/python -m unittest discover -s tests -t .
"""

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
