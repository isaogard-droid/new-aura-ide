#!/usr/bin/env python3
"""Проверка синхронизации зеркал AGENTS.md.

Зеркала:
- ~/.config/opencode/AGENTS.md
- корень AGGG2.0 (./AGENTS.md)
- projects/sherpa-voice/AGENTS.md

Все три должны быть идентичны. Расхождение = ошибка.
"""
import hashlib
import sys
from pathlib import Path


def file_hash(path: Path) -> str:
    """Хэш файла для сравнения зеркал."""
    if not path.exists():
        return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[2]
    mirrors = [
        Path.home() / ".config" / "opencode" / "AGENTS.md",
        root / "AGENTS.md",
        root / "projects" / "sherpa-voice" / "AGENTS.md",
    ]

    hashes = {p: file_hash(p) for p in mirrors}
    unique = set(hashes.values())

    if len(unique) == 1 and "MISSING" not in unique:
        print("✓ Зеркала синхронизированы")
        return 0

    print("✗ Расхождение зеркал AGENTS.md:")
    for path, h in hashes.items():
        status = "✓" if h == list(unique)[0] else "✗"
        print(f"  {status} {path} ({h[:8]})")

    print("\nСинхронизируйте: python3 scripts/install/install_agents.py --all")
    return 1


if __name__ == "__main__":
    sys.exit(main())
