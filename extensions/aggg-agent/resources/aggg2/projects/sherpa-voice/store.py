#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""store — хранилища sherpa-voice: история записей, подмешка, сессии,
словарь терминов. Слой 2: зависит только от ui_utils (вынесено из
монолита transcribe.py).

Слои: ui_utils → store → publish → chat (transcribe.py — facade).
"""
import os
import threading
import time

import ui_utils
from ui_utils import _atomic_write

# Стартовый набор словаря терминов (как говоришь → как писать). Паттерн
# custom spelling из индустрии (Gladia/WhisperTyping): список фокусный,
# не раздувать — пополняется пользователем через /vocab.
_DEFAULT_VOCAB = [
    ("опен код", "OpenCode"),
    ("клоуд код", "Claude Code"),
    ("клауд код", "Claude Code"),
    ("клод", "Claude"),
    ("дипсик", "DeepSeek"),
    ("дип сик", "DeepSeek"),
    ("си эл ай", "CLI"),
    ("ай ди и", "IDE"),
    ("десктоп", "Desktop"),
    ("харнес", "harness"),
    ("агентс", "AGENTS"),
    ("агентс эмди", "AGENTS.md"),
    ("сайкл", "CYCLE"),
    ("чейнджлог", "CHANGELOG"),
    ("транскрайб", "transcribe"),
    ("камфифокс", "Camoufox"),
    ("камуффокс", "Camoufox"),
    ("клине", "Cline"),
    ("шерпа войс", "sherpa-voice"),
    ("ди би тулс", "DB-Tools"),
    ("агент эл эс пи", "agent-lsp"),
]


def _tag_last_entry(ts, text):
    """Фоновая тегировка последней записи: DeepSeek даёт 2-3 тега, они
    дописываются в конец строки истории (#тег1 #тег2). Не блокирует запись
    (поток-демон); если запись уже тегирована — пропуск БЕЗ запроса к API.
    Ошибки молча пропускаются: теги — украшение, не критичный путь."""
    import deepseek_ai
    if not (deepseek_ai.auto_tags_enabled() and deepseek_ai.enabled()):
        return
    try:
        marker = f"- `{ts}`"
        if not os.path.isfile(ui_utils.HISTORY_FILE):
            return
        # Файл истории маленький — вставка целиком в памяти. Байтовые seek
        # в text-режиме ломались на Windows: CRLF + многобайтовый UTF-8
        # сдвигали запись на 2 байта и молча затирали последнюю букву.
        with open(ui_utils.HISTORY_FILE, encoding="utf-8",
                  errors="replace") as f:
            content = f.read()
        idx = content.rfind(marker)
        if idx == -1:
            return
        line_start = content.rfind("\n", 0, idx) + 1
        line_end = content.find("\n", idx)
        if line_end == -1:
            line_end = len(content)
        line = content[line_start:line_end]
        if "#" in line:
            return  # уже тегирована
    except Exception:
        return
    out, err = deepseek_ai.ask(deepseek_ai.PROMPTS["tags"], text,
                               temperature=0.0)
    if err or not out:
        return
    tags = [t.strip().lstrip("#").lower() for t in out.split(",")]
    tags = ["#" + t for t in tags if t and " " not in t][:3]
    if not tags:
        return
    try:
        with open(ui_utils.HISTORY_FILE, encoding="utf-8",
                  errors="replace") as f:
            content = f.read()
        idx = content.rfind(marker)
        if idx == -1:
            return
        line_end = content.find("\n", idx)
        if line_end == -1:
            line_end = len(content)
        tag_str = " " + " ".join(tags)
        _atomic_write(ui_utils.HISTORY_FILE,
                      content[:line_end] + tag_str + content[line_end:])
    except Exception:
        return


def _append_history(text):
    """История транскриптов в markdown: записи под заголовком дня.

    Без ограничения по размеру (сознательное решение — история копится
    и остаётся доступной целиком; искать по ней можно поиском или через
    нашу базу). После записи теги запускаются фоном (DeepSeek), чтобы
    не тормозить цикл записи."""
    try:
        os.makedirs(os.path.dirname(ui_utils.HISTORY_FILE), exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        day = ts[:10]
        with open(ui_utils.HISTORY_FILE, "a+", encoding="utf-8",
                  errors="replace") as f:
            # хвост файла: заголовок дня пишем, только если день сменился
            f.seek(0, 2)
            size = f.tell()
            need_header = size == 0
            if size > 0:
                f.seek(max(0, size - 300))
                tail = f.read()
                need_header = f"## {day}" not in tail
            if need_header:
                f.write(f"## {day}\n")
            f.write(f"- `{ts}` {text}\n")
        threading.Thread(target=_tag_last_entry, args=(ts, text),
                         daemon=True).start()
    except OSError as e:
        print(f"[i] История не записана ({e})")


def _history_remove_last():
    """Удаляет последнюю запись за сегодня из history.md. True — если удалена."""
    today = time.strftime("%Y-%m-%d")
    if not os.path.isfile(ui_utils.HISTORY_FILE):
        return False
    with open(ui_utils.HISTORY_FILE, encoding="utf-8") as f:
        lines = f.readlines()
    removed = False
    out = []
    in_day = False
    for line in lines:
        if line.startswith("## "):
            in_day = line[3:].strip() == today
            out.append(line)
        elif in_day and line.startswith("- `") and not removed:
            removed = True  # пропускаем первую запись дня (последнюю добавленную)
        else:
            out.append(line)
    if removed:
        with open(ui_utils.HISTORY_FILE, "w", encoding="utf-8") as f:
            f.writelines(out)
    return removed


def load_mix():
    """Подмешка: возвращает (включена?, текст). Первая строка файла — ON/OFF,
    остальное — сам текст (файл позволяет многострочность)."""
    try:
        with open(ui_utils.MIX_FILE, encoding="utf-8") as f:
            lines = f.read().split("\n", 1)
        enabled = lines[0].strip().upper() == "ON"
        text = lines[1].rstrip("\n") if len(lines) > 1 else ""
    except (OSError, ValueError):
        return False, ""
    return enabled, text


def save_mix(enabled, text):
    """Сохраняет подмешку. Ошибка не роняет поток."""
    try:
        _atomic_write(ui_utils.MIX_FILE, ("ON" if enabled else "OFF") + "\n" + text.rstrip("\n"))
        return True
    except OSError as e:
        print(f"[i] Подмешка не сохранена ({e})")
        return False


def append_mix(text):
    """Подмешка — постоянный «хвостик», включённый в меню действий.

    Подмешка НЕ вшивается в текст: основной текст остаётся чистым (буфер,
    история, экспорт — без служебного хвостика), а подмешка уходит
    отдельным сообщением в Telegram и печатается отдельно в консоли.
    Возвращает (текст, добавилась ли подмешка, сама подмешка)."""
    enabled, mix = load_mix()
    if enabled and mix.strip():
        return text, True, mix
    return text, False, None


_SESSION = None


def get_session(new=False, session_id=None):
    """Сессия диалога дня (как в харнессах): автоподхват сегодняшней или
    новая; --session <id> — подключиться к существующей."""
    global _SESSION
    if _SESSION is None or new:
        from session import Session
        if session_id:
            _SESSION = Session.load(session_id) or Session(session_id)
        else:
            _SESSION = Session.load_latest() or Session()
            if _SESSION and _SESSION.messages:
                print(f"[~] Продолжаю сессию {_SESSION.session_id} "
                      f"({_SESSION.created})")
    return _SESSION


def _session_context(tail_count=None):
    """Контекст сессии для запроса; при любой ошибке — None (без сессии)."""
    try:
        return get_session().build_context(tail_count=tail_count)
    except Exception:
        return None


def _session_status_line():
    """Строка статуса сессии (как OpenCode TUI): модель · токены · $.
    Выводится блоком с разделителями — результат всегда отделён от
    служебного вывода (паттерн OpenCode: статус снизу, блоки сверху)."""
    try:
        import deepseek_ai
        sess = get_session()
        from termui import rule, status
        line = status(deepseek_ai.model_display_name(),
                      deepseek_ai.PROVIDER, sess.context_str())
        return f"{rule('Сессия')}\n{line}\n{rule()}"
    except Exception:
        return ""


def _session_add_and_compact(user_text, result_text, usage=None):
    """Пишет диктовку+результат в сессию; при переполнении — автокомпакт."""
    try:
        import deepseek_ai
        sess = get_session()
        sess.add("user", user_text)
        sess.add("assistant", result_text, kind="polish")
        sess.record_usage(usage)
        line = _session_status_line()
        if line:
            print(line)
        if sess.needs_compact():
            print("[~] Сессия: автокомпакт (сжимаю старые ходы)…")
            sess.compact(deepseek_ai.ask)
    except Exception:
        pass


def _vocab_load():
    """Словарь терминов «как говоришь → как писать» из vocab.txt.
    Создаётся со стартовым набором при первом чтении, если файла нет."""
    if not os.path.isfile(ui_utils.VOCAB_FILE):
        _vocab_save(_DEFAULT_VOCAB)
    pairs = []
    try:
        with open(ui_utils.VOCAB_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                sep = "→" if "→" in line else ("->" if "->" in line else None)
                if not sep:
                    continue
                k, v = line.split(sep, 1)
                k, v = k.strip().lower(), v.strip()
                if k and v:
                    pairs.append((k, v))
    except OSError:
        return []
    return pairs


def _vocab_save(pairs):
    try:
        os.makedirs(os.path.dirname(ui_utils.VOCAB_FILE), exist_ok=True)
        with open(ui_utils.VOCAB_FILE, "w", encoding="utf-8") as f:
            f.write("# Словарь терминов: «как говоришь → как писать»\n")
            f.write("# Управление: команда /vocab (или правьте файл руками)\n")
            for k, v in pairs:
                f.write(f"{k} → {v}\n")
    except OSError:
        pass


def _vocab_text():
    """Словарь одной строкой для вставки в запрос полировке."""
    pairs = _vocab_load()
    if not pairs:
        return ""
    return "; ".join(f"{k} → {v}" for k, v in pairs)


def _day_stats():
    """Записи за сегодня из history.md: (число, последняя запись)."""
    today = time.strftime("%Y-%m-%d")
    entries = []
    if os.path.isfile(ui_utils.HISTORY_FILE):
        in_day = False
        with open(ui_utils.HISTORY_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if line.startswith("## "):
                    in_day = line[3:].strip() == today
                elif in_day and line.startswith("- `"):
                    _, _, text = line.lstrip("- `").partition("`")
                    entries.append(text.strip())
    last = entries[-1] if entries else None
    return len(entries), last

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
