#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""claude_plugin — установка AGGG2.0 как Claude Code плагина.

Паттерн индустрии: официальный plugin/marketplace Claude Code
(code.claude.com/docs/en/plugins-reference): .claude-plugin/plugin.json +
commands/ (промпт-команды /bro, /findings, /canon) в harness/claude/plugin/;
marketplace — harness/claude/.claude-plugin/marketplace.json.

Установка требует залогиненного Claude Code (claude /login). Команды:
    /plugin marketplace add <путь к harness/claude>
    /plugin install aggg2@aggg2-marketplace

Использование:
    python3 scripts/install/harness_plugins/claude_plugin.py [--check]
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))  # корень чулана
ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
MKT = ROOT / "harness" / "claude"


def _claude_ok() -> bool:
    r = subprocess.run(["claude", "--version"], capture_output=True,
                       text=True, timeout=30)
    return r.returncode == 0


def _logged_in() -> bool:
    r = subprocess.run(["claude", "-p", "Ответь одним словом: ок"],
                       capture_output=True, text=True, timeout=60)
    return "Not logged in" not in (r.stdout + r.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="dry-run")
    args = ap.parse_args()
    print(f"плагин: {MKT / 'plugin'}  marketplace: {MKT}")
    if not _claude_ok():
        print("[!] claude CLI не установлен", file=sys.stderr)
        return 1
    if not _logged_in():
        print("[!] Claude Code не залогинен — выполни `claude /login`, "
              "затем:", file=sys.stderr)
        print(f"    /plugin marketplace add {MKT}")
        print("    /plugin install aggg2@aggg2-marketplace")
        return 1
    if args.check:
        print("[~] dry-run: установка возможна (CLI залогинен)")
        return 0
    r1 = subprocess.run(["claude", "-p",
                         f"/plugin marketplace add {MKT}"],
                        capture_output=True, text=True, timeout=120)
    r2 = subprocess.run(["claude", "-p",
                         "/plugin install aggg2@aggg2-marketplace"],
                        capture_output=True, text=True, timeout=120)
    print((r1.stdout + r1.stderr)[:300])
    print((r2.stdout + r2.stderr)[:300])
    return 0 if r2.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
