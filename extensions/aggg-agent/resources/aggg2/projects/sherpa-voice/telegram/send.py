#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""telegram.send — отправка: text/rich/file/result/document."""
import os
import time

from .api import _tg_skip_reason

_PREFIX_BOLD = {
    "📝 Транскрипт": "Транскрипт",
    "📋 Саммари": "Саммари",
    "💬 Ответ": "Ответ",
    "💻 Кодинг-промт": "Кодинг-промт",
}

def _tg_md_to_html(text):
    """Маркдаун из ответов модели → HTML для Telegram: экранирует & < >,
    заголовки (# / ## / ###) и **жирный** превращает в <b>…</b>.
    Заголовков Telegram не понимает — в проде их принято делать жирными."""
    import html as _h
    import re
    text = _h.escape(text)
    lines = []
    for line in text.split("\n"):
        s = line.lstrip()
        if s.startswith("### "):
            lines.append("<b>" + s[4:] + "</b>")
        elif s.startswith("## "):
            lines.append("<b>" + s[3:] + "</b>")
        elif s.startswith("# "):
            lines.append("<b>" + s[2:] + "</b>")
        else:
            lines.append(line)
    text = "\n".join(lines)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)

def _impl_tg_send_text(text, prefix=None, chat_id=None, reply_markup=None):
    """Отправляет текст в Telegram, если режим включён. Текст длиннее 4096
    символов режется на сообщения (лимит Bot API). chat_id — явный (ответ
    на голосовое); по умолчанию — из настроек. reply_markup — inline-кнопки
    действий, вешаются на первое сообщение.
    Значки-префиксы превращаются в жирный текст, маркдаун модели (## и
    **жирный**) — в <b>…</b> (parse_mode=HTML; если Telegram не сможет
    распарсить чанк — он уйдёт без форматирования).
    Возвращает (отправлено?, ошибка_или_None); при пропуске — причина."""
    enabled, token, default_chat = load_telegram()
    chat_id = chat_id or default_chat
    reason = _tg_skip_reason(enabled, token, chat_id)
    if reason:
        return False, f"Telegram: {reason}"
    if prefix:
        label = _PREFIX_BOLD.get(prefix, prefix)
        text = f"<b>{label}</b>\n\n" + _tg_md_to_html(text)
    else:
        text = _tg_md_to_html(text)
    for i in range(0, len(text), 4096):
        payload = {"chat_id": chat_id, "text": text[i:i + 4096],
                   "parse_mode": "HTML"}
        if reply_markup and i == 0:
            payload["reply_markup"] = reply_markup
        ok, err = _tg_request(token, "sendMessage", payload)
        if not ok and ("parse" in (err or "").lower()
                       or "entities" in (err or "").lower()):
            payload.pop("parse_mode", None)  # фолбэк: чанк без разметки
            ok, err = _tg_request(token, "sendMessage", payload)
        if not ok:
            return False, err
    return True, None

def _impl_tg_send_rich_text(text, chat_id=None, reply_markup=None,
                      title="📝 Транскрипт", max_len=4000):
    """Отправляет транскрипт как rich-сообщение (официальный Rich Messages,
    Bot API 10.1): заголовок + широкая цитата (pullquote) + разделитель.
    Для текста длиннее max_len или при ошибке API возвращает (False,
    причина) — вызывающий откатывается на обычный текст. Возвращает
    (отправлено?, ошибка_или_None); при пропуске — причина."""
    enabled, token, default_chat = load_telegram()
    chat_id = chat_id or default_chat
    reason = _tg_skip_reason(enabled, token, chat_id)
    if reason:
        return False, f"Telegram: {reason}"
    if len(text) > max_len:
        return False, "rich: текст слишком длинный — нужен обычный sendMessage"
    payload = {
        "chat_id": chat_id,
        "rich_message": {"blocks": [
            {"type": "heading", "text": title, "size": 2},
            {"type": "pullquote", "text": text},
            {"type": "divider"},
        ]},
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    ok, err = _tg_request(token, "sendRichMessage", payload)
    if not ok:
        return False, err
    return True, None

def _tg_file_ts():
    """Метка времени для имён файлов: 2026-08-10_19-45-30."""
    return time.strftime("%Y-%m-%d_%H-%M-%S")

def _tg_file_kind(prefix):
    """По префиксу результата — каким файлом слать в Telegram:
    ВСЕ результаты — документом .txt с датой-временем в имени (по файлу
    видно, что к чему относится): транскрипт, промпт, саммари, ответ,
    задачи, кодинг-промт, итог дня."""
    if not prefix:
        return None
    p = prefix.lower()
    if "транскрипт" in p:
        return "транскрипт"
    if "промпт" in p:
        return "промпт"
    if "саммари" in p:
        return "саммари"
    if "ответ" in p:
        return "ответ"
    if "задач" in p:
        return "задачи"
    if "кодинг" in p or "ревью" in p:
        return "кодинг"
    if "итог" in p or "сводк" in p:
        return "сводка"
    return "результат"

def _impl_tg_send_text_file(content, filename, chat_id=None, caption=None,
                      reply_markup=None):
    """Отправляет текст как файл (sendDocument): транскрипт/промпт/подмешка
    уходят отдельным .txt с датой-временем в имени — по файлу видно, что
    к чему относится. caption — короткая подпись, reply_markup — кнопки
    (sendDocument поддерживает оба). Возвращает (ok, err)."""
    enabled, token, default_chat = load_telegram()
    chat_id = chat_id or default_chat
    reason = _tg_skip_reason(enabled, token, chat_id)
    if reason:
        return False, f"Telegram: {reason}"
    blob = content.encode("utf-8")
    payload = {"chat_id": chat_id}
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _tg_request(token, "sendDocument", payload,
                       [("document", filename, blob)])

def _impl_tg_send_result(text, prefix=None, chat_id=None, reply_markup=None,
                    footer=None):
    """Единая отправка результата: ВСЕ результаты — документом .txt
    с датой-временем в имени (sendDocument: транскрипт, промпт, задача,
    саммари, ответ, кодинг, сводка) + подпись и кнопки. При ошибке
    файла (длинный текст и т.п.) — обычный sendMessage.
    footer — подмешка/подпись: уходит отдельным файлом
    подмешка_<дата-время>.txt (sendDocument), а не вшивается в текст и не
    слается сообщением.

    Раньше rich-путь был у ответов на голосовые из Telegram, а файлами
    слались только транскрипты/промпты. Теперь единый лог всех текстовых
    сущностей: всё — файлами .txt с датой-временем.
    Возвращает (отправлено?, ошибка_или_None)."""
    title = _PREFIX_BOLD.get(prefix, prefix) if prefix else "Транскрипт"
    kind = _tg_file_kind(prefix) or "результат"
    ts = _tg_file_ts()
    ok, err = tg_send_text_file(
        text, f"{kind}_{ts}.txt", chat_id=chat_id, caption=title,
        reply_markup=reply_markup)
    if not ok:
        # файл не прошёл (слишком длинный/ошибка) — фолбэк обычным текстом
        ok, err = tg_send_text(text, prefix, chat_id=chat_id,
                               reply_markup=reply_markup)
    if ok and footer:
        fok, ferr = tg_send_text_file(
            footer, f"подмешка_{_tg_file_ts()}.txt", chat_id=chat_id)
        if not fok and ferr:
            print(f"[✗] Футер не отправлен: {ferr}")
    return ok, err

def tg_send_document(path, chat_id=None):
    """Отправляет файл (MD/PDF) в Telegram, если режим включён. chat_id —
    явный (ответ на кнопку Экспорт в чате); по умолчанию — из настроек.
    Возвращает (отправлено?, ошибка_или_None); при пропуске — причина."""
    enabled, token, default_chat = load_telegram()
    chat_id = chat_id or default_chat
    reason = _tg_skip_reason(enabled, token, chat_id)
    if reason:
        return False, f"Telegram: {reason}"
    try:
        with open(path, "rb") as f:
            blob = f.read()
    except OSError as e:
        return False, f"Telegram: файл не прочитан ({e})"
    return _tg_request(token, "sendDocument", {"chat_id": chat_id},
                       [("document", os.path.basename(path), blob)])
import telegram as _telegram  # noqa: E402 — форвардеры (патчи-совместимость)


def _fwd_route(name):
    def _forward(*args, **kwargs):
        return getattr(_telegram, name)(*args, **kwargs)
    _forward.__name__ = name
    return _forward

tg_send_text = _fwd_route('tg_send_text')
tg_send_rich_text = _fwd_route('tg_send_rich_text')
tg_send_text_file = _fwd_route('tg_send_text_file')
_tg_send_result = _fwd_route('_tg_send_result')
load_telegram = _fwd_route('load_telegram')
_tg_request = _fwd_route('_tg_request')

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
