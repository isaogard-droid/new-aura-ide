#!/usr/bin/env python3
"""Перф-батл: нагрузка на эндпоинт + пороги по перцентилям (ab).

Конфиг — Python-модуль с CONFIG:
    CONFIG = {
        "steps": [
            {"name": "…", "url": "http://…/", "n": 200, "c": 4,
             "want": lambda p: p.p95_ms < 200 and p.failed == 0},
        ],
    }

want получает dict: rps, failed, p50_ms, p90_ms, p95_ms, p99_ms.
Культура замера (k6/youngju): порог = распределение (p95), а не
«прошло/не прошло». ab не моделирует браузер — точечная проверка
эндпоинта (docs). Высокая нагрузка — только с согласия владельца.
"""
import importlib.util
import re
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import battle_core  # noqa: E402

PCT = {"50%": "p50_ms", "90%": "p90_ms", "95%": "p95_ms", "99%": "p99_ms"}


def _run_ab(url, n, c):
    r = subprocess.run(["ab", "-n", str(n), "-c", str(c), url],
                       capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    res = {"rps": 0.0, "failed": 0}
    m = re.search(r"Requests per second:\s+([\d.]+)", out)
    if m:
        res["rps"] = float(m.group(1))
    m = re.search(r"Failed requests:\s+(\d+)", out)
    if m:
        res["failed"] = int(m.group(1))
    for line in out.splitlines():
        m = re.match(r"\s*(\d+)%\s+(\d+)", line)
        if m and m.group(1) + "%" in PCT:
            res[PCT[m.group(1) + "%"]] = int(m.group(2))
    return res


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    spec = importlib.util.spec_from_file_location("perf_config", sys.argv[1])
    cfg_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg_mod)
    cfg = getattr(cfg_mod, "CONFIG", None)
    if not isinstance(cfg, dict):
        raise SystemExit(f"в {sys.argv[1]} нет CONFIG (dict)")

    _last = [None]

    def drive(step):
        if step == "__last__":
            return _last[0]
        _last[0] = _run_ab(step["url"], step.get("n", 200), step.get("c", 4))
        return _last[0]

    steps = [{"name": s["name"], "action": s, "wait": "__last__",
              "want": s.get("want"), "timeout": s.get("timeout", 10)}
             for s in cfg["steps"]]
    out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    sys.exit(battle_core.run(drive, steps, report_out=out, tag="perf"))


if __name__ == "__main__":
    main()
