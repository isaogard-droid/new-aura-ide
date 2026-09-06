#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""chat.history — история записей: поиск, теги, сводка дня.
Вынесено из chat.py механически (verbatim), 15.08.2026 — гейт god-файлов."""
import os
import time

import chat
import ui_utils

from .polish import _ask_no_echo


def publish_result(*args, **kwargs):
    """Форвардер через пакет: функции ниже зовут publish_result по имени,
    а тесты патчат chat.publish_result (механика старого chat.py-модуля).
    Look-up атрибута пакета в момент вызова — патчи видны без правки тел
    функций (verbatim-перенос сохранён)."""
    return chat.publish_result(*args, **kwargs)

def _history_search():
    """Поиск по истории (history.md): подстрока → записи с датами, выбор
    номера копирует запись в буфер (без отправки и без дубля в истории)."""
    if not os.path.isfile(ui_utils.HISTORY_FILE):
        print("[i] История пуста — пока нет записей.")
        return
    try:
        q = input("[ai] 🔍 Искать в истории (подстрока, Enter — отмена):\n    > ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not q:
        return
    hits = []
    day = None
    with open(ui_utils.HISTORY_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("## "):
                day = line[3:]
            elif q.lower() in line.lower():
                rest = line.lstrip().lstrip("-").lstrip()
                ts = ""
                if rest.startswith("`"):
                    ts, _, text = rest[1:].partition("`")
                    text = text.lstrip()
                else:
                    text = rest
                hits.append((day, ts, text))
    if not hits:
        print(f"[i] Ничего не найдено по «{q}».")
        return
    print(f"[ai] Найдено: {len(hits)}")
    for i, (day, ts, text) in enumerate(hits[:20], 1):
        shown = text if len(text) <= 90 else text[:87] + "…"
        print(f"  [{i}] {ts or day}: {shown}")
    if len(hits) > 20:
        print(f"  … ещё {len(hits) - 20} записей")
    try:
        choice = input("[ai] Копировать номер (Enter — ничего): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice.isdigit() and 1 <= int(choice) <= len(hits):
        publish_result(hits[int(choice) - 1][2], to_tg=False,
                       to_history=False)


def _tag_menu():
    """Подменю тегов: топ-тегов из истории → выбор → записи с тегом →
    копирование. Теги ставятся автоматически (DeepSeek) после каждой
    записи."""
    if not os.path.isfile(ui_utils.HISTORY_FILE):
        print("[i] История пуста — тегов пока нет.")
        return
    from collections import Counter
    counts = Counter()
    entries = {}
    day = None
    with open(ui_utils.HISTORY_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("## "):
                day = line[3:]
            elif line.startswith("- `"):
                ts, _, rest = line.lstrip("- `").partition("`")
                text, _, tag_part = rest.lstrip().partition(" #")
                if not tag_part:
                    continue
                tags = ["#" + t for t in tag_part.split("#") if t.strip()]
                for t in tags:
                    counts[t] += 1
                    entries.setdefault(t, []).append((day, ts, text))
    if not counts:
        print("[i] Тегов пока нет — они появляются сами после записи "
              "(нужен ключ DeepSeek).")
        return
    top = counts.most_common(20)
    print("[ai] Теги:")
    for i, (t, n) in enumerate(top, 1):
        print(f"  [{i}] {t} ({n})")
    try:
        choice = input("[ai] Показать записи по тегу (Enter — назад): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(top)):
        return
    tag = top[int(choice) - 1][0]
    hits = entries[tag][-20:]
    print(f"[ai] Записи с тегом {tag}: {len(hits)}")
    for i, (day, ts, text) in enumerate(hits, 1):
        shown = text if len(text) <= 90 else text[:87] + "…"
        print(f"  [{i}] {day} {ts}: {shown}")
    try:
        choice2 = input("[ai] Копировать номер (Enter — ничего): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice2.isdigit() and 1 <= int(choice2) <= len(hits):
        publish_result(hits[int(choice2) - 1][2], to_tg=False,
                       to_history=False)


def _day_summary(day=None):
    """Итог дня: собирает записи за дату из history.md, отдаёт DeepSeek
    (промпт day_summary), печатает результат. day — 'YYYY-MM-DD', по
    умолчанию сегодня. Возвращает итог или None (нет записей/ошибка)."""
    import deepseek_ai
    day = day or time.strftime("%Y-%m-%d")
    entries = []
    if os.path.isfile(ui_utils.HISTORY_FILE):
        in_day = False
        with open(ui_utils.HISTORY_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if line.startswith("## "):
                    in_day = line[3:].strip() == day
                elif in_day and line.startswith("- `"):
                    ts, _, text = line.lstrip("- `").partition("`")
                    entries.append(f"[{ts}] {text.lstrip()}")
    if not entries:
        print(f"[i] За {day} записей нет — итог собирать не из чего.")
        return None
    print(f"[ai] Собираю итог дня: {len(entries)} записей за {day}…")
    if not deepseek_ai.enabled():
        print("[i] DeepSeek не подключен — положите ключ в .env "
              "(DEEPSEEK_API_KEY=sk-...).")
        return None
    body = "\n".join(entries)
    # одноразовая задача с ИЗОЛИРОВАННЫМ контекстом + эхо-защита (как
    # задачи/саммари/кодинг-промт): история сессии заставляет модель
    # «продолжать» последнее сообщение вместо итога дня
    out, err = _ask_no_echo("day_summary", body, temperature=0.3,
                            echo_ref=body)
    if err:
        print(f"[✗] {err}")
        return None
    print(f"[ai] Итог дня {day}:\n{out}")
    tasks, err2 = deepseek_ai.ask(deepseek_ai.PROMPTS["action_items"],
                                  body, temperature=0)
    if err2:
        print(f"[✗] Задачи дня не собраны: {err2}")
    else:
        print(f"[ai] Задачи на день ({day}):\n{tasks}")
        # единый лог: сводка дня + задачи — txt с датой-временем + TG
        try:
            import textlog
            textlog.save("сводка",
                         f"Итог дня {day}:\n\n{out}\n\nЗадачи на день:\n{tasks}",
                         to_tg=True)
        except Exception:
            pass
    return out


# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
