#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""telegram — Telegram-слой sherpa-voice (пакет; вынесен из
telegram.py механически 15.08.2026, гейт god-файлов). Barrel сохраняет
контракт: импортёры и тесты не тронуты; патчи (telegram.X) работают
через форвардеры в подмодулях.
"""
__all__ = [
    "_ipv4_getaddrinfo", "_ipv4_getaddrinfo_ctx", "_tg_chat_action",
    "_tg_download", "_tg_do_export", "_tg_file_kind", "_tg_file_ts",
    "_tg_get_chat_id", "_tg_get_updates", "_tg_handle_callback",
    "_tg_handle_text_command", "_tg_handle_update", "_tg_keyboard",
    "_tg_listen_loop", "_tg_md_to_html", "_tg_request", "_tg_send_docs",
    "_tg_send_result", "_tg_set_reaction", "_tg_skip_reason",
    "_tg_state_load", "_tg_state_path", "_tg_state_save", "_tg_voice_to_wav",
    "_telegram_menu", "load_telegram", "save_telegram", "tg_send_document",
    "tg_send_rich_text", "tg_send_text", "tg_send_text_file",
]

# Зеркало модульного состояния (тесты/импортёры могут читать)
from .api import (
                  _ORIG_GETADDRINFO,  # noqa: F401
                  _ipv4_getaddrinfo,
                  _ipv4_getaddrinfo_ctx,
                  _tg_chat_action,
                  _tg_download,
                  _tg_get_chat_id,
                  _tg_get_updates,
                  _tg_request,
                  _tg_set_reaction,
                  _tg_skip_reason,
                  _tg_voice_to_wav,
)
from .daemon import _tg_handle_update, _tg_listen_loop
from .menu import (  # noqa: F401
                  _TG_BUSY,
                  _TG_DEBOUNCE_SEC,
                  _TG_LAST,
                  _telegram_menu,
                  _tg_do_export,
                  _tg_send_docs,
)
from .menu import _impl_tg_handle_callback as _tg_handle_callback
from .menu import _impl_tg_handle_text_command as _tg_handle_text_command
from .send import (
                  _PREFIX_BOLD,  # noqa: F401
                  _tg_file_kind,
                  _tg_file_ts,
                  _tg_md_to_html,
                  tg_send_document,
)
from .send import _impl_tg_send_result as _tg_send_result
from .send import _impl_tg_send_rich_text as tg_send_rich_text
from .send import _impl_tg_send_text as tg_send_text
from .send import _impl_tg_send_text_file as tg_send_text_file
from .state import (  # noqa: F401
                  _TG_ACTIONS,
                  _TG_STATE,
                  _tg_keyboard,
                  _tg_state_load,
                  _tg_state_path,
                  _tg_state_save,
                  load_telegram,
                  save_telegram,
)

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
