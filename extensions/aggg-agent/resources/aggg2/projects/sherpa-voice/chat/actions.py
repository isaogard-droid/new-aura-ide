#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""chat.actions — DeepSeek-кнопки под текстом (задачи/саммари/ответ/промт).
Вынесено из chat.py механически (verbatim), 15.08.2026 — гейт god-файлов."""
from store import _session_context, _session_status_line, get_session
from ui_utils import c_warn

from .polish import _ask_no_echo, _is_echo


def _action_tasks(text, marked):
    """[0] Задачи: из записи — только дела (action items)."""
    from termui import step as _step
    print(_step("ai", "Вытаскиваю задачи из записи…"))
    usage_m = {}
    out, err = _ask_no_echo("action_items", marked, usage=usage_m,
                            temperature=0, echo_ref=text)
    if not err:
        get_session().add("assistant", out)
        get_session().record_usage(usage_m)
        line = _session_status_line()
        if line:
            print(line)
    return out, err


def _action_summary(text, marked):
    """[1] Саммари: пересказ и ключевые мысли записи."""
    from termui import step as _step
    print(_step("ai", "Готовлю пересказ и ключевые мысли…"))
    usage_m = {}
    out, err = _ask_no_echo("summary", marked, usage=usage_m,
                            echo_ref=text)
    if not err:
        get_session().add("assistant", out)
        get_session().record_usage(usage_m)
        line = _session_status_line()
        if line:
            print(line)
    return out, err


def _action_answer(text, marked):
    """[2] Ответить с учётом контекста сессии (эхо-защита)."""
    import deepseek_ai
    lu = text if len(text) <= 70 else text[:70] + "…"
    print(f"[ai] Отвечаю на: {lu}")
    usage_a = {}
    out, err = deepseek_ai.ask(
        deepseek_ai.PROMPTS["answer"], marked,
        messages=_session_context(), usage=usage_a)
    if not err and _is_echo(out, marked):
        print(c_warn("[i] Эхо-ответ — переспрашиваю…"))
        demand = (marked + "\n\n(Предыдущий ответ был дословным "
                  "повтором. Это не ответ. Дай содержательный "
                  "ответ по существу: прокомментируй, дополни, "
                  "приведи примеры.)")
        out, err = deepseek_ai.ask(
            deepseek_ai.PROMPTS["answer"], demand,
            messages=_session_context(), usage=usage_a)
        if not err and _is_echo(out, marked):
            print(c_warn("[i] Ответ снова повтор — отдаю как есть."))
    if not err:
        get_session().add("assistant", out)
        get_session().record_usage(usage_a)
        line = _session_status_line()
        if line:
            print(line)
    return out, err


def _action_prompt_review(text, marked):
    """[4] Кодинг-промпт: запись → ТЗ для агента."""
    from termui import step as _step
    print(_step("ai", "Составляю кодинг-промпт (ресёрч, тесты, критерии)…"))
    review_req = (f"Озвученная человеком задача (после распознавания "
                  f"и очистки речи):\n{text}")
    usage_m = {}
    # одноразовая задача с ИЗОЛИРОВАННЫМ контекстом + эхо-защита
    # (как задачи/саммари): с историей сессии модель «продолжает»
    # последнее сообщение ассистента вместо ТЗ (проверено живьём)
    out, err = _ask_no_echo("prompt_review", review_req,
                            usage=usage_m, echo_ref=text)
    if not err:
        get_session().add("assistant", out)
        get_session().record_usage(usage_m)
        line = _session_status_line()
        if line:
            print(line)
    return out, err


# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
