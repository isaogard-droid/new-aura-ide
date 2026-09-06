#!/usr/bin/env python3
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""publish — единый путь публикации результата в sherpa-voice: буфер,
история, Telegram. Слой 3: зависит от store и ui_utils (вынесено из
монолита transcribe.py).

Слои: ui_utils → store → publish → chat (transcribe.py — facade).
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""
import os

import store
import ui_utils
from ui_utils import c_err, c_ok, notify


def publish_result(text, prefix=None, reply_markup=None, chat_id=None,
                   to_history=True, to_tg=True, to_file=True,
                   to_clipboard=True, notify_once=False, tg_footer=None):
    """Единый путь публикации результата: буфер (или файл, если буфер
    недоступен), история, состояние Telegram, отправка в Telegram.

    Раньше этот блок был продублирован в трёх местах (main, deepseek_menu,
    _tg_handle_update) и разошёлся: в deepseek_menu не писались история и
    состояние Telegram. Флаги сохраняют поведение каждого места.
    tg_footer — отдельное сообщение после основного (например, подмешка):
    основной текст остаётся чистым, футер уходит вторым сообщением.
    Возвращает (отправлено?, ошибка_или_None)."""
    from telegram import _tg_send_result, _tg_state_save, load_telegram
    if to_clipboard:
        copied = ui_utils.copy_to_clipboard(text)
        if copied:
            print(c_ok("[✓] Скопировано в буфер обмена"))
        elif to_file:
            os.makedirs(os.path.dirname(ui_utils.LAST_TEXT_FILE), exist_ok=True)
            with open(ui_utils.LAST_TEXT_FILE, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"[✓] Буфер недоступен — текст сохранён: {ui_utils.LAST_TEXT_FILE}")
        else:
            print("[i] Буфер недоступен — результат остался в консоли.")
        if notify_once:
            notify("Sherpa Voice", "Текст скопирован в буфер обмена.")
    if to_history:
        store._append_history(text)
    ok_tg, err_tg = True, None
    if to_tg:
        _enabled_tg, _tok_tg, _chat_tg = load_telegram()
        chat_id = chat_id or _chat_tg
        if chat_id:
            _tg_state_save(chat_id, text)
        ok_tg, err_tg = _tg_send_result(text, prefix, chat_id=chat_id,
                                        reply_markup=reply_markup,
                                        footer=tg_footer)
        if ok_tg:
            print(c_ok("[✓] Отправлено в Telegram"))
        elif err_tg:
            print(c_err(f"[✗] {err_tg}"))
    return ok_tg, err_tg

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
