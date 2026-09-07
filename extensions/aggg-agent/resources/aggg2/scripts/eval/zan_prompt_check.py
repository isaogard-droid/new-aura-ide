#!/usr/bin/env python3
"""Deterministic structural checks for the ZanAI prompt and fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT / "agent" / "zan"
SOURCE = AGENT / "zan.md"
CASES = AGENT / "evals" / "cases.json"
GENERATOR = AGENT / "scripts" / "generate_adapters.py"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    required_sections = [
        "## Identity",
        "## Voice Contract",
        "## Modes",
        "## Process",
        "## Quality Bar",
        "## Edge Cases",
        "## Boundaries",
        "## Output Test",
    ]
    missing = [section for section in required_sections if section not in source]
    if missing:
        fail(f"missing source sections: {', '.join(missing)}")
    if "безопас" not in source.lower() or "read-only" not in source.lower():
        fail("source lost safety or read-only boundary")

    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        fail(result.stderr.strip() or "generated adapters are stale")

    adapters = [
        AGENT / "agents" / "zan.md",
        AGENT / "agents" / "zan.opencode.md",
        AGENT / "agents" / "zan.claude.md",
        AGENT / "agents" / "zan.codex.toml",
        AGENT / "agents" / "zan.codewhale.toml",
    ]
    for path in adapters:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".toml":
            data = tomllib.loads(text)
            if data.get("name") != "zan":
                fail(f"wrong TOML name in {path}")
        elif "name: zan" not in text or "edit: deny" not in text:
            fail(f"invalid Markdown adapter metadata in {path}")
        if "## Voice Contract" not in text or "@zan" not in text:
            fail(f"adapter lost voice contract or trigger: {path}")

    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if len(cases) < 30:
        fail(f"expected at least 30 eval cases, got {len(cases)}")
    ids = [case.get("id") for case in cases]
    if len(ids) != len(set(ids)) or any(not case.get("prompt") for case in cases):
        fail("eval cases must have unique ids and non-empty prompts")
    modes = {case.get("mode") for case in cases}
    if not {"banter", "fact", "review", "explain", "refusal"} <= modes:
        fail(f"eval modes incomplete: {sorted(modes)}")

    print(f"PASS: source, {len(adapters)} adapters, {len(cases)} eval cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
