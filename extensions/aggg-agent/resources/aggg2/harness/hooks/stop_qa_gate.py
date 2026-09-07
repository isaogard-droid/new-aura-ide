#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Stop-хук Claude Code: детерминированный QA-гейт конца хода.

Индустрия (code.claude.com/docs/en/best-practices): «As a deterministic
gate: a Stop hook runs your check as a script and blocks the turn from
ending until it passes». У нас QA — напоминание в PreToolUse; этот хук
делает проверку БЛОКИРУЮЩЕЙ: если в git-дереве есть правленые .py и
ruff на них не чист — ход не завершается, пока агент не починит.

Правила:
- Stop-хук запускается из cwd сессии; git-репо нет → не мешаем (exit 0).
- Проверяются только .py-файлы с незакоммиченными изменениями (diff +
  untracked) — прогон доли секунды, чужое не трогаем.
- ruff не найден в PATH — не мешаем (гейт мягко деградирует).
- stop_hook_active=true (Claude уже блокировал 8 раз) — разрешаем:
  иначе вечный блок.

Вывод (формат Claude Code Stop hook): stdout JSON {"decision":
"block"|"approve", "reason"}; exit 2 — дополнительный сигнал блокировки.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _ruff_cmd() -> str | None:
    for name in ("ruff", "ruff.exe"):
        path = shutil.which(name)
        if path:
            return path
    for extra in (Path.home() / ".local/bin",):
        cand = extra / ("ruff.exe" if sys.platform == "win32" else "ruff")
        if cand.is_file():
            return str(cand)
    return None


def _changed_py_files() -> list[str]:
    git = shutil.which("git")
    if not git:
        return []
    try:
        repo = subprocess.run([git, "rev-parse", "--is-inside-work-tree"],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if repo.returncode != 0 or repo.stdout.strip() != "true":
        return []
    names: set[str] = set()
    for argv in (["diff", "--name-only", "--diff-filter=ACMR"],
                 ["ls-files", "--others", "--exclude-standard"]):
        try:
            proc = subprocess.run([git, *argv], capture_output=True,
                                  text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode == 0:
            names.update(proc.stdout.split())
    return sorted(n for n in names if n.endswith(".py") and Path(n).is_file())


def main() -> int:
    data: dict = {}
    try:
        raw = sys.stdin.read().strip()
        if raw:
            data = json.loads(raw)
    except (OSError, ValueError):
        pass
    if data.get("stop_hook_active"):
        print(json.dumps({"decision": "approve"}), flush=True)
        return 0
    files = _changed_py_files()
    if not files:
        print(json.dumps({"decision": "approve"}), flush=True)
        return 0
    ruff = _ruff_cmd()
    if not ruff:
        print(json.dumps({"decision": "approve"}), flush=True)
        return 0
    try:
        proc = subprocess.run([ruff, "check", "--output-format=concise",
                               *files], capture_output=True, text=True,
                              timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        print(json.dumps({"decision": "approve"}), flush=True)
        return 0
    if proc.returncode == 0:
        print(json.dumps({"decision": "approve"}), flush=True)
        return 0
    reason = ("QA-гейт: ruff нашёл ошибки в правленых .py — почини и "
              "заверши ход повторно.\n" + (proc.stdout or "")[:2000])
    print(json.dumps({"decision": "block", "reason": reason},
                     ensure_ascii=False), flush=True)
    sys.stderr.write(reason + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
