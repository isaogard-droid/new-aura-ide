#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Микрофон → текст (локально, без облака) на sherpa-onnx.

Лёгкий транскрайбер для слабых машин: русская модель zipformer int8 (~74MB),
память ~300MB, старт <1с, VAD встроен. Режим «push-to-talk»: Enter — начать
запись, Enter — остановить.

Установка:
    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    # модель скачается автоматически при первом запуске (~74MB)

Запуск:
    python transcribe.py                      # микрофон, русский
    python transcribe.py --streaming          # стриминговая small (29MB)
    python transcribe.py --file audio.wav     # распознать файл (для тестов)

Архитектура (разбиение монолита, см. CHANGELOG):
    ui_utils → store → publish → chat, transcribe.py — facade (main + re-export).
    Внешние импорты (telegram.py, audio.py, hotwords.py, тесты) работают
    как раньше — все имена доступны из transcribe.
"""
import argparse
import os
import signal
import threading

import soxr

from chat import (  # noqa: F401
    COMMANDS,
    HELP_TEXT,
    SLASH,
    _ask_no_echo,
    _day_summary,
    _help_text,
    _history_search,
    _is_echo,
    _mix_menu,
    _polish_examples,
    _polish_request,
    _polish_text,
    _prompt_from_text,
    _publish_transcript,
    _sanitize_polish,
    _tag_menu,
    _vocab_menu,
    deepseek_menu,
)
from publish import publish_result  # noqa: F401
from store import (  # noqa: F401
    _DEFAULT_VOCAB,
    _append_history,
    _day_stats,
    _history_remove_last,
    _session_add_and_compact,
    _session_context,
    _session_status_line,
    _tag_last_entry,
    _vocab_load,
    _vocab_save,
    _vocab_text,
    append_mix,
    get_session,
    load_mix,
    save_mix,
)

# --- Facade: re-export из модулей (compatibility facade, см. agent-refactor-safety) ---
from ui_utils import (  # noqa: F401
    HAS_CLIPBOARD,
    HISTORY_FILE,
    LAST_TEXT_FILE,
    LOCK_FILE,
    MIX_FILE,
    REC_MARKER,
    SHERPA_CONFIG_DIR,
    STOP_FLAG,
    TELEGRAM_FILE,
    VOCAB_FILE,
    _atomic_write,
    _cleanup_markers,
    _kill_previous,
    _migrate_history,
    _migrate_settings,
    _settings_dir,
    _sigterm_cleanup,
    acquire_single_instance,
    c_blue,
    c_err,
    c_err_lbl,
    c_info,
    c_ok,
    c_ok_lbl,
    c_warn,
    c_warn_lbl,
    copy_to_clipboard,
    notify,
)


def parse_args():
    p = argparse.ArgumentParser(description="Микрофон → текст (sherpa-onnx, локально, лёгкий)")
    p.add_argument("--streaming", action="store_true",
                   help="стриминговая small-модель (29MB) (алиас --model streaming)")
    p.add_argument("--model", choices=["offline", "streaming", "gigaam"],
                   default="gigaam",
                   help="модель: gigaam (230MB transducer, лучшее качество "
                        "+ hotwords, по умолчанию) | offline (74MB) | "
                        "streaming (29MB, онлайн)")
    p.add_argument("--device", default="auto",
                   help="устройство захвата (auto | имя/индекс)")
    p.add_argument("--list-devices", action="store_true",
                   help="показать доступные аудиоустройства и выйти (без загрузки моделей)")
    p.add_argument("--file", default=None,
                   help="распознать WAV-файл вместо записи с микрофона")
    p.add_argument("--threads", type=int, default=2,
                   help="число потоков для sherpa-onnx")
    p.add_argument("--once", action="store_true",
                   help="одна запись и выход (без меню) — для внешних хоткеев")
    p.add_argument("--silence", type=float, default=0.0,
                   help="секунды тишины до автостопа в фоновом режиме (0 — выкл, по умолчанию)")
    p.add_argument("--session", default=None,
                   help="подключиться к существующей сессии по id")
    p.add_argument("--new-session", action="store_true",
                   help="начать новую сессию (не подхватывать последнюю)")
    p.add_argument("--list-sessions", action="store_true",
                   help="список сохранённых сессий и выход")
    p.add_argument("--auto-export", action="store_true",
                   help="каждая запись сразу сохраняется в MD (и PDF, если есть шрифт)")
    p.add_argument("--day-summary", action="store_true",
                   help="собрать итог дня из истории и выйти (для хоткея/крона)")
    p.add_argument("--telegram-daemon", action="store_true",
                   help="слушать голосовые из Telegram (без микрофона и меню)")
    return p.parse_args()


def _setup_command_completion():
    """Tab-автодополнение slash-команд в меню (как OpenCode: ввод / + Tab)."""
    try:
        import readline
        cmds = sorted(COMMANDS) + ["/help"]
        readline.set_completer(
            lambda text, state: (
                [c for c in cmds if c.startswith(text)] + [None])[state])
        readline.parse_and_bind("tab: complete")
    except Exception:
        pass


def main():
    # telegram/audio импортируются локально: они -> transcribe (цикл на
    # верхнем уровне невозможен, transcribe уже полностью загружен).
    from audio import (
        MODEL_RATE,
        RECORD_RATE,
        find_input_device,
        load_model,
        read_wav,
        record_until_enter,
        transcribe_offline,
        transcribe_streaming,
    )
    from telegram import (
        _tg_listen_loop,
        load_telegram,
    )
    signal.signal(signal.SIGTERM, _sigterm_cleanup)
    args = parse_args()
    if args.list_devices:
        import sounddevice as sd
        try:
            devs = sd.query_devices()
            for i, d in enumerate(devs):
                if d["max_input_channels"] > 0 and d["max_output_channels"] > 0:
                    kind = "in+out"
                elif d["max_input_channels"] > 0:
                    kind = "in"
                elif d["max_output_channels"] > 0:
                    kind = "out"
                else:
                    kind = "-"
                print(f"[{i}] {kind:5s} {d['name']}")
            print(f"\nauto выбирает: {find_input_device('auto') or 'default (PortAudio)'}")
            print("Закрепить микрофон: transcribe.py --device \"<имя из списка>\"")
        except Exception as e:
            print(f"[✗] Не удалось получить список устройств: {e}")
        return
    _migrate_settings()
    _migrate_history()
    # Онбординг первого запуска (паттерн OpenClaw: детект → спросить →
    # Skip → режим без ИИ). В неинтерактивных режимах не спрашиваем.
    try:
        import deepseek_ai as _dai
        import firstrun
        if args.once or args.file or args.telegram_daemon or args.day_summary:
            pass  # скриптовый режим — без вопросов
        else:
            status = firstrun.onboard(_dai.load_key)
            if status == "skip":
                print(c_warn("[i] DeepSeek пропущен — режим без ИИ (только "
                             "запись); включить позже: /ai"))
            elif _dai.enabled():
                print(c_ok("[✓] DeepSeek активен — улучшение и действия вкл."))
            else:
                # ключ есть, но ИИ выключен флагом /ai — честно говорим
                # активное состояние (паттерн Hermes #7385: UI показывает
                # runtime, а не конфиг)
                print(c_warn("[i] DeepSeek выключен (/ai) — режим без ИИ "
                             "(только запись); включить: /ai"))
    except Exception:
        pass
    if SHERPA_CONFIG_DIR == os.path.expanduser("~/.cache/sherpa-voice"):
        print("[i] ~/.config недоступен для записи — настройки хранятся "
              "в ~/.cache/sherpa-voice")
    # Второе нажатие хоткея (--once): запись уже идёт → ставим стоп-флаг
    # и выходим БЕЗ загрузки модели (быстрая реакция на клавишу).
    if args.once and os.path.exists(REC_MARKER):
        os.makedirs(os.path.dirname(STOP_FLAG), exist_ok=True)
        with open(STOP_FLAG, "w") as f:
            f.write("1")
        notify("Sherpa Voice", "Запись остановлена.")
        print("[⏹] Стоп-сигнал отправлен.")
        return
    # --once не ставит lock: короткоживущий (одна запись и выход), а микрофон
    # основной процесс держит только во время записи. Если оба записывают
    # одновременно — сработают ретраи open_microphone и понятная ошибка.
    if not args.once:
        acquire_single_instance()
    model = "streaming" if args.streaming else args.model
    size = {"offline": 74, "streaming": 29, "gigaam": 230}[model]
    # словарь терминов («как говоришь») → hotwords для ASR
    try:
        import hotwords
        hotwords.sync_from_vocab()
    except Exception:
        pass
    print(f"[~] Загрузка модели ({model}, ~{size}MB)…")
    recognizer, is_streaming = load_model(model, args.threads)
    print(c_ok("[✓] Готово."))
    _setup_command_completion()
    if args.list_sessions:
        from session import Session
        for sid, created, count, _summary, title in Session.list_sessions(20):
            print(f"{title or sid}  ({sid}, {created})  {count} сообщ.")
        return
    sess = get_session(new=args.new_session, session_id=args.session)
    # контекст-подкормка: термины из сессии → hotwords (влияют на ASR)
    try:
        import hotwords
        hotwords.from_session(sess)
    except Exception:
        pass
    n_today, last_today = _day_stats()
    print(c_info(f"[~] Записей за сегодня: {n_today}")
          + (f" · последняя: {last_today[:60]}…" if last_today else ""))
    sess_name = sess.title or sess.session_id
    print(c_info(f"[~] Сессия «{sess_name}» ({sess.session_id}): {sess.context_str()}")
          + (f" · сводка: {sess.summary[:80]}…" if sess.summary else ""))

    if args.day_summary:
        # итог дня — без микрофона и меню; модель уже загружена, но
        # саммари её не использует. Делаем и выходим.
        summary = _day_summary()
        if summary:
            publish_result(summary, "📅 Итог дня", to_tg=True)
        return

    if args.telegram_daemon:
        enabled, token, chat_id = load_telegram()
        if not (enabled and token and chat_id):
            print("[i] Telegram не настроен или выключен — включите через меню [6].")
            return
        print("[~] Telegram-демон: слушаю голосовые… (Ctrl+C — выход)")
        _tg_listen_loop(recognizer, is_streaming, copy_to_buf=False,
                        notify_new=True)
        return

    if args.file:
        audio = read_wav(args.file)
        print(f"[~] Распознаю {args.file} ({len(audio) / MODEL_RATE:.1f}с)…")
        text = (transcribe_streaming if is_streaming else transcribe_offline)(recognizer, audio)
        from termui import fmt_result
        print(fmt_result("🎤 Транскрипт", text))
        return

    import deepseek_ai
    device = find_input_device(deepseek_ai.env_config("MIC_DEVICE") or args.device)
    print(f"[✓] Вход: {device or 'default'}. Пустой Enter — запись, текст — "
          "как запись (полировка → ТГ), Enter — остановить запись. "
          "(Ctrl+C — выход)\n")

    # Голосовые из Telegram обрабатываются в фоне, пока программа открыта.
    # Говорим честно, слушаем ли мы: раньше поток стартовал молча, и было
    # непонятно, почему «голосовые не переводятся».
    if not args.once:
        enabled_tg, token_tg, chat_id_tg = load_telegram()
        if enabled_tg and token_tg and chat_id_tg:
            print("[~] Telegram: слушаю голосовые — пришлите голосовое боту, "
                  "верну транскрипцию в этот же чат.")
        else:
            print("[i] Telegram не настроен или выключен — голосовые боту не "
                  "обрабатываются (настройка: меню [6] в Действиях).")
        threading.Thread(target=_tg_listen_loop,
                         args=(recognizer, is_streaming), daemon=True).start()

    while True:
        if args.once:
            # Фоновая запись без окна: запуск процесса — старт, повторный
            # запуск — стоп (новый процесс ставит STOP_FLAG и выходит).
            os.makedirs(os.path.dirname(REC_MARKER), exist_ok=True)
            with open(REC_MARKER, "w") as f:
                f.write(str(os.getpid()))
            notify("Sherpa Voice", "Запись началась — запустите ещё раз для стопа.")
            print("\n[⏺] Фоновая запись (повторный запуск = стоп)…")
            try:
                audio = record_until_enter(device=device, background=True,
                                           silence_stop=args.silence)
            finally:
                _cleanup_markers()
            if audio is None:
                break
            if audio.size == 0:
                print("[i] Пустая запись — не распознаю.")
                notify("Sherpa Voice", "Не услышал звука.")
                break
        else:
            try:
                first = input(
                    "\n[⏺] Enter — запись · текст — как запись · "
                    "Ctrl+C — выход\n> ")
            except (EOFError, KeyboardInterrupt):
                print("Выход.")
                break
            if first.strip():
                first_s = first.strip()
                # Команды (цифры меню, /-команды) обрабатываются СРАЗУ по
                # первой строке, без сбора «…>»: иначе ввод «/help» + Enter
                # уходил в сбор продолжения, и команда становилась промптом
                # модели (проверено вживую).
                if first_s in ("0", "1", "2", "3", "4", "5", "6",
                               "7", "8", "9", "s", "S"):
                    print(c_warn("[i] Это команда меню — она доступна после "
                                 "записи (меню внизу). Промпт не отправлен."))
                    continue
                if first_s.lower().startswith("/"):
                    cmd = SLASH.get(first_s.lower(), "h")
                    if cmd == "h":
                        print(HELP_TEXT)
                    elif cmd == "t":
                        _prompt_from_text()
                    else:
                        print(c_warn("[i] Эта команда доступна в меню после "
                                     "записи."))
                    continue
                # Многострочный промпт вставкой (как OpenCode/Copilot CLI):
                # после первой строки продолжаем «…>», пустая строка или
                # Ctrl+D — конец. Раньше input() брал только первую строку
                # пасты, а остаток уходил отдельными промптами/записями.
                lines = [first]
                try:
                    while True:
                        more = input("  …> ")
                        if not more.strip():
                            break
                        lines.append(more)
                except (EOFError, KeyboardInterrupt):
                    pass
                entry = "\n".join(lines).strip()
                if not entry:
                    continue
                # Текстовый ввод = как голосовой (единый путь публикации):
                # полировка → подмешка → транскрипт в ТГ с кнопками.
                # Раньше текст уходил в чат-режим _chat_send и в ТГ слался
                # ответ ИИ вместо полировки (см. CHANGELOG).
                entry = _publish_transcript(entry, auto_export=args.auto_export)
                deepseek_menu(entry, kind="text")
                continue
            audio = record_until_enter(device=device)
            if audio is None:
                break
            if audio.size == 0:
                print("[i] Пустая запись — говорите и нажмите Enter.")
                continue

        print(f"[~] Распознаю ({len(audio) / RECORD_RATE:.1f}с)…")
        try:
            # микрофон пишет в родных 48кГц — приводим к 16кГц один раз
            # здесь; read_wav (голосовые из TG, --file) уже отдаёт 16кГц
            audio16 = soxr.resample(audio, RECORD_RATE, MODEL_RATE)
            text = (transcribe_streaming if is_streaming else transcribe_offline)(
                recognizer, audio16)
            from termui import fmt_result
            print(fmt_result("🎤 Транскрипт", text))
            if text.strip():
                # Единый путь публикации (общий с текстовым вводом):
                # полировка → подмешка → транскрипт в ТГ с кнопками →
                # автоэкспорт. Меню действий вызывается после — как раньше.
                text = _publish_transcript(text, notify_once=args.once,
                                           auto_export=args.auto_export)
                if not args.once:
                    deepseek_menu(text)
        except Exception as e:
            print(f"[✗] Ошибка: {e}")
        if args.once:
            # Одна запись = один заход: выходим даже при пустом распознавании
            # или ошибке (иначе цикл запишет второй раз — был такой баг).
            break


if __name__ == "__main__":
    main()

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
