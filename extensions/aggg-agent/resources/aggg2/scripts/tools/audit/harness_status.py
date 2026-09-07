#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""harness_status — единый отчёт по всем харнесам: что установлено,
какие слои разнесены, прошивка on/off.

Паттерн индустрии: multi-harness agent contract (HMS Commander) —
единый контракт поперёк харнесов: правила/скиллы/субагенты/MCP.
Собирает данные из harness_map + toggle-состояния + конфигов.

Использование:
    python3 scripts/tools/audit/harness_status.py
    python3 scripts/tools/audit/harness_status.py --harness claude codex
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))) + "/scripts/install")

from harness_map import HARNESSES, expand  # noqa: E402

HOME = Path.home()
STATE = HOME / ".aggg2" / "toggle-state.json"


def _rules_ok(h) -> bool:
    p = (h.get("paths") or {}).get("posix")
    if not p:
        return False
    return Path(expand(p, "posix")).expanduser().is_file()


def _skills_n(h) -> int:
    sk = (h.get("skills") or {}).get("posix")
    if not sk:
        return 0
    if isinstance(sk, (list, tuple)):
        sk = sk[0]
    d = Path(sk).expanduser()
    return len(list(d.glob("*/SKILL.md"))) if d.is_dir() else 0


def _agents_n(h) -> int:
    ag = (h.get("agents") or {}).get("posix")
    if not ag:
        return 0
    if isinstance(ag, (list, tuple)):
        ag = ag[0]
    d = Path(ag).expanduser()
    return len(list(d.glob("*.md"))) + len(list(d.glob("*.toml"))) \
        if d.is_dir() else 0


def _mcp_n(h) -> int:
    name = h["name"]
    files = {
        "opencode": "~/.config/opencode/opencode.jsonc",
        "claude": "~/.claude.json",
        "codex": "~/.codex/config.toml",
        "gemini": "~/.gemini/settings.json",
        "antigravity": "~/.gemini/config/mcp_config.json",
        "omp": "~/.omp/agent/mcp.json",
    }
    p = files.get(name)
    if not p:
        return 0
    fp = Path(p).expanduser()
    if not fp.is_file():
        return 0
    try:
        raw = fp.read_text(encoding="utf-8", errors="ignore")
        if fp.suffix == ".toml":
            return len(re.findall(r"^\[mcp_servers\.", raw, re.MULTILINE))
        # jsonc: полный парсер канона (jsonc_edit) — примитивный re-стрип
        # коммент-строк не переваривал opencode.jsonc (блочные комментарии,
        # trailing commas) и давал ложные -1 (баг найден аудитом 16.08).
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from jsonc_edit import load_jsonc
        data = load_jsonc(str(fp))
        mcp = data.get("mcpServers") or data.get("mcp") or {}
        if isinstance(mcp, dict) and "servers" in mcp:
            mcp = mcp["servers"]
        return len(mcp)
    except Exception:  # noqa: BLE001 — чужой конфиг
        return -1


def _proshivka(h) -> str:
    """on/off по toggle-state и артефактам .aggg2-off."""
    if STATE.is_file():
        try:
            st = json.loads(STATE.read_text(encoding="utf-8"))
            if st.get(h["name"]):
                return "off"
        except Exception:  # noqa: BLE001
            pass
    p = (h.get("paths") or {}).get("posix")
    if not p:
        return "n/a"
    home = Path(expand(p, "posix")).expanduser()
    if home.is_file():
        return "on"
    return "off"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--harness", nargs="*", help="только эти харнесы")
    args = ap.parse_args()
    rows = HARNESSES
    if args.harness:
        rows = [h for h in HARNESSES if h["name"] in args.harness]
    print(f"{'харнес':14} {'правила':7} {'скиллы':6} {'агенты':6} "
          f"{'MCP':4} {'прошивка':8}")
    for h in rows:
        r = "✓" if _rules_ok(h) else "—"
        sk = _skills_n(h)
        ag = _agents_n(h)
        m = _mcp_n(h)
        pr = _proshivka(h)
        print(f"{h['name']:14} {r:7} {sk:5} {ag:6} "
              f"{str(m):>4} {pr:8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
