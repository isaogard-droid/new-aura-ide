#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""State-хелперы toggle_proshivka: чтение/запись конфигов, бэкапы,
состояние off/on. Вынесено из toggle_proshivka.py (резка soft-файла,
docs/canon/FILE-SIZE.md: per-concern модули + тонкий barrel, перенос verbatim)."""

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
from pathlib import Path

from _compat import fix_encoding  # noqa: E402 — единый хелпер канона

fix_encoding()

from jsonc_edit import load_jsonc, write_json  # noqa: E402
from toggle.toggle_map import ALL, HOME  # noqa: E402

STATE_PATH = HOME / ".aggg2" / "toggle-state.json"

__all__ = ["STATE_PATH", "_load", "_write", "_backup",
           "load_state", "save_state", "_owners_off"]


def _load(path: Path) -> dict:
    """Прочитать JSON/JSONC-конфиг (utf-8-sig: BOM не убивает парсинг)."""
    try:
        return load_jsonc(str(path))
    except Exception as e:  # noqa: BLE001 — битый конфиг не трогаем
        raise ValueError(f"не могу разобрать конфиг {path}: {e!r}") from e


def _write(path: Path, data: dict) -> None:
    write_json(str(path), data)


def _backup(path: Path) -> None:
    """Бэкап перед записью. Windows: занятый файл не копируется — не роняем."""
    if not path.is_file():
        return
    bak = path.with_suffix(path.suffix + ".bak")
    try:
        shutil.copy2(path, bak)
        print(f"[~] бэкап -> {bak}")
    except OSError as e:
        print(f"[!] бэкап не сделан ({bak}): {e!r}")


def load_state() -> dict:
    if STATE_PATH.is_file():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            print(f"[!] битый state {STATE_PATH} — начинаю с чистого",
                  file=sys.stderr)
    return {"off": [], "files": {}, "configs": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8", newline="\n")


def _owners_off(owners, state, all_mode: bool, current: str) -> bool:
    """Можно ли выключить файл/конфиг: все владельцы, КРОМЕ current
    (выключаем его сейчас), уже off. Shared для всех (ALL) — только --all."""
    if owners == (ALL,):
        return all_mode
    off = set(state.get("off", []))
    others = [o for o in owners if o != current and o != ALL]
    return all(o in off for o in others)
