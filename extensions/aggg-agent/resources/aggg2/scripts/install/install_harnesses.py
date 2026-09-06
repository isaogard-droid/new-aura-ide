#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.




# Владелец проекта: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия неповторима, новая — ещё лучше.
"""Кроссплатформенный установщик агентных харнесов (Linux/macOS/Windows).

Команды установки живут в install_agents.py (один источник, поле install)
— этот скрипт только выполняет их. Проверяет наличие инструмента перед
установкой (which/where).

Запуск:
    python3 install_harnesses.py --list                 # команды установки
    python3 install_harnesses.py                        # установить всё, чего нет
    python3 install_harnesses.py deepcode omp           # только указанные
    python3 install_harnesses.py --exclude deepcode omp # все, кроме указанных
    python3 install_harnesses.py --force deepcode       # переустановить
"""
import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона

# Windows-консоль по умолчанию cp1251 — русский вывод падает с
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass

from install_agents import HARNESSES


def bin_exists(name):
    if os.name == "nt":
        r = subprocess.run(["where", name], capture_output=True, check=False)
        return r.returncode == 0
    return shutil.which(name) is not None


def run(cmd):
    print(f"[~] {cmd}")
    try:
        if os.name == "nt":
            # Команды харнесов для Windows написаны под PowerShell
            # (irm ... | iex)
            r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                               check=False, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
        else:
            r = subprocess.run(["bash", "-c", cmd], check=False,
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as exc:
        # БАГ-ФИКС AGGG2-2026-08-16-01: одна упавшая команда НЕ должна
        # ронять весь проход по харнесам. Windows Defender блокирует
        # «irm URL | iex» из python-subprocess (PermissionError
        # [WinError 5]) — подсказываем вручную из PowerShell.
        print(f"[✗] {cmd[:60]}: {exc}")
        if os.name == "nt" and isinstance(exc, PermissionError):
            print("[i] Windows Defender может блокировать 'irm | iex' из "
                  "python-subprocess — запусти команду вручную в "
                  "интерактивном PowerShell и перезапусти установщик")
        return False
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "")[-300:]
        print(f"[✗] {cmd[:60]}: код {r.returncode}\n{tail}")
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description="Установщик харнесов")
    ap.add_argument("names", nargs="*", help="только эти харнесы (по умолчанию все)")
    ap.add_argument("--exclude", nargs="+", default=[], help="все, кроме указанных")
    ap.add_argument("--list", action="store_true", help="показать команды установки")
    ap.add_argument("--force", action="store_true", help="установить, даже если уже стоит")
    args = ap.parse_args()

    platform = "nt" if os.name == "nt" else "posix"
    selected = [h for h in HARNESSES
                if (not args.names or h["name"] in args.names)
                and h["name"] not in args.exclude]

    if args.list:
        for h in selected:
            inst = (h.get("install") or {}).get(platform)
            print(f"{h['name']:12s}: {inst or '— (не задокументировано)'}")
        return

    ok, failed = [], []
    for h in selected:
        inst = (h.get("install") or {}).get(platform)
        if not inst:
            # GUI-харнесы (antigravity IDE) ставятся вручную — это не ошибка,
            # setup.py не должен падать из-за отсутствия CLI-команды.
            print(f"[ ] {h['name']}: команда установки не задокументирована — пропуск")
            continue
        name = h["name"]
        if not args.force and bin_exists(name):
            print(f"[=] {name}: уже установлен — пропуск (--force для переустановки)")
            continue
        if run(inst):
            ok.append(name)
        else:
            failed.append(name)

    print(f"\nитого: установлено/обновлено {len(ok)}, ошибки/пропущены {len(failed)}")
    if failed:
        print("не удались:", ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
