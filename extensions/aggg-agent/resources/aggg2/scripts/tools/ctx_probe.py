#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""ctx_probe — статический замер контекста харнеса (без вызова модели).

Паттерн индустрии: ctx-probe / ctxlens — «сколько токенов ест системный
промпт ДО первого сообщения». Считаем статически: файлы правил
(AGENTS.md/CLAUDE.md/GEMINI.md/...), описания скиллов (frontmatter),
число MCP-серверов из конфигов + (--tools) их тулы через FastMCP CLI.
Оценка: ~3 символа на токен (смешанный русский/код).

Использование:
    python3 scripts/tools/ctx_probe.py --harness opencode
    python3 scripts/tools/ctx_probe.py --all
    python3 scripts/tools/ctx_probe.py --harness claude --tools
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))) + "/scripts/install")

from harness_map import HARNESSES, expand  # noqa: E402

CHAR_PER_TOKEN = 3  # грубая: русский ~2.5, код ~3.5

RULES_FILES = {
    "opencode": ["~/.config/opencode/AGENTS.md", "~/AGENTS.md"],
    "claude": ["~/.claude/CLAUDE.md", "~/CLAUDE.md"],
    "codex": ["~/.codex/AGENTS.md", "~/AGENTS.md"],
    "gemini": ["~/.gemini/GEMINI.md", "~/GEMINI.md"],
    "hermes": ["~/.hermes/SOUL.md"],
    "reasonix": ["~/.reasonix/AGENTS.md", "~/AGENTS.md"],
    "codewhale": ["~/.codewhale/AGENTS.md"],
    "omp": ["~/.omp/agent/AGENTS.md"],
    "deepcode": ["~/.deepcode/AGENTS.md"],
    "amp": ["~/.config/amp/AGENTS.md"],
    "antigravity": ["~/.gemini/GEMINI.md"],
    "agy": ["~/.gemini/GEMINI.md"],
}

MCP_FILES = {
    "opencode": "~/.config/opencode/opencode.jsonc",
    "claude": "~/.claude.json",
    "codex": "~/.codex/config.toml",
    "gemini": "~/.gemini/settings.json",
    "omp": "~/.omp/agent/mcp.json",
    "hermes": "~/.hermes/config.yaml",
    "antigravity": "~/.gemini/config/mcp_config.json",
}


def _size_tokens(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        return path.stat().st_size // CHAR_PER_TOKEN
    except OSError:
        return 0


def _skill_desc_tokens(skills_dir: str) -> tuple[int, int]:
    """Сумма description скиллов каталога (то, что афишируется модели)."""
    total = 0
    count = 0
    d = Path(skills_dir).expanduser()
    if not d.is_dir():
        return 0, 0
    for f in d.glob("*/SKILL.md"):
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"^description:\s*(.+?)(?=^\S+:|\Z)", t,
                          re.MULTILINE | re.DOTALL)
            if m:
                total += len(m.group(1).strip())
                count += 1
        except OSError:
            continue
    return total // CHAR_PER_TOKEN, count


def _mcp_servers(path: str) -> tuple[list, int]:
    p = Path(path).expanduser()
    if not p.is_file():
        return [], 0
    try:
        raw = p.read_text(encoding="utf-8", errors="ignore")
        if p.suffix == ".toml":
            names = re.findall(r"^\[mcp_servers\.([^\].]+)\]", raw, re.MULTILINE)
        elif p.suffix in (".yaml", ".yml"):
            names = re.findall(r"^\s{2}(\S+):", raw, re.MULTILINE)
        else:
            data = json.loads(re.sub(r"//[^\n]*", "", raw))
            mcp = data.get("mcpServers") or data.get("mcp") or {}
            if isinstance(mcp, dict) and "servers" in mcp:
                mcp = mcp["servers"]
            names = list(mcp.keys())
        # оценка токенов на сервер: имя + описания тулов (~150 ток/тул,
        # ghidra-класс — 212 тулов ≈ 30k, лёгкие — 8 тулов ≈ 1.2k)
        tokens = sum(150 * 212 if n == "ghidra" else 150 * 8
                     for n in names)
        return names, tokens
    except Exception:  # noqa: BLE001 — чужой конфиг, не ломаемся
        return [], 0


def _bin_installed(harness: str) -> bool:
    for h in HARNESSES:
        if h.get("name") == harness:
            return os.path.exists(str(expand(h["paths"]["posix"], "posix")))
    return False


def probe(harness: str, with_tools: bool = False) -> dict:
    out = {"harness": harness, "rules_tokens": 0, "skills_tokens": 0,
           "skills_count": 0, "mcp_names": [], "mcp_tokens": 0,
           "installed": _bin_installed(harness)}
    for f in RULES_FILES.get(harness, []):
        out["rules_tokens"] += _size_tokens(Path(f).expanduser())
    h = next((x for x in HARNESSES if x.get("name") == harness), None)
    if h and h.get("skills"):
        sk = h["skills"]["posix"]
        out["skills_tokens"], out["skills_count"] = \
            _skill_desc_tokens(sk)
    mcp_file = MCP_FILES.get(harness)
    if mcp_file:
        names, tokens = _mcp_servers(mcp_file)
        out["mcp_names"], out["mcp_tokens"] = names, tokens
    out["total"] = (out["rules_tokens"] + out["skills_tokens"]
                    + out["mcp_tokens"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--harness", help="имя харнеса")
    ap.add_argument("--all", action="store_true", help="все харнесы")
    ap.add_argument("--tools", action="store_true",
                    help="точный список тулов MCP (медленнее, FastMCP)")
    args = ap.parse_args()
    targets = [args.harness] if args.harness else (
        list(RULES_FILES) if args.all else ["opencode"])
    print(f"{'харнес':14} {'правила':>8} {'скиллы':>8} {'MCP':>8} "
          f"{'итого':>8}  серверы")
    for h in targets:
        r = probe(h, with_tools=args.tools)
        mark = "✓" if r["installed"] else "✗"
        print(f"{h:14} {r['rules_tokens']:>7} {r['skills_tokens']:>7}"
              f" ({r['skills_count']:>2}) {r['mcp_tokens']:>7}"
              f" {r['total']:>7}  {mark} {', '.join(r['mcp_names'])[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
