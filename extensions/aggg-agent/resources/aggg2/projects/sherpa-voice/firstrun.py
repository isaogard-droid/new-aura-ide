#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Онбординг при первом запуске (паттерн OpenClaw/OpenCode CLI).

Детект → проверить → предложить → Skip → режим без ИИ:
- если DeepSeek-ключ уже есть (env/.env) — ничего не спрашиваем, всё вкл.;
- если нет — спрашиваем один раз: ввести ключ / пропустить;
- при «пропустить» — флаг в настройках: программа работает чисто как
  транскрайбер (полировка/теги/действия меню отключены), но спросить
  можно снова в любой момент (меню Telegram/действий).

Настройки в config-файле (рядом с telegram.txt): deepseek_key=<введённый>
или deepseek_skip=1.
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""
import os

DEEPSEEK_CFG = os.path.expanduser("~/.cache/sherpa-voice/deepseek.cfg")


def _load_cfg():
    data = {}
    try:
        with open(DEEPSEEK_CFG, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
    except OSError:
        pass
    return data


def _save_cfg(data):
    os.makedirs(os.path.dirname(DEEPSEEK_CFG), exist_ok=True)
    with open(DEEPSEEK_CFG, "w", encoding="utf-8", newline="\n") as f:
        for k, v in data.items():
            f.write(f"{k}={v}\n")


def skip_reason():
    """Почему режим без ИИ: 'нет ключа' / 'пропущено при настройке' / None."""
    cfg = _load_cfg()
    if cfg.get("deepseek_skip") == "1":
        return "пропущено при настройке"
    if cfg.get("deepseek_key"):
        return None
    return None  # ключ мог появиться в env — решает вызывающий (load_key)


def onboard(load_key, force=False):
    """Первый запуск: спросить про DeepSeek-ключ, если его нет.
    load_key — функция deepseek_ai.load_key (проверяет env/.env).
    force=True — спросить ВСЕГДА (для /reconfigure «сменить ключ»:
    при существующем ключе обычный путь сразу вернул бы 'ok').

    Возвращает 'ok' — ключ есть (env или введён), 'skip' — пользователь
    отказался, 'err' — не удалось сохранить. Не интерактивно (--once,
    --file, --telegram-daemon) — не спрашиваем."""
    if not force:
        cfg0 = _load_cfg()
        # «Без ИИ» (off) — осознанный выбор, сильнее ключа: даже если ключ
        # появился в env, не включаем без согласия и не спрашиваем
        if cfg0.get("deepseek_off") == "1":
            return "skip"
        # ключ реально есть (env/.env/cfg) → включено; skip блокирует
        # только ВОПРОС при старте, а не работу
        if load_key():
            return "ok"
        if cfg0.get("deepseek_skip") == "1":
            return "skip"
        if cfg0.get("deepseek_key"):
            return "ok"
    # интерактивный вопрос — только если терминал живой
    try:
        if force:
            prompt = ("\n[?] Настройка DeepSeek-ключа (уже есть: "
                      "…" + (load_key() or "")[-4:] + ").\n"
                      "    [1] Ввести новый ключ   [2] Пропустить (оставить как есть)   "
                      "[Enter] Пропустить\n    > ")
        else:
            prompt = ("\n[?] DeepSeek-ключ не найден (DEEPSEEK_API_KEY).\n"
                      "    [1] Ввести ключ — включить ИИ (полировка, теги, "
                      "сводка дня, анализ)\n"
                      "    [2] Без ИИ — только запись и распознавание "
                      "(можно включить позже: /ai)\n"
                      "    [Enter] Без ИИ\n    > ")
        ans = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        ans = ""
    if ans == "1":
        try:
            key = input("    Ключ: ").strip()
        except (EOFError, KeyboardInterrupt):
            key = ""
        if key.startswith("sk-"):
            cfg = _load_cfg()
            cfg["deepseek_key"] = key
            cfg.pop("deepseek_skip", None)
            cfg.pop("deepseek_off", None)  # ввод ключа = включить ИИ
            _save_cfg(cfg)
            return "ok"
        print("[i] Ключ не похож на sk-… — оставляю как было.")
        return "skip"
    if force:
        return "skip"  # при смене — не трогаем старый ключ и skip
    # «Без ИИ» = осознанный выбор (паттерн OpenClaw 'Skip for now'):
    # ставим ОБА флага — skip (не спрашивать при старте) и off (не
    # включать ИИ, даже если ключ позже появится в .env — иначе выбор
    # пользователя перетрётся молча)
    _save_cfg({"deepseek_skip": "1", "deepseek_off": "1"})
    return "skip"


def unskip():
    """Сбросить флаг «пропущено» — чтобы спросить снова (меню)."""
    cfg = _load_cfg()
    cfg.pop("deepseek_skip", None)
    _save_cfg(cfg)

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
