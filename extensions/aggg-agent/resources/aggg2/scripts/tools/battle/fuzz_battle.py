#!/usr/bin/env python3
"""Фазз-батл: property-based на Hypothesis — контрпримеры вместо примеров.

Конфиг — Python-модуль с CONFIG:
    CONFIG = {
        "targets": [
            {"name": "…", "fn": callable, "strategy": st.text(),
             "prop": callable(value) -> bool,   # True = свойство ВЫПОЛНЕНО
             "n": 300},
        ],
    }

Паттерн (Codex CLI/round-trip): prop — инвариант (round-trip,
идемпотентность, «не падает кроме ValueError»). Поиск контрпримера —
hypothesis.find: нашёл → FAIL с контрпримером (shrink'нутым), не нашёл
за n примеров → PASS. Примеры, которые ты придумал, не ловят того, чего
не придумал (property-based).
"""
import importlib.util
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import battle_core  # noqa: E402
from hypothesis import HealthCheck, find, settings
from hypothesis.errors import NoSuchExample


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    spec = importlib.util.spec_from_file_location("fuzz_config", sys.argv[1])
    cfg_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg_mod)
    cfg = getattr(cfg_mod, "CONFIG", None)
    if not isinstance(cfg, dict):
        raise SystemExit(f"в {sys.argv[1]} нет CONFIG (dict)")

    results = []

    def drive(t):
        if t == "__last__":
            return results[-1] if results else None
        prop = t["prop"]
        try:
            bad = find(t["strategy"],
                       lambda v: not prop(v),
                       settings=settings(max_examples=t.get("n", 300),
                                         suppress_health_check=HealthCheck.all(),
                                         database=None))
            results.append(f"КОНТРПРИМЕР: {bad!r}")
        except NoSuchExample:
            results.append("ok")
        return results[-1]

    steps = [{"name": t["name"], "action": t, "wait": "__last__",
              "want": lambda v: v == "ok", "timeout": 60}
             for t in cfg["targets"]]
    out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    sys.exit(battle_core.run(drive, steps, report_out=out, tag="fuzz"))


if __name__ == "__main__":
    main()
