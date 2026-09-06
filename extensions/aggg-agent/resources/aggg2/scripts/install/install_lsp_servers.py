#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


# Оригинал от https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна и лучше предыдущей.
"""Установка LSP-серверов для agent-lsp (кроссплатформенно: Linux/macOS/Windows).

Серверы ставятся ГЛОБАЛЬНО на машину (npm -g, pipx, pip --user, пакет ОС,
go install, rustup, GitHub release) — скрипт универсален, не привязан
к конкретному проекту воркспейса и работает на любом железе/ОС.

Идемпотентный: уже установленное пропускает, ставит недостающее.
В конце генерирует mcp/agent-lsp/config.json с реальными путями бинарей.
На CI (env CI=true) пропускает тяжёлые загрузки (clangd/lua) — не таскает
гигабайты на раннерах, логика npm/go/rustup/генерации проверяется и так.

Данные (что ставить, аргументы, маппинг языков) — в lsp_data.py:
код — только логика установки/проверки (declarative config).

Запуск:
    python3 install_lsp_servers.py                 # поставить всё недостающее
    python3 install_lsp_servers.py --doctor        # + agent-lsp doctor после
    python3 install_lsp_servers.py --only-config   # только пересоздать config.json
    python3 install_lsp_servers.py --check         # план: что есть / чего нет
Резка soft-файла (docs/canon/FILE-SIZE.md): установщики серверов вынесены в
lsp_installers.py, среда (пути/PATH/запуск команд) — в lsp_env.py
(перенос verbatim). Здесь: генерация config.json, check/doctor и CLI (main).
"""


import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона


from pathlib import Path

from lsp.lsp_data import (
    LANG_SERVERS,
    SERVER_ARGS,
    check_bins,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from lsp.lsp_agent_binary import (  # noqa: E402 — резка soft-файла (docs/canon/FILE-SIZE.md)
    agent_lsp_bin,
    install_agent_lsp_binary,
)
from lsp.lsp_env import (  # среда: пути/PATH/запуск (вынесено, docs/canon/FILE-SIZE.md)
    ARCH,
    HOME,
    IS_CI,
    IS_NT,
    LOCAL_BIN,
    WORKSPACE_VENV_BIN,
    cargo_bin,
    go_bin,
    have,
    npm_bin,
    run,
    win_refresh_path,
)
from lsp.lsp_installers import (  # установщики серверов (вынесено, docs/canon/FILE-SIZE.md)
    install_clangd,
    install_gopls,
    install_lua,
    install_npm_servers,
    install_pyright,
    install_rust_analyzer,
    link_all,
    npm_install,
)

__all__ = [
    "ARCH",
    "CONFIG",
    "HOME",
    "IS_CI",
    "IS_NT",
    "LOCAL_BIN",
    "ROOT",
    "WORKSPACE_VENV_BIN",
    "cargo_bin",
    "check_plan",
    "doctor",
    "gen_config",
    "go_bin",
    "have",
    "install_clangd",
    "install_gopls",
    "install_lua",
    "install_npm_servers",
    "install_pyright",
    "install_rust_analyzer",
    "link_all",
    "main",
    "npm_bin",
    "npm_install",
    "run",
    "win_refresh_path",
]


# Windows-консоль по умолчанию cp1251 — русский вывод падает с
# UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "mcp" / "agent-lsp" / "config.json"


# Карта после резки (docs/canon/FILE-SIZE.md): lsp_env.py — среда (константы,
# где лежат бинари, запуск команд); lsp_installers.py — установка
# серверов (npm/go/rustup/pipx/…); здесь — генерация mcp/agent-lsp/
# config.json (gen_config/_resolvers/_find), check_plan, doctor, main.


def _resolvers():
    """Резолверы шаблонов путей из lsp_data.LANG_SERVERS. Резолвер,
    вернувший None, делает шаблон невалидным (путь пропускается)."""
    win_get = (Path(os.environ.get("LOCALAPPDATA", HOME))
               / "Microsoft" / "WinGet" / "Links")
    return {
        "go_bin": str(go_bin()),
        "cargo_bin": str(cargo_bin()),
        "npm_bin": str(npm_bin()),
        "local_bin": str(LOCAL_BIN),
        "home": str(HOME),
        # Windows: winget кладёт clangd в %LOCALAPPDATA%\...\WinGet\Links\
        "win_get": str(win_get) if IS_NT else None,
    }


def _resolve_extra(templates, resolvers):
    """Шаблоны extra → реальные пути; шаблоны с None-резолвером пропускаются."""
    out = []
    for t in templates:
        s = t.format_map(resolvers)
        if "None" in s:
            continue  # резолвер вернул None (например, win_get на posix)
        out.append(s)
    return out


def _find(names, extra=()):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    for p in extra:
        if Path(p).is_file():
            return str(p)
    return None


# --- генерация mcp/agent-lsp/config.json из реальных путей ---
def gen_config():
    print(f"\n== генерация {CONFIG} ==")

    pyright = _find(["pyright-langserver"])
    resolvers = _resolvers()
    servers = []
    if pyright:
        servers.append((["py"], [pyright] + SERVER_ARGS["pyright-langserver"]))
    for entry in LANG_SERVERS:
        p = _find(entry["names"], _resolve_extra(entry["extra"], resolvers))
        if p:
            # Windows-шимки npm: bash-language-server.cmd/.exe — снимаем
            # расширение для сопоставления с server_args
            name = Path(p).name.lower()
            for ext in (".exe", ".cmd", ".bat"):
                if name.endswith(ext):
                    name = name[:-len(ext)]
                    break
            args = SERVER_ARGS.get(name, [])
            servers.append((entry["exts"], [p] + args))

    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(
        {"servers": [{"extensions": exts, "command": cmd}
                     for exts, cmd in servers]},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"   [✓] конфиг обновлён: {len(servers)} серверов")


def check_plan():
    """--check: показать, что есть / чего нет (ничего не ставит)."""
    print("== План (что установлено / чего нет) ==")
    for b in check_bins():
        found = have(b) or (go_bin() / b).is_file()
        print(f"   {'[✓]' if found else '[ ]'} {b}")
    print("   [i] CI:", "да (тяжёлые пропускаются)" if IS_CI else "нет")
    gen_config()


def doctor():
    bin = agent_lsp_bin()
    if bin and bin.is_file():
        subprocess.run([str(bin), "doctor"], check=False)
    else:
        print("[!] agent-lsp не установлен — doctor пропущен")


def main():
    ap = argparse.ArgumentParser(description="Установщик LSP-серверов для agent-lsp")
    ap.add_argument("--doctor", action="store_true",
                    help="после установки прогнать agent-lsp doctor")
    ap.add_argument("--only-config", action="store_true",
                    help="только пересоздать config.json")
    ap.add_argument("--check", action="store_true",
                    help="план: что установлено, ничего не ставить")
    args = ap.parse_args()

    # Свежие бинари (scoop/go/rustup/winget) уже в реестре Windows, но не в
    # os.environ этого процесса — обновляем PATH до всех проверок have()
    win_refresh_path()

    if args.check:
        check_plan()
        return
    if args.only_config:
        gen_config()
        return

    install_agent_lsp_binary()
    install_npm_servers()
    install_gopls()
    install_rust_analyzer()
    install_pyright()
    install_clangd()
    install_lua()
    link_all()
    gen_config()
    if args.doctor:
        doctor()
    print("\nГотово. Перезапусти opencode, чтобы agent-lsp подхватил новый "
          "конфиг.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)


# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
