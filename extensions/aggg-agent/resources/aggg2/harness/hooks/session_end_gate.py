#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""SessionEnd-хук: детерминированный журнал конца сессии.

Индустрия (code.claude.com/docs/en/hooks): события сессии — место для
того, что должно происходить ВСЕГДА, а не по памяти модели. Сейчас
чекпоинт-ритуал (CYCLE.md «Цикл чекпоинта сессии») — промпт-правило,
которое забывается; этот хук пишет компактную запись конца сессии в
~/.cache/aggg2-hook/sessions.jsonl детерминированно: что делалось
(чтения/веб/правки кода/тесты) + флаг qa_gap (правился код — тесты не
запускались). Флаг qa_gap — сигнал следующему агенту при чекпоинт-поиске.

Формат входа (Claude Code SessionEnd): {session_id, transcript_path,
cwd, hook_event_name}. Ошибки = молчаливый allow (хук не ломает сессию).
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from hook_gates import _get_cache_dir, _idx_state  # noqa: E402

JOURNAL = Path(_get_cache_dir()) / "sessions.jsonl"


def _append(entry: dict) -> None:
    try:
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with open(JOURNAL, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def main() -> int:
    data = {}
    try:
        raw = sys.stdin.read().strip()
        if raw:
            data = json.loads(raw)
    except (OSError, ValueError):
        pass
    if not isinstance(data, dict):
        data = {}
    if data.get("hook_event_name") != "SessionEnd":
        # Событие не наше — не мешаем (хук зарегистрирован только на SessionEnd)
        print(json.dumps({"decision": "approve"}), flush=True)
        return 0
    session_id = str(data.get("session_id") or "")
    state = _idx_state(session_id)
    code_changed = bool(state.get("code_changed"))
    tests_run = bool(state.get("tests_run"))
    entry = {
        "ts": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M"),
        "session_id": session_id or "-",
        "cwd": str(data.get("cwd") or ""),
        "reads": int(state.get("reads") or 0),
        "web": bool(state.get("web")),
        "code_changed": code_changed,
        "tests_run": tests_run,
        "qa_gap": code_changed and not tests_run,
    }
    _append(entry)
    if entry["qa_gap"]:
        sys.stderr.write(
            "QA-гейт: в сессии правился код, тесты не запускались — "
            "записано в sessions.jsonl (qa_gap). Следующая сессия должна "
            "свериться: `grep qa_gap ~/.cache/aggg2-hook/sessions.jsonl | "
            "tail -1`.\n")
    print(json.dumps({"decision": "approve"}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
