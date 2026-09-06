#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""chat.menus — меню действий диалога (сборка меню, экспорт, сессии,
реконфиг, ai-toggle, deepseek_menu — оркестратор).
Вынесено из chat.py механически (verbatim), 15.08.2026 — гейт god-файлов."""
import os

from publish import publish_result
from store import _history_remove_last, get_session, load_mix
from ui_utils import c_info, c_ok, c_warn

from .actions import (
    _action_answer,
    _action_prompt_review,
    _action_summary,
    _action_tasks,
)
from .commands import HELP_TEXT, SLASH
from .history import _day_summary, _history_search, _tag_menu
from .mix import _mix_menu
from .polish import _prompt_from_text
from .vocab import _vocab_menu


def _build_menu(mix_status, no_ai):
    """Панели меню «Действия» — чистый список строк (без ввода)."""
    from termui import panel, rule
    menu = []
    menu.append(rule("Действия"))
    if no_ai:
        menu.append(panel("Режим без ИИ (только запись)",
                          "DeepSeek выключен: без полировки, тегов, "
                          "сводки дня и анализа. Включить: /ai или "
                          "меню Telegram [6].", dim=True))
    else:
        menu.append(panel("Анализ записи",
                          "[0] Задачи   [1] Саммари   [2] Ответить  "
                          "[4] Кодинг-промт", dim=True))
    menu.append(panel("Публикация",
                      f"[3] Экспорт   [6] Telegram   [5] Подмешка({mix_status})",
                      dim=True))
    if no_ai:
        menu.append(panel("Дневник",
                          "[7] История   [s] Сессия   "
                          "(сводка дня и теги — выкл. вместе с ИИ)",
                          dim=True))
    else:
        menu.append(panel("Дневник",
                          "[7] История   [8] Сводка дня   [9] Теги",
                          dim=True))
    menu.append(panel("Сессии",
                      "[s] Сессия    [Enter] продолжить   "
                      "(команды: /tasks /day … — /help)", dim=True))
    menu.append(rule())
    return menu


def _no_ai_state():
    """Режим без ИИ? (DeepSeek выключен или онбординг пропущен)."""
    import deepseek_ai as _dai
    import firstrun
    return not _dai.enabled() or firstrun._load_cfg().get("deepseek_skip") == "1"


def _menu_export(text, summary=None, answer=None, review=None):
    """[3] Экспорт транскрипта + результатов в MD/PDF и Telegram."""

    from export import save_text_export
    from telegram import tg_send_document
    parts = ["транскрипт"]
    if summary:
        parts.append("саммари")
    if answer:
        parts.append("ответ")
    if review:
        parts.append("кодинг-промт")
    print(f"[~] Экспортирую ({', '.join(parts)})…")
    md_path, pdf_path, err = save_text_export(
        text, summary=summary, answer=answer, review=review)
    if err:
        print(f"[i] {err}")
    print(f"[✓] MD: {md_path}")
    if pdf_path:
        print(f"[✓] PDF: {pdf_path}")
    for p in (md_path, pdf_path):
        if p:
            ok_tg, err_tg = tg_send_document(p)
            if ok_tg:
                print(f"[✓] {os.path.basename(p)} отправлен в Telegram")
            elif err_tg:
                print(f"[✗] {err_tg}")


def _menu_sessions():
    """[s] Сессии: список / подключиться / новая / компакт."""
    from session import Session
    sess = get_session()
    print(f"  Текущая: «{sess.title or '—'}» ({sess.session_id}, "
          f"{sess.created})")
    print(f"  Контекст: {sess.context_str()}")
    if sess.summary:
        print(f"  Сводка: {sess.summary[:200]}")
    print("  Сессии (последние):")
    for i, (sid, created, count, _summary, title) in enumerate(
            Session.list_sessions(10), 1):
        mark = " <-- сейчас" if sid == sess.session_id else ""
        name = title or sid
        print(f"   [{i}] «{name}» ({created}) · {count} сообщ.{mark}")
    sub = input("  [номер] подключиться · [n] новая · [c] компакт "
                "сейчас · Enter — назад: ").strip().lower()
    if sub == "n":
        get_session(new=True)
        print("  [✓] Новая сессия создана")
    elif sub == "c":
        import deepseek_ai
        if sess.compact(deepseek_ai.ask):
            print("  [✓] Компакт выполнен")
        else:
            print("  [i] Компакт не удался (или история пуста)")
    elif sub.isdigit():
        lst = Session.list_sessions(10)
        idx = int(sub) - 1
        if 0 <= idx < len(lst):
            get_session(session_id=lst[idx][0])
            print(f"  [✓] Подключена сессия {lst[idx][0]}")
        else:
            print("  [i] Нет такой сессии")


def _menu_reconfigure():
    """[e] Заново пройти онбординг DeepSeek (ключ / пропустить)."""
    import deepseek_ai as _dai
    import firstrun
    print(c_info("[~] Настройка DeepSeek заново (онбординг)…"))
    has = bool(_dai.load_key())
    if has:
        try:
            ans = input("    Ключ уже есть. [1] Сменить  [2] Убрать  "
                        "[Enter] назад: ").strip()
        except (EOFError, KeyboardInterrupt):
            ans = ""
        if ans == "1":
            # force=True: спросить новый ключ даже при существующем
            status = firstrun.onboard(_dai.load_key, force=True)
            if status == "ok":
                print(c_ok("[✓] Ключ заменён."))
        elif ans == "2":
            cfg = firstrun._load_cfg()
            cfg.pop("deepseek_key", None)
            firstrun._save_cfg(cfg)
            print(c_info("[i] Ключ убран — режим без ИИ (только запись)."))
        return
    # ключа нет — просто запускаем онбординг (спросит заново)
    firstrun.unskip()
    status = firstrun.onboard(_dai.load_key)
    if status == "ok":
        if _dai.enabled():
            print(c_ok("[✓] DeepSeek настроен и активен — улучшение и "
                       "действия вкл."))
        else:
            print(c_warn("[i] Ключ настроен, но ИИ выключен (/ai) — "
                         "режим без ИИ; включить: /ai"))
    elif status == "skip":
        print(c_warn("[i] Пропущено — режим без ИИ (только запись)."))


def _menu_ai_toggle():
    """[a] Глобальный выключатель DeepSeek (паттерн Zed disable_ai,
    OpenCode offline mode) — выкл = без ИИ (только запись)."""
    import deepseek_ai as _dai
    import firstrun
    cfg = firstrun._load_cfg()
    off = _dai._env_or_file("DEEPSEEK_OFF", "0").lower() in (
        "1", "true", "yes", "on") or cfg.get("deepseek_off") == "1"
    if off:
        try:
            ans = input("    DeepSeek выключен. [1] Включить  "
                        "[Enter] назад: ").strip()
        except (EOFError, KeyboardInterrupt):
            ans = ""
        if ans == "1":
            cfg.pop("deepseek_off", None)
            firstrun._save_cfg(cfg)
            if _dai.load_key():
                print(c_ok("[✓] DeepSeek включён — улучшение и действия работают."))
            else:
                print(c_warn("[i] Включено, но ключа нет — запускаю настройку…"))
                firstrun.unskip()
                status = firstrun.onboard(_dai.load_key)
                if status == "ok" and _dai.enabled():
                    print(c_ok("[✓] Ключ введён — DeepSeek активен."))
                else:
                    print(c_warn("[i] Без ключа — режим без ИИ (только запись)."))
    else:
        try:
            ans = input("    DeepSeek включён. [1] Выключить (без ИИ, "
                        "только запись)  [Enter] назад: ").strip()
        except (EOFError, KeyboardInterrupt):
            ans = ""
        if ans == "1":
            cfg["deepseek_off"] = "1"
            firstrun._save_cfg(cfg)
            print(c_warn("[i] DeepSeek выключен — программа работает "
                         "только как запись+распознавание (без полировки, "
                         "тегов и действий меню)."))


def deepseek_menu(text, kind="voice"):
    """Кнопки-действия с текстом: Саммари / Ответить / Экспорт / Кодинг-промт
    / Задачи.

    kind: "voice" — текст пришёл с микрофона (marked «Транскрипт голосовой
    записи»), "text" — текстовый промпт с главного экрана (marked «Текстовый
    промпт»). Меню одно и то же — единый флоу «ввод → результат → действия».

    Консольные «кнопки» — Enter-меню. Саммари, Ответить, Кодинг-промт и
    Задачи работают только с ключом в .env (DEEPSEEK_API_KEY); Экспорт —
    всегда. Ошибки не роняют. Сгенерированные саммари/ответ/кодинг-промт
    запоминаются и попадают в экспорт (MD/PDF) вместе с транскрипцией.
    Кодинг-промт превращает озвученную задачу (улучшенный текст) в ТЗ для
    агента. Задачи вытаскивают из записи только дела (глагол + суть), без
    пересказа — по паттерну action items из индустрии (Otter.ai, Nylas):
    один пункт = одно действие, без выдуманных сроков и исполнителей."""
    import deepseek_ai
    from telegram import _telegram_menu
    summary = None
    answer = None
    review = None
    while True:
        try:
            mix_enabled, _ = load_mix()
            mix_status = "вкл" if mix_enabled else "выкл"
            no_ai = _no_ai_state()
            menu = _build_menu(mix_status, no_ai)
            choice = input("\n".join(menu) + "\n    > ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        # Slash-команды (/day) или цифры/буквы меню; "/" — список команд
        choice_l = choice.lower()
        if choice_l.startswith("/"):
            choice = SLASH.get(choice_l, "h")
        if not choice:
            return
        # Явный маркер данных: без него модель принимает текст записи
        # за обращение к ней и отказывается («не получил текст записи»).
        if kind == "text":
            marked = f"Текстовый промпт: «{text}»"
        else:
            marked = f"Транскрипт голосовой записи: «{text}»"
        if choice in ("0", "1", "2", "4"):
            if _no_ai_state():
                print("[i] DeepSeek не подключен — режим без ИИ (только запись). "
                      "Включить: ввести ключ в .env (DEEPSEEK_API_KEY=sk-...), "
                      "или меню Telegram [6].")
                continue
            handlers = {"0": _action_tasks, "1": _action_summary,
                        "2": _action_answer, "4": _action_prompt_review}
            out, err = handlers[choice](text, marked)
        elif choice == "3":
            _menu_export(text, summary, answer, review)
            continue
        elif choice == "5":
            _mix_menu()
            continue
        elif choice == "6":
            _telegram_menu(text)
            continue
        elif choice == "7":
            _history_search()
            continue
        elif choice == "8":
            if not deepseek_ai.enabled():
                print(c_warn("[i] Сводка дня — это вызов DeepSeek; сейчас ИИ "
                             "выключен (включить: /ai)."))
                continue
            _day_summary()
            continue
        elif choice == "9":
            if not deepseek_ai.enabled():
                print(c_warn("[i] Теги — это вызов DeepSeek; сейчас ИИ "
                             "выключен (включить: /ai)."))
                continue
            _tag_menu()
            continue
        elif choice == "h":
            print(HELP_TEXT)
            continue
        elif choice == "n":
            get_session(new=True)
            print("  [✓] Новая сессия создана")
            continue
        elif choice == "c":
            sess = get_session()
            if sess.compact(deepseek_ai.ask):
                print("  [✓] Компакт выполнен")
            else:
                print("  [i] Компакт не удался (или история пуста)")
            continue
        elif choice == "q":
            print("Выход.")
            return
        elif choice == "u":
            sess = get_session()
            if sess.undo() and _history_remove_last():
                print(c_ok("[✓] Последняя диктовка отменена (сессия + история)"))
            elif sess.undo():
                print(c_warn("[i] Отменена в сессии (в истории не найдена)"))
            else:
                print(c_warn("[i] Отменять нечего"))
            continue
        elif choice == "r":
            print(c_info("[~] Enter — новая запись…"))
            return
        elif choice == "e":
            _menu_reconfigure()
            continue
        elif choice == "a":
            _menu_ai_toggle()
            continue
        elif choice == "t":
            _prompt_from_text()
            continue
        elif choice == "v":
            _vocab_menu()
            continue
        elif choice in ("s", "S"):
            _menu_sessions()
            continue
        else:
            # Чат-режим убран (см. CHANGELOG): текст на главном экране
            # обрабатывается как запись (полировка → транскрипт в ТГ),
            # а в меню действий — только команды. Не команда — подсказка.
            print(c_warn("[i] Это не команда меню. Текст вводится на главном "
                         "экране (вписать текст вместо Enter) и "
                         "обрабатывается как запись — полировка → ТГ."))
            continue
        if err:
            print(f"[✗] {err}")
        else:
            print(f"[ai] {out}")
            if choice == "1":
                summary = out
            elif choice == "2":
                answer = out
            elif choice == "4":
                review = out
            prefix = {"0": "✅ Задачи", "1": "📋 Саммари", "2": "💬 Ответ",
                      "4": "💻 Кодинг-промт"}.get(choice, "💬 Ответ")
            # подмешка (footer) в меню не шлётся — только при транскрипте
            publish_result(out, prefix, to_history=False, to_file=False)


# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
