#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Установка бинарника agent-lsp с GitHub Releases (latest).

Вынесено из install_lsp_servers.py (резка soft-файла, docs/canon/FILE-SIZE.md:
per-concern модули + тонкий barrel, перенос verbatim). Отдельный concern:
скачивание/распаковка бинаря — без логики установки LSP-серверов.
"""
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path

IS_NT = os.name == "nt"


def agent_lsp_bin():
    """Путь к бинарю agent-lsp: в PATH или рядом с конфигом (mcp/agent-lsp/)."""
    exe = shutil.which("agent-lsp")
    if exe:
        return Path(exe)
    cand = Path("mcp") / "agent-lsp" / ("agent-lsp.exe" if IS_NT else "agent-lsp")
    return cand if cand.is_file() else None


def _urlopen_https(url, timeout):
    """urlopen только по https: урлы собираются из API GitHub, но
    «динамический urllib» — известный паттерн SSRF/file:// (semgrep
    dynamic-urllib-use-detected). Явная проверка схемы закрывает его."""
    if not url.startswith("https://"):
        raise ValueError(f"небезопасный URL (нужен https://): {url}")
    # nosemgrep: dynamic-urllib-use-detected — схема проверена строкой выше
    return urllib.request.urlopen(url, timeout=timeout)


def install_agent_lsp_binary():
    """Скачивает бинарь agent-lsp с GitHub Releases (latest) — Windows,
    macOS, Linux, amd64/arm64. До этого на Windows был только ручной шаг:
    «скачать zip с GitHub Releases вручную» — спотыкались все."""
    exe = agent_lsp_bin()
    if exe:
        print(f"   [–] agent-lsp уже есть: {exe}")
        return True
    try:
        import zipfile

        api = "https://api.github.com/repos/blackwell-systems/agent-lsp/releases/latest"
        with _urlopen_https(api, timeout=30) as r:
            rel = json.load(r)
        tag = rel["tag_name"].lstrip("v")
        os_name = {"win32": "windows", "darwin": "darwin"}.get(sys.platform, "linux")
        arch = "arm64" if sys.maxsize.bit_length() == 63 and sys.platform == "darwin" else (
            "arm64" if sys.platform in ("darwin", "linux") and "aarch64" in (
                os.uname().machine if hasattr(os, "uname") else "") else "amd64")
        asset_name = f"agent-lsp_{os_name}_{arch}.zip"
        asset = next((a for a in rel["assets"] if a["name"] == asset_name), None)
        if not asset:
            print(f"   [!] ассет {asset_name} не найден в релизе {tag} — "
                  f"ставьте вручную")
            return False
        dest_dir = Path("mcp") / "agent-lsp"
        dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"   [~] скачиваю agent-lsp {tag} ({asset_name})…")
        with _urlopen_https(asset["browser_download_url"], timeout=120) as r:
            data = r.read()
        zpath = dest_dir / asset_name
        zpath.write_bytes(data)
        with zipfile.ZipFile(zpath) as z:
            z.extractall(dest_dir)  # noqa: S202 — dest_dir свой, архив из офиц. релиза
        zpath.unlink()
        print(f"   [✓] agent-lsp -> {dest_dir}")
        return True
    except Exception as e:  # noqa: BLE001 — сетевой шаг, ошибку говорим честно
        print(f"   [!] не удалось скачать agent-lsp: {e}")
        return False
