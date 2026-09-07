#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""harness_snapshot — снапшот/restore конфигов харнесов.

Паттерн индустрии: точки восстановления перед массовыми правками
конфигов (repo-clean: «automatic backups before any changes»; Meridian
refactor checklist: бэкап до переноса). Снапшот — в
~/.aggg2/snapshots/<timestamp>/ (вне воркспейса, в git не попадает).

Использование:
    python3 scripts/tools/audit/harness_snapshot.py backup
    python3 scripts/tools/audit/harness_snapshot.py list
    python3 scripts/tools/audit/harness_snapshot.py restore <имя-снапшота>
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

SNAP_DIR = Path.home() / ".aggg2" / "snapshots"

CONFIGS = [
    "~/.config/opencode/opencode.jsonc",
    "~/.config/opencode/opencode.json",
    "~/.claude.json",
    "~/.claude/settings.json",
    "~/.codex/config.toml",
    "~/.gemini/settings.json",
    "~/.gemini/config/mcp_config.json",
    "~/.omp/agent/config.yml",
    "~/.hermes/config.yaml",
    "~/.hermes/SOUL.md",
    "~/.reasonix/AGENTS.md",
    "~/.codewhale/config.toml",
    "~/.deepcode/AGENTS.md",
    "~/.config/amp/AGENTS.md",
]


def _backup_file(src: Path, dst_root: Path) -> bool:
    src = src.expanduser()
    if not src.is_file():
        return False
    rel = str(src).replace(str(Path.home()), "").lstrip("/")
    dst = dst_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def cmd_backup() -> int:
    ts = time.strftime("%Y%m%d-%H%M%S")
    dst = SNAP_DIR / ts
    n = sum(1 for c in CONFIGS if _backup_file(Path(c), dst))
    print(f"[✓] снапшот {ts}: {n} файлов -> {dst}")
    return 0


def cmd_list() -> int:
    if not SNAP_DIR.is_dir():
        print("снапшотов нет")
        return 0
    for d in sorted(SNAP_DIR.iterdir(), reverse=True):
        n = sum(1 for _ in d.rglob("*") if _.is_file())
        print(f"  {d.name}  ({n} файлов)")
    return 0


def cmd_restore(name: str) -> int:
    src = SNAP_DIR / name
    if not src.is_dir():
        print(f"[!] снапшот не найден: {name}", file=sys.stderr)
        return 1
    restored = 0
    for f in sorted(src.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(src)
        dst = Path.home() / rel
        if dst.exists():
            shutil.copy2(dst, str(dst) + ".pre-restore.bak")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)
        restored += 1
    print(f"[✓] восстановлено {restored} файлов из {name} "
          f"(текущие — в .pre-restore.bak)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backup")
    sub.add_parser("list")
    r = sub.add_parser("restore")
    r.add_argument("name")
    args = ap.parse_args()
    if args.cmd == "backup":
        return cmd_backup()
    if args.cmd == "list":
        return cmd_list()
    return cmd_restore(args.name)


if __name__ == "__main__":
    sys.exit(main())
