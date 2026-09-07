#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""extensions_gemini — установка AGGG2.0 как Gemini CLI extension.

Паттерн индустрии: официальный механизм Gemini CLI (extensions пакет:
контекст + MCP + команды в одном манифесте gemini-extension.json) —
вместо ручной правки settings.json. Extension «aggg2»: монолит GEMINI.md
как contextFileName + рабочие MCP-серверы воркспейса (берутся из текущих
~/.gemini/settings.json — источник правды доставки install_mcp).

Установка — link (симлинк на каталог чулана: обновления сразу, без
gemini extensions update). Требует git в PATH (требование gemini CLI).

Использование:
    python3 scripts/install/harness_plugins/extensions_gemini.py [--check]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))  # корень чулана
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))) + "/scripts")
from _compat import chulan_root  # noqa: E402

HOME = Path.home()
EXT_DIR = HOME / ".gemini" / "extensions"
NAME = "aggg2"


def _mcp_from_settings() -> dict:
    """Рабочие MCP-серверы gemini из settings.json (доставлены install_mcp)."""
    p = HOME / ".gemini" / "settings.json"
    if not p.is_file():
        return {}
    try:
        return json.load(open(p, encoding="utf-8")).get("mcpServers", {})
    except Exception:  # noqa: BLE001 — чужой конфиг, не ломаемся
        return {}


def _manifest(mcp: dict) -> dict:
    return {
        "name": NAME,
        "version": "1.0.0",
        "description": ("AGGG2.0: ядро правил, веб-ресёрч (Camoufox), "
                        "база знаний (db-tools), граф кода, LSP — "
                        "t.me/aidvizhenie"),
        "contextFileName": "GEMINI.md",
        "mcpServers": mcp,
    }


def _src_dir() -> Path:
    return Path(chulan_root()) / "harness" / "gemini" / "extension"


def _sync_source(monolith: str) -> None:
    """Каталог-источник extension в чулане: манифест генерится, GEMINI.md
    — копия монолита (источник правды — ~/.gemini/GEMINI.md)."""
    src = _src_dir()
    src.mkdir(parents=True, exist_ok=True)
    (src / "gemini-extension.json").write_text(
        json.dumps(_manifest(_mcp_from_settings()), indent=2,
                   ensure_ascii=False) + "\n", encoding="utf-8")
    mono = Path(monolith).expanduser()
    if mono.is_file():
        shutil.copy2(mono, src / "GEMINI.md")


def _link() -> None:
    target = EXT_DIR / NAME
    src = _src_dir()
    if target.exists() or target.is_symlink():
        if target.is_symlink() and os.readlink(str(target)) == str(src):
            print(f"[=] extension уже прилинкован: {target}")
            return
        print(f"[~] заменяю существующий: {target}")
        if target.is_symlink():
            target.unlink()
        else:
            shutil.rmtree(target)
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    os.symlink(src, target)
    print(f"[✓] extension прилинкован: {target} -> {src}")


def _verify() -> int:
    r = subprocess.run(["gemini", "extensions", "list"], capture_output=True,
                       text=True, timeout=60)
    out = (r.stdout or "") + (r.stderr or "")
    if NAME in out:
        print(f"[✓] gemini CLI видит extension: {NAME}")
        return 0
    print(f"[!] gemini CLI не показал {NAME} (возможно, CLI не установлен "
          f"или нужен рестарт сессии):\n{out[:300]}", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="dry-run")
    ap.add_argument("--monolith", default=str(HOME / ".gemini" / "GEMINI.md"),
                    help="файл монолита для контекста")
    args = ap.parse_args()
    if args.check:
        m = _mcp_from_settings()
        print(f"план: extension '{NAME}' -> {EXT_DIR / NAME}")
        print(f"  contextFileName: GEMINI.md (из {args.monolith})")
        print(f"  mcpServers: {', '.join(m) or '—'}")
        return 0
    _sync_source(args.monolith)
    _link()
    return _verify()


if __name__ == "__main__":
    sys.exit(main())
