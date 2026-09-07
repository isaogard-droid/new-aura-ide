#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
"""MCP для GUI-батл-тестов: запуск без блокировки + прогресс по логу.

Обёртка над scripts/tools/gui_battle.py: battle_run стартует прогон в
фоне и СРАЗУ возвращает путь лога (никаких «завис на 400 секунд»),
battle_status отдаёт прогресс (счётчик шагов, последние строки, итог).
Паттерн Claude: MCP = доступ, скилл gui-battle-test = как пользоваться.
Тулы синхронные — по опыту camoufox, async-тулы в FastMCP дедлочат.
"""
import os
import pathlib
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from mcp.server.fastmcp import FastMCP

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "tools" / "battle" / "gui_battle.py"
SURFACES = {"gui": RUNNER,
            "cli": ROOT / "scripts" / "tools" / "battle" / "cli_battle.py",
            "api": ROOT / "scripts" / "tools" / "battle" / "api_battle.py",
            "web": ROOT / "scripts" / "tools" / "battle" / "web_battle.py",
            "perf": ROOT / "scripts" / "tools" / "battle" / "perf_battle.py",
            "fuzz": ROOT / "scripts" / "tools" / "battle" / "fuzz_battle.py",
            "visual": ROOT / "scripts" / "tools" / "battle" / "visual_battle.py"}
LOGDIR = pathlib.Path(tempfile.gettempdir()) / "opencode" / "gui-battle"
LOGDIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("gui-battle")


def _spawn(config_path, surface):
    config_path = str(pathlib.Path(config_path).expanduser().resolve())
    if not os.path.isfile(config_path):
        return {"ok": False, "error": f"конфига нет: {config_path}"}
    runner = SURFACES.get(surface, RUNNER)
    name = f"{surface}-{pathlib.Path(config_path).stem}"
    log_path = LOGDIR / f"{name}.log"
    report_path = LOGDIR / f"{name}.json"
    cmd = [sys.executable, str(runner), config_path, "--json", str(report_path)]
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                cwd=str(ROOT))
    return {"ok": True, "pid": proc.pid, "surface": surface,
            "log_path": str(log_path), "report_path": str(report_path),
            "hint": "прогресс: battle_status(log_path); итог — в report_path"}


@mcp.tool()
def battle_run(config_path: str, surface: str = "gui") -> dict:
    """Запустить батл-тест по конфигу в фоне. НЕ блокирует: возвращает
    сразу log_path/report_path/pid; прогресс — battle_status.
    surface: gui | cli | api (какой раннер)."""
    return _spawn(config_path, surface)


@mcp.tool()
def battle_status(log_path: str) -> dict:
    """Прогресс прогона по логу: счётчик шагов, итог (если есть), хвост.
    НЕ блокирует: читает файл и сразу отвечает."""
    log_path = str(pathlib.Path(log_path).expanduser())
    if not os.path.isfile(log_path):
        return {"ok": False, "error": f"лога нет: {log_path}"}
    with open(log_path, encoding="utf-8", errors="replace") as log:
        lines = log.read().splitlines()
    ok_n = sum(1 for line in lines if line.startswith("✓"))
    bad_n = sum(1 for line in lines if line.startswith("✗"))
    itog = next((line for line in reversed(lines) if line.startswith("ИТОГ")), None)
    done = itog is not None
    return {"ok": True, "done": done, "steps_ok": ok_n, "steps_bad": bad_n,
            "итог": itog, "tail": lines[-6:]}


if __name__ == "__main__":
    mcp.run()

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
