#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""chat — диалоговый слой sherpa-voice: меню действий, полировка,
эхо-защита, словарь, история-меню, подмешка-меню. Слой 4: зависит от
store, publish, ui_utils. Пакет вынесен из chat.py механически
(verbatim) 15.08.2026 — гейт god-файлов (docs/canon/FILE-SIZE.md): barrel
сохраняет публичный контракт модуля, импортёры не тронуты.

Слои: ui_utils → store → publish → chat (transcribe.py — facade).
"""
# Ниже — модульные имена СТАРОГО chat.py (barrel-зеркало namespace):
# тесты и импортёры патчат/читают их как атрибуты chat.
import difflib  # noqa: F401
import os  # noqa: F401
import shlex  # noqa: F401
import tempfile  # noqa: F401
import time  # noqa: F401

import ui_utils  # noqa: F401
from publish import publish_result  # noqa: F401
from store import (  # noqa: F401
                      _history_remove_last,
                      _session_add_and_compact,
                      _session_context,
                      _session_status_line,
                      _vocab_load,
                      _vocab_save,
                      _vocab_text,
                      append_mix,
                      get_session,
                      load_mix,
                      save_mix,
)
from ui_utils import c_blue, c_info, c_ok, c_warn  # noqa: F401

from .actions import (
                      _action_answer,
                      _action_prompt_review,
                      _action_summary,
                      _action_tasks,
)
from .commands import COMMANDS, HELP_TEXT, SLASH, _help_text
from .history import _day_summary, _history_search, _tag_menu
from .menus import (
                      _build_menu,
                      _menu_ai_toggle,
                      _menu_export,
                      _menu_reconfigure,
                      _menu_sessions,
                      _no_ai_state,
                      deepseek_menu,
)
from .mix import _mix_menu
from .polish import (
                      _ask_no_echo,
                      _is_echo,
                      _polish_examples,
                      _polish_request,
                      _polish_text,
                      _prompt_from_text,
                      _sanitize_polish,
)
from .publish import _publish_transcript
from .vocab import _vocab_menu

__all__ = [
    # функции (контракт chat.py)
    "_action_answer", "_action_prompt_review", "_action_summary",
    "_action_tasks", "_ask_no_echo", "_build_menu", "_day_summary",
    "_help_text", "_history_search", "_is_echo", "_menu_ai_toggle",
    "_menu_export", "_menu_reconfigure", "_menu_sessions", "_mix_menu",
    "_no_ai_state", "_polish_examples", "_polish_request", "_polish_text",
    "_prompt_from_text", "_publish_transcript", "_sanitize_polish",
    "_tag_menu", "_vocab_menu", "deepseek_menu",
    # константы
    "COMMANDS", "HELP_TEXT", "SLASH",
    # модульное зеркало (тесты патчат chat.publish_result и т.п.)
    "publish_result", "ui_utils", "get_session", "load_mix", "save_mix",
    "append_mix", "_history_remove_last", "_session_add_and_compact",
    "_session_context", "_session_status_line", "_vocab_load",
    "_vocab_save", "_vocab_text", "c_blue", "c_info", "c_ok", "c_warn",
    "difflib", "os", "shlex", "tempfile", "time",
]

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
