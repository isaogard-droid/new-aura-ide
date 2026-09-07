#!/usr/bin/env python3
"""CLI-батл: команды как юзер + условия по exit/stdout/stderr (ISTQB).

Конфиг — Python-модуль с CONFIG:
    CONFIG = {
        "snapshot": callable() -> dict | None,
        "restore": callable(snap) | None,
        "timeout": 30,                    # таймаут команды по умолчанию
        "steps": [
            {"name": "...", "cmd": ["cmd", "args"], "input": None|str,
             "timeout": 30,
             "want": lambda r: r.returncode == 0 and "OK" in r.stdout,
             "wait_retry": 0},            # поллинг: повтор команды до условия
        ],
    }

want получает CompletedProcess с полями returncode/stdout/stderr/text.
wait_retry>0 — condition-based waiting для асинхронных CLI: команда
повторяется каждые 0.6-1.2с, пока want не истина (по логам/выходу), —
«сколько насколько нужно», без фиксированных sleep.
Прогресс печатается построчно сразу (tail -f лога). --json <файл> — отчёт.
"""
import importlib.util
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import battle_core  # noqa: E402


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    spec = importlib.util.spec_from_file_location("cli_config", sys.argv[1])
    cfg_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg_mod)
    cfg = getattr(cfg_mod, "CONFIG", None)
    if not isinstance(cfg, dict):
        raise SystemExit(f"в {sys.argv[1]} нет CONFIG (dict)")

    class _TimedOut:
        """Команда убита по таймауту — легитимный исход шага (timeout=True)."""
        returncode = None
        stdout = ""
        stderr = ""
        timeout = True

    _last = [None]

    def drive(cmd):
        if cmd == "__last__":
            return _last[0]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=cfg.get("timeout", 30))
        except subprocess.TimeoutExpired:
            r = _TimedOut()
        _last[0] = r
        return r

    steps = []
    for s in cfg["steps"]:
        retry = s.get("wait_retry", 0)
        if retry > 0:
            def wait(_drive, cmd=s["cmd"], tout=s.get("timeout", 30)):
                try:
                    return subprocess.run(cmd, capture_output=True, text=True,
                                          timeout=tout)
                except subprocess.TimeoutExpired:
                    return None
            steps.append({"name": s["name"], "action": s["cmd"],
                          "wait": wait, "want": s.get("want"),
                          "timeout": s.get("timeout", 30)})
        else:
            steps.append({"name": s["name"], "action": s["cmd"],
                          "wait": "__last__", "want": s.get("want"),
                          "timeout": s.get("timeout", 30)})
    out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    code = battle_core.run(drive, steps,
                           snapshot=cfg.get("snapshot"),
                           restore=cfg.get("restore"),
                           report_out=out, tag="cli")
    sys.exit(code)


if __name__ == "__main__":
    main()
