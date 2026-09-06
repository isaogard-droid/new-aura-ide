#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""chat.vocab — меню словаря терминов.
Вынесено из chat.py механически (verbatim), 15.08.2026 — гейт god-файлов."""
from store import _vocab_load, _vocab_save
from ui_utils import c_ok, c_warn


def _vocab_menu():
    """Команда /vocab: показать словарь терминов, добавить пару, удалить,
    очистить. Словарь используется полировкой (custom spelling): «опен код»
    всегда становится OpenCode и т.п."""
    pairs = _vocab_load()
    if not pairs:
        print("[i] Словарь пуст.")
    else:
        print("[ai] Словарь терминов (как говоришь → как писать):")
        for i, (k, v) in enumerate(pairs, 1):
            print(f"  [{i}] {k} → {v}")
    print("  [д] добавить  [номер] удалить  [о] очистить  [Enter] назад")
    try:
        sub = input("    > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    if sub == "д":
        try:
            raw = input("  Пара «как говоришь → как писать»: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        sep = "→" if "→" in raw else ("->" if "->" in raw else None)
        if not sep:
            print(c_warn("[i] Нужен разделитель →, например: опен код → OpenCode"))
            return
        k, v = raw.split(sep, 1)
        k, v = k.strip().lower(), v.strip()
        if not k or not v:
            print(c_warn("[i] Пустая пара — не добавлено."))
            return
        pairs = [(kk, vv) for kk, vv in pairs if kk != k]
        pairs.append((k, v))
        _vocab_save(pairs)
        print(c_ok(f"[✓] Добавлено: {k} → {v}"))
    elif sub == "о":
        _vocab_save([])
        print(c_ok("[✓] Словарь очищен"))
    elif sub.isdigit():
        idx = int(sub) - 1
        if 0 <= idx < len(pairs):
            removed = pairs.pop(idx)
            _vocab_save(pairs)
            print(c_ok(f"[✓] Удалено: {removed[0]} → {removed[1]}"))
        else:
            print(c_warn("[i] Нет такой пары"))


# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
