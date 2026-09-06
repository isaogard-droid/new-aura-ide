#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Spike: quality-eval скиллов AGGG2.0 (второй слой — качество, не триггер).

Методика: парный прогон «со скиллом» vs «без скилла» (методика OpenAI
eval-skills / agent-skills-eval / skillcheck): одна задача, два прогона,
результаты сравниваются по рубрике. Скилл скрывается временным
переименованием каталога в зеркале opencode (~/.config/opencode/skills/).

Запуск:
    python3 quality_eval.py --skill changelog-discipline --query "..." --out out.md
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import tempfile
import time

SKILLS_DIR = pathlib.Path.home() / ".config/opencode/skills"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"


def run(query: str, config: str, workdir: str, timeout: int = 120,
           model: str = DEFAULT_MODEL) -> str:
    """Один прогон opencode; возвращает текст ответа."""
    cmd = ["opencode", "run", "--format", "json", "--model", model, query]
    env = {**os.environ, "OPENCODE_CONFIG": config}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, cwd=workdir, env=env, check=False)
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    texts = []
    for line in (proc.stdout or "").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "text" and ev.get("part", {}).get("type") == "text":
            texts.append(ev["part"].get("text", ""))
    return "\n".join(texts) or "(пусто)"


def hide_skill(name: str) -> None:
    """Временно скрыть скилл (переименовать каталог в зеркале opencode)."""
    src = SKILLS_DIR / name
    dst = SKILLS_DIR / f".{name}.hidden"
    if src.exists() and not dst.exists():
        shutil.move(str(src), str(dst))


def show_skill(name: str) -> None:
    src = SKILLS_DIR / f".{name}.hidden"
    dst = SKILLS_DIR / name
    if src.exists() and not dst.exists():
        shutil.move(str(src), str(dst))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skill", required=True)
    ap.add_argument("--query", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="модель opencode (provider/model)")
    args = ap.parse_args()

    workdir = tempfile.mkdtemp(prefix="quality-eval-")
    config = os.path.join(workdir, "opencode.json")
    with open(config, "w", encoding="utf-8") as f:
        json.dump({"$schema": "https://opencode.ai/config.json", "mcp": {}}, f)

    try:
        # Прогон 1: со скиллом
        res_with = run(args.query, config, workdir, model=args.model)
        # Прогон 2: без скилла
        hide_skill(args.skill)
        time.sleep(1)
        try:
            res_without = run(args.query, config, workdir, model=args.model)
        finally:
            show_skill(args.skill)

        out = pathlib.Path(args.out)
        out.write_text(
            f"# Quality-eval: {args.skill}\n\n"
            f"Запрос: {args.query}\n\n"
            f"## С скиллом\n\n{res_with}\n\n"
            f"## Без скилла\n\n{res_without}\n",
            encoding="utf-8",
        )
        print(f"готово: {args.out}")
        return 0
    finally:
        import shutil as _s
        _s.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
