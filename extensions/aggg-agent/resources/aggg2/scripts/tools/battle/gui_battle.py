#!/usr/bin/env python3
"""Универсальный раннер GUI-батл-тестов (скилл gui-battle-test).
Тонкая обёртка над battle_core (общее ядро gui/cli/api).

Конфиг — Python-модуль с переменной CONFIG (dict):
    CONFIG = {
        "launch": callable() -> None,      # блокирующий запуск приложения
        "snapshot": callable() -> dict,    # снимок состояния ДО
        "restore": callable(snap) -> None, # откат в finally
        "eval_js": callable(code) -> any,  # драйвер: выполнить JS/действие
        "steps": [
            {"name": "…", "action": "js или callable", "wait": "js или callable",
             "want": None | callable(value), "timeout": 15, "retries": 0},
            …
        ],
        "pre": callable() -> None | None,  # env перед запуском
    }

Условия (condition-based waiting, паттерн obra/superpowers): wait
возвращает значение; want — предикат Python (None = truthy). Поллинг с
прогрессией интервала. Никаких фиксированных sleep.

Запуск: python3 scripts/tools/gui_battle.py <config_module.py> [--json отчёт.json]
Вывод: построчно по шагам (сразу, для tail -f), итог X/Y %, время, отказы.
Код выхода: 0 — 100%, 1 — есть отказы.
"""
import importlib.util
import sys
import threading

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import battle_core  # noqa: E402

RESULTS = battle_core.RESULTS
poll = battle_core.poll


def run(config, report_out=None):
    if callable(config.get("pre")):
        config["pre"]()
    if callable(config.get("launch")):
        threading.Thread(target=config["launch"], daemon=True).start()
    return battle_core.run(
        config["eval_js"], config["steps"],
        snapshot=config.get("snapshot"),
        restore=config.get("restore"),
        boot_wait=config.get("boot_wait", 3.0),
        report_out=report_out, tag="gui")


def load_config(path):
    spec = importlib.util.spec_from_file_location("battle_config", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cfg = getattr(mod, "CONFIG", None)
    if not isinstance(cfg, dict):
        raise SystemExit(f"в {path} нет CONFIG (dict)")
    return cfg


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cfg = load_config(sys.argv[1])
    out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    sys.exit(run(cfg, report_out=out))


if __name__ == "__main__":
    main()
