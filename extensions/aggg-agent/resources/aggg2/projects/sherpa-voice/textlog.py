#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Единый текстовый логгер: ВСЕ текстовые сущности (задача/промпт, ответ,
саммари, континуум-контекст, сводка дня) — в txt-файлы с датой-временем
и автоотправкой в Telegram файлом.

Файлы: ~/sherpa-voice/logs/<тип>_<ГГГГ-ММ-ДД_ЧЧ-ММ-СС>.txt
Telegram: если включён — файл уходит sendDocument с подписью типа.

Использование:
    import textlog
    textlog.save("задача", "текст промпта")
    textlog.save("ответ", "текст ответа", to_tg=True)
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""
import os
import time

LOG_DIR = os.path.expanduser("~/sherpa-voice/logs")

# Типы: русское имя в файле + подпись в Telegram
KINDS = {
    "задача": ("задача", "📌 Задача (промпт)"),
    "ответ": ("ответ", "💬 Ответ"),
    "саммари": ("саммари", "📝 Саммари"),
    "континуум": ("континуум", "🔁 Континуум-контекст"),
    "сводка": ("сводка", "📅 Сводка дня"),
    "транскрипт": ("транскрипт", "🎤 Транскрипт"),
}


def save(kind, text, to_tg=False):
    """Сохраняет текст в txt с датой-временем; при to_tg — отправляет
    файлом в Telegram. Возвращает (path, ok_tg, err_tg)."""
    if not text or not text.strip():
        return None, None, None
    fname, caption = KINDS.get(kind, (kind, kind))
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(LOG_DIR, exist_ok=True)
    path = os.path.join(LOG_DIR, f"{fname}_{ts}.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# {caption}\n\n")
        f.write(text.rstrip() + "\n")
    print(f"[log] {fname}_{ts}.txt")
    ok_tg = err_tg = None
    if to_tg:
        try:
            from telegram import tg_send_text_file
            ok_tg, err_tg = tg_send_text_file(
                text, f"{fname}_{ts}.txt", caption=caption)
        except Exception as e:  # noqa: BLE001 — логгер не должен ронять
            err_tg = str(e)
    return path, ok_tg, err_tg

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
