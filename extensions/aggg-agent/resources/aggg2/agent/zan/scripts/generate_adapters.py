#!/usr/bin/env python3
"""Generate ZanAI harness adapters from the canonical prompt."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[1]
SOURCE = AGENT_DIR / "zan.md"
ADAPTERS = AGENT_DIR / "agents"
DESCRIPTION = (
    "Использовать по @zan для жёсткого код-ревью, разбора кривых "
    "промптов/ТЗ, технической консультации без цензуры и стресс-теста "
    "архитектуры. НЕ использовать для обучения новичков, продуктовых "
    "обсуждений и вежливой клиентской коммуникации."
)


def _body() -> str:
    text = SOURCE.read_text(encoding="utf-8").strip()
    return text + "\n\nВызов: `@zan` или делегирование.\n"


def _markdown(body: str) -> str:
    return (
        "---\n"
        "name: zan\n"
        f'description: "{DESCRIPTION}"\n'
        "mode: subagent\n"
        "permission:\n"
        "  edit: deny\n"
        "---\n\n"
        "Источник prompt: `$AGGG2_ROOT/agent/zan/zan.md`.\n\n"
        + body
    )


def _toml(body: str, codewhale: bool) -> str:
    safe_body = body.replace('"""', '\\"\\"\\"')
    header = (
        "# Generated from agent/zan/zan.md. Do not edit manually.\n\n"
        'name = "zan"\n'
        f'description = "{DESCRIPTION}"\n'
    )
    if codewhale:
        return (
            header
            + 'role_hint = "consultant"\n'
            'model_class_hint = "balanced"\n\n'
            "[instructions]\n"
            'text = """\n'
            + safe_body
            + '"""\n\n[tools]\nposture = "read-only"\n'
        )
    return (
        header
        + 'model_reasoning_effort = "medium"\n'
        'sandbox_mode = "read-only"\n'
        'nickname_candidates = ["Зан", "ZanAI"]\n\n'
        'developer_instructions = """\n'
        + safe_body
        + '"""\n'
    )


def expected() -> dict[str, str]:
    body = _body()
    return {
        "zan.md": _markdown(body),
        "zan.opencode.md": _markdown(body),
        "zan.claude.md": _markdown(body),
        "zan.codex.toml": _toml(body, codewhale=False),
        "zan.codewhale.toml": _toml(body, codewhale=True),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if adapters are stale")
    args = parser.parse_args()

    generated = expected()
    stale = []
    for name, content in generated.items():
        path = ADAPTERS / name
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path))
            continue
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"generated: {path}")

    if stale:
        print("stale adapters:", file=sys.stderr)
        for path in stale:
            print(f"  {path}", file=sys.stderr)
        return 1
    if args.check:
        print("Zan adapters are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
