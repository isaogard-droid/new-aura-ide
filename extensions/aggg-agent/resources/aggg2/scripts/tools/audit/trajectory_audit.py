#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Аудит траекторий сессий (паттерн HarnessAudit, arXiv 2605.14271:
output-level оценка не видит mid-trajectory нарушений). Живые хуки
сторожат вызовы, этот скрипт аудирует УЖЕ состоявшиеся сессии по
транскриптам (~/.claude/projects/*.jsonl, ~/.codex/sessions/*.jsonl):
- проскочившие опасные команды (pkill без трюка, rm -rf /, git reset
  --hard, curl|bash) — проверка эффективности хука;
- секреты в выводе ассистента;
- canary-токен (утечка системного промпта);
- статистика: сессии, ходы, тул-вызовы, токены.

Запуск:
    python3 scripts/tools/trajectory_audit.py            # все найденные транскрипты
    python3 scripts/tools/trajectory_audit.py --dir <путь>
    python3 scripts/tools/trajectory_audit.py --days 7
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

# Паттерны — зеркало BLOCK_RULES сторожа (harness/hooks/aggg2_prompt_hook.py):
# аудит проверяет, что хук реально не пропускал.
RISKY = [
    (re.compile(r"pkill\s+(-[a-zA-Z0-9]+\s+)*-f\s+[\"']?[^\[\"']"), "pkill-без-трюка"),
    (re.compile(r"rm\s+-[a-z]*r[a-z]*f?\s+/\*?(\s|$|[\"'])"), "rm-rf-корень"),
    (re.compile(r"git\s+reset\s+--hard"), "git-reset-hard"),
    (re.compile(r"curl\s+[^|&\n]*\|\s*(sudo\s+)?(ba|z|da|k|fi)?sh\b"), "curl-bash"),
]
SECRET_RE = re.compile(
    r"(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{30,}|"
    r"AKIA[0-9A-Z]{16}|api[_-]?key[\"'\s:=]+[a-zA-Z0-9]{20,})",
    re.IGNORECASE)
CANARY_RE = re.compile(r"AGGG2-CANARY-[0-9a-f]{24}")


def _transcript_dirs() -> list[Path]:
    dirs = [Path.home() / ".claude" / "projects"]
    codex = Path.home() / ".codex" / "sessions"
    if codex.is_dir():
        dirs.append(codex)
    return dirs


def _iter_jsonl(root: Path, days: int | None):
    cutoff = time.time() - days * 86400 if days else 0
    for f in root.rglob("*.jsonl"):
        try:
            if days and f.stat().st_mtime < cutoff:
                continue
            yield f
        except OSError:
            continue


def _audit_file(path: Path) -> dict:
    out = {"turns": 0, "tool_calls": 0, "risky": [], "secrets": [],
           "canary": [], "tokens": 0}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.startswith("{"):
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                msg = ev.get("message") or {}
                if ev.get("type") in ("assistant", "user") or "content" in msg:
                    out["turns"] += 1
                content = json.dumps(msg.get("content", ""), ensure_ascii=False)
                if isinstance(msg.get("content"), list):
                    content = json.dumps(msg["content"], ensure_ascii=False)
                if ev.get("type") == "assistant":
                    for tool in msg.get("content", []):
                        if isinstance(tool, dict) and tool.get("type") == "tool_use":
                            out["tool_calls"] += 1
                            inp = json.dumps(tool.get("input", {}),
                                             ensure_ascii=False)
                            for rx, tag in RISKY:
                                if rx.search(inp):
                                    out["risky"].append((tag, inp[:120]))
                if SECRET_RE.search(content):
                    out["secrets"].append(SECRET_RE.search(content).group(0)[:40])
                if CANARY_RE.search(content):
                    out["canary"].append(CANARY_RE.search(content).group(0))
                usage = ev.get("message", {}).get("usage") or {}
                out["tokens"] += int(usage.get("input_tokens") or 0)
                out["tokens"] += int(usage.get("output_tokens") or 0)
    except OSError:
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[3])
    ap.add_argument("--dir", metavar="ПУТЬ", help="каталог транскриптов "
                    "(по умолчанию: ~/.claude/projects, ~/.codex/sessions)")
    ap.add_argument("--days", type=int, default=0,
                    help="только транскрипты за N последних дней")
    args = ap.parse_args()
    roots = [Path(args.dir).expanduser()] if args.dir else _transcript_dirs()
    total = {"files": 0, "turns": 0, "tool_calls": 0, "tokens": 0}
    risky_all, secrets_all, canary_all = [], [], []
    for root in roots:
        if not root.is_dir():
            continue
        for f in _iter_jsonl(root, args.days):
            r = _audit_file(f)
            total["files"] += 1
            total["turns"] += r["turns"]
            total["tool_calls"] += r["tool_calls"]
            total["tokens"] += r["tokens"]
            for tag, cmd in r["risky"]:
                risky_all.append((str(f)[-40:], tag, cmd))
            for s in r["secrets"]:
                secrets_all.append((str(f)[-40:], s))
            for c in r["canary"]:
                canary_all.append((str(f)[-40:], c))
    print(f"транскриптов: {total['files']}, ходов: {total['turns']}, "
          f"тул-вызовов: {total['tool_calls']}, токенов: {total['tokens']:,}")
    print(f"\nОПАСНЫЕ команды (проскочили хук): {len(risky_all)}")
    for f, tag, cmd in risky_all[:20]:
        print(f"  [{tag}] {f}\n    {cmd}")
    print(f"\nСЕКРЕТЫ в выводе: {len(secrets_all)}")
    for f, s in secrets_all[:10]:
        print(f"  {f}: {s}")
    print(f"\nCANARY (утечка промпта): {len(canary_all)}")
    for f, c in canary_all[:5]:
        print(f"  {f}: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
