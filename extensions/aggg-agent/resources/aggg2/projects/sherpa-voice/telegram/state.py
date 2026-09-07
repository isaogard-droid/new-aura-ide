#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""telegram.state — конфиг-состояние: load/save, state-путь,
клавиатура."""
import json
import os

from transcribe import (
    TELEGRAM_FILE,
    _atomic_write,
)

_TG_STATE = {}

_TG_ACTIONS = [
    # ряд 1 — текстовые действия (по 2 кнопки: на маленьком экране видно)
    [
        {"text": "📋 Саммари", "callback_data": "summary", "style": "success"},
        {"text": "💬 Ответить", "callback_data": "answer", "style": "primary"},
    ],
    # ряд 2 — сложное и сохранение
    [
        {"text": "💻 Кодинг-промт", "callback_data": "coding", "style": "danger"},
        {"text": "💾 Экспорт", "callback_data": "export", "style": "success"},
    ],
    # ряд 3 — информация
    [
        {"text": "📖 Документация", "callback_data": "docs", "style": "primary"},
    ],
]

def load_telegram():
    """Настройки Telegram: (включено?, токен, chat_id).
    Файл: первая строка ON/OFF, вторая токен бота, третья chat_id."""
    try:
        with open(TELEGRAM_FILE, encoding="utf-8") as f:
            parts = f.read().split("\n", 2)
        enabled = parts[0].strip().upper() == "ON"
        token = parts[1].strip() if len(parts) > 1 else ""
        chat_id = parts[2].strip() if len(parts) > 2 else ""
    except (OSError, ValueError):
        return False, "", ""
    return enabled, token, chat_id

def save_telegram(enabled, token, chat_id):
    """Сохраняет настройки Telegram. Ошибка не роняет поток.
    Токен бота — секрет: файл с правами 0600 (только владелец)."""
    try:
        _atomic_write(TELEGRAM_FILE,
                      ("ON" if enabled else "OFF") + "\n" + token.strip()
                      + "\n" + chat_id.strip(),
                      mode=0o600)
        return True
    except OSError as e:
        print(f"[i] Настройки Telegram не сохранены ({e})")
        return False

def _tg_state_path():
    """Персистентный state бота: файл рядом с telegram.txt. Нужен, потому
    что CLI и бот-демон могут быть разными процессами — каждый со своей
    памятью: CLI шлёт транскрипт и пишет state в свой процесс, демон при
    нажатии кнопки не видит его. Файл — общий мост между процессами."""
    return os.path.join(os.path.dirname(TELEGRAM_FILE), "tg_state.json")

def _tg_state_save(chat_id, text):
    """Записать контекст бота (chat_id → текст) в память И файл."""
    _TG_STATE[chat_id] = {"text": text}
    try:
        data = {str(k): v for k, v in _TG_STATE.items()}
        _atomic_write(_tg_state_path(), json.dumps(data, ensure_ascii=False))
    except Exception:
        pass

def _tg_state_load(chat_id):
    """Контекст для chat_id: из памяти, иначе из файла (другой процесс)."""
    if chat_id in _TG_STATE:
        return _TG_STATE[chat_id]
    try:
        with open(_tg_state_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data.get(str(chat_id)) or {}
    except Exception:
        return {}

def _tg_keyboard():
    # inline_keyboard — массив рядов (официальный InlineKeyboardMarkup):
    # кнопки одного ряда делят ширину; 5 кнопок в ряд на телефоне нечитаемы.
    return {"inline_keyboard": _TG_ACTIONS}

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
