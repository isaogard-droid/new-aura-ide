#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""chat.publish — публикация транскрипта из диалога.
Вынесено из chat.py механически (verbatim), 15.08.2026 — гейт god-файлов."""
from publish import publish_result
from store import append_mix

from .polish import _polish_text


def _publish_transcript(text, notify_once=False, auto_export=False):
    """Единый путь публикации записи: полировка → подмешка → publish
    (буфер, история, ТГ «Транскрипт» с кнопками) → автоэкспорт.
    Один для голоса (main, микрофон) и текстового ввода (главный экран) —
    текст с клавиатуры обрабатывается как диктовка, чтобы оба режима
    вели себя одинаково (см. CHANGELOG: раньше текст уходил в чат-режим
    _chat_send и в ТГ слался ответ ИИ вместо полировки).
    Возвращает обработанный текст (для меню действий)."""
    from export import save_text_export
    from telegram import _tg_keyboard
    text = _polish_text(text)
    text, added, mix = append_mix(text)
    publish_result(text, "📝 Транскрипт",
                   reply_markup=_tg_keyboard(),
                   notify_once=notify_once,
                   tg_footer=mix if added else None)
    if auto_export:
        md_path, pdf_path, err = save_text_export(text)
        if err:
            print(f"[i] {err}")
        print(f"[✓] Автоэкспорт: MD {md_path}" +
              (f", PDF {pdf_path}" if pdf_path else ""))
    return text


# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
