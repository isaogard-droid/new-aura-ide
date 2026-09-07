#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


# Оригинал от https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна и лучше предыдущей.


"""Среда установщика LSP: пути, PATH, запуск команд.

Вынесено из install_lsp_servers.py (резка soft-файла, docs/canon/FILE-SIZE.md:
per-concern модули + тонкий barrel, перенос verbatim). Отдельный concern:
платформенное окружение (константы, где лежат бинари, как запускать
команды) — без логики установки серверов и генерации config.json.
"""


import os
import platform
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))  # scripts/ — кирпичи канона
import _compat  # noqa: E402 — общий кроссплатформенный модуль (run)

HOME = Path.home()
IS_NT = os.name == "nt"
IS_CI = os.environ.get("CI") == "true"
ARCH = platform.machine().lower()  # x86_64 / aarch64 / amd64 / arm64
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


LOCAL_BIN = HOME / ".local" / "bin"


# Общий venv воркспейса (~/.venvs/aggg2, создаётся setup.py) — используется
# только как последний fallback для pyright (если нет npm/pipx/python3).
WORKSPACE_VENV_BIN = HOME / ".venvs" / "aggg2" / ("Scripts" if IS_NT else "bin")


def have(name):
    return shutil.which(name) is not None


def npm_bin():
    npm = shutil.which("npm")
    if npm:
        r = _compat.run([npm, "prefix", "-g"])
        if r.returncode == 0:
            return Path(r.stdout.strip()) / ("Scripts" if IS_NT else "bin")
    return LOCAL_BIN


def go_bin():
    go = shutil.which("go")
    if go:
        r = _compat.run([go, "env", "GOPATH"])
        if r.returncode == 0:
            return Path(r.stdout.strip()) / "bin"
    return HOME / "go" / "bin"


def cargo_bin():
    return HOME / ".cargo" / "bin"


def _npm_cmd():
    """npm на Windows — npm.cmd (CreateProcess без shell не запускает .cmd,
    WinError 2). На posix — npm."""
    if IS_NT:
        for name in ("npm.cmd", "npm"):
            p = shutil.which(name)
            if p:
                return p
    return "npm"


def run(cmd, sudo=False):
    """Запуск команды; на posix с sudo, если нужно. FileNotFoundError
    (бинарь не в PATH — например, нет winget) — не исключение, а False:
    вызывающий показывает честное «не удалось» и идёт дальше.
    _compat.run: utf-8 + errors=replace — BUG-4 (UnicodeDecodeError в
    reader-потоках на Windows) закрыт общим хелпером."""
    c = ["sudo"] + cmd if sudo and not IS_NT else cmd
    try:
        return _compat.run(c).returncode == 0
    except FileNotFoundError:
        return False


def win_refresh_path():
    """Windows: процесс не видит PATH, изменённый после его старта (scoop,
    go install, rustup, winget) — реестр уже обновлён, а os.environ нет.
    Добавляем из реестра ТОЛЬКО недостающие каталоги (дедуп), а не
    препендим весь PATH: раздутый PATH ломает .cmd-шимки npm — cmd.exe
    имеет лимит командной строки 8191 (learn.microsoft.com «Command prompt
    line string limitation»), держим запас 8000. Текущий PATH процесса
    приоритетнее реестрового — он гарантированно работает."""
    if not IS_NT:
        return
    try:
        import winreg
    except ImportError:
        return
    reg_parts = []
    for hive, key in (
            (winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            (winreg.HKEY_CURRENT_USER, r"Environment")):
        try:
            with winreg.OpenKey(hive, key) as k:
                val, _ = winreg.QueryValueEx(k, "Path")
                if val:
                    reg_parts.extend(p for p in val.split(os.pathsep) if p)
        except OSError:
            pass
    current = os.environ.get("PATH", "")
    cur = [p for p in current.split(os.pathsep) if p]
    seen = set(cur)
    extra = []
    for p in reg_parts:
        if p not in seen:
            seen.add(p)
            extra.append(p)
    if not extra:
        return
    merged = cur + extra
    budget = 8000
    total = sum(len(p) + 1 for p in merged)
    if total > budget:
        # убираем лишнее с конца extra — реестровые дополнения наименее критичны
        while extra and total > budget:
            p = extra.pop()
            total -= len(p) + 1
        merged = cur + extra
    os.environ["PATH"] = os.pathsep.join(merged)
