#!/usr/bin/env python3
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Trigger-rate eval для скиллов AGGG2.0 (методика agentskills.io).

Замеряет, насколько description скилла заставляет агента загрузить его
(trigger rate). Детект: `opencode run --format json`, событие tool_use
с tool=skill и input.name == целевой скилл.

ВАЖНО (проверено замером 08.2026, research.db id=302): по умолчанию скрипт
создаёт ЧИСТЫЙ временный конфиг (без MCP и без build-промпта) — замеряется
только сила description, а не гейты прошивки (build.txt/core.txt
«СКИЛЛЫ НА КАКДУЮ ЗАДАЧУ»). Реальный триггер в работе выше: description —
нижняя граница, гейты — гарантия (находка id=293).

Перед прогоном — smoke health-check модели (урок research.db id=591):
один короткий `opencode run` с таймаутом 60с (--health-timeout). Мёртвая/
зависшая модель ловится ДО того, как --parallel воркеров сожгут --timeout
(300с) каждый.

Методика (agentskills.io/skill-creation/optimizing-descriptions):
- ~20 запросов на скилл: 8-10 should-trigger + 8-10 should-not (near-miss);
- 3 прогона на запрос (ранний стоп при ясном результате 2/2);
- порог trigger rate 0.5; should-not должны быть near-miss (похожие слова,
  но другая задача), а не «какая погода»;
- не добавлять конкретные слова из failed-запросов в description = overfitting.

Запуск:
    python3 scripts/eval/eval_skill_triggers.py --queries queries.json
    python3 scripts/eval/eval_skill_triggers.py --queries q.json --runs 3 --parallel 4
    python3 scripts/eval/eval_skill_triggers.py --queries q.json --model deepseek/deepseek-v4-flash
    python3 scripts/eval/eval_skill_triggers.py --queries q.json --config real.json  # с прошивкой/MCP
    python3 scripts/eval/eval_skill_triggers.py --queries q.json --out results.jsonl

Формат queries.json (JSON-массив):
    [{"skill": "nodumb", "should": true,  "query": "..."},
     {"skill": "nodumb", "should": false, "query": "..."}]

Вывод: построчно прогресс, в конце сводка по скиллам (should / should-not
в процентах). Результаты — JSONL в --out.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"

HEALTH_TIMEOUT_DEFAULT = 60  # smoke health-check модели перед прогоном (урок 591)


def make_clean_config(workdir: str) -> str:
    """Чистый конфиг opencode (без MCP) — замер description без прошивки.

    Возвращает путь к созданному opencode.json во временной папке.
    """
    cfg = os.path.join(workdir, "opencode.json")
    with open(cfg, "w", encoding="utf-8") as f:
        json.dump({"$schema": "https://opencode.ai/config.json", "mcp": {}}, f)
    return cfg


def health_check(model: str, config: str, workdir: str,
                 timeout: int = HEALTH_TIMEOUT_DEFAULT) -> bool:
    """Smoke-проверка модели ПЕРЕД прогоном eval (урок research.db id=591).

    Один короткий `opencode run` с тривиальным промптом и малым таймаутом
    (60с по умолчанию). Ловит мёртвую/зависшую модель ДО того, как
    --parallel воркеров сожгут --timeout (300с) каждый. Актуально после
    автообновления opencode: run стал серверным и может виснуть после
    ответа (ensureTitle без таймаута — GitHub anomalyco/opencode#3213/#5888).
    Возвращает True, если модель ответила (rc=0 и непустой stdout)."""
    cmd = ["opencode", "run", "--format", "json", "--model", model,
           "ответь одним словом: ок"]
    env = {**os.environ, "OPENCODE_CONFIG": config}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, cwd=workdir, env=env,
                              check=False)
    except subprocess.TimeoutExpired:
        print(f"FAIL: health-check модели {model} не ответил за {timeout}с — "
              f"модель зависла (паттерн 591/719/738), eval не запускаю",
              file=sys.stderr)
        return False
    out = proc.stdout or ""
    if proc.returncode != 0:
        print(f"FAIL: health-check модели {model} вернул rc={proc.returncode}: "
              f"{out[:200]}", file=sys.stderr)
        return False
    if not out.strip():
        print(f"FAIL: health-check модели {model} — пустой вывод",
              file=sys.stderr)
        return False
    print(f"OK: health-check модели {model} прошёл ({len(out)} байт)")
    return True


def run_once(query: str, skill: str, tools: list, model: str, config: str,
             workdir: str, timeout: int) -> bool:
    """Один запуск opencode: True, если скилл загружен (tool_use skill)
    ИЛИ использован хотя бы один из `tools` (поведенческий триггер:
    модель выполнила миссию скилла через MCP-тулы, не грузя сам скилл)."""
    cmd = ["opencode", "run", "--format", "json", "--model", model, query]
    env = {**os.environ, "OPENCODE_CONFIG": config}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, cwd=workdir, env=env,
                              check=False)
        out = proc.stdout or ""
    except subprocess.TimeoutExpired:
        return False
    for line in out.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") != "tool_use":
            continue
        part = ev.get("part", {})
        if (part.get("tool") == "skill"
                and part.get("state", {}).get("input", {}).get("name") == skill):
            return True
        if tools and part.get("tool") in tools:
            return True
    return False


def eval_query(item: dict, model: str, config: str, workdir: str,
               max_runs: int, timeout: int) -> dict:
    """До max_runs прогонов с ранним стопом при ясном результате."""
    skill = item["skill"]
    should = item["should"]
    query = item["query"]
    tools = item.get("tools", [])
    heldout = bool(item.get("heldout"))
    triggers = 0
    runs = 0
    for _ in range(max_runs):
        runs += 1
        if run_once(query, skill, tools, model, config, workdir, timeout):
            triggers += 1
        if runs == 2:
            if should and triggers == 2:
                break
            if not should and triggers == 0:
                break
    rate = triggers / runs
    return {
        "skill": skill,
        "should": should,
        "query": query,
        "heldout": heldout,
        "triggers": triggers,
        "runs": runs,
        "rate": rate,
        "pass": (rate >= 0.5) == should,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queries", required=True,
                    help="JSON-массив запросов [{'skill','should','query'}]")
    ap.add_argument("--out", default="docs/eval/skill_eval_results.jsonl",
                    help="куда писать результаты (JSONL)")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="модель opencode (provider/model)")
    ap.add_argument("--runs", type=int, default=3,
                    help="максимум прогонов на запрос (по умолчанию 3)")
    ap.add_argument("--parallel", type=int, default=4,
                    help="параллельных запусков opencode")
    ap.add_argument("--timeout", type=int, default=300,
                    help="таймаут одного запуска opencode, сек")
    ap.add_argument("--health-timeout", type=int, default=HEALTH_TIMEOUT_DEFAULT,
                    help="таймаут smoke health-check модели перед прогоном, "
                         "сек (урок 591)")
    ap.add_argument("--config",
                    help="свой конфиг opencode (по умолчанию чистый временный)")
    ap.add_argument("--keep-workdir", action="store_true",
                    help="не удалять временную папку после прогона")
    ap.add_argument("--min-should", type=float, default=0.8,
                    help="мин. доля срабатываний на позитивах (recall); ниже — exit 1")
    ap.add_argument("--min-not", type=float, default=0.7,
                    help="мин. доля НЕсрабатываний на негативах (специфичность); ниже — exit 1")
    ap.add_argument("--heldout", action="store_true",
                    help="прогнать ТОЛЬКО heldout-запросы (финальная проверка "
                         "без overfitting; train-запросы используются при "
                         "итерациях по description)")
    args = ap.parse_args()

    with open(args.queries, encoding="utf-8") as f:
        items = json.load(f)
    if not items:
        print("пусто: нет запросов", file=sys.stderr)
        return 2
    if args.heldout:
        items = [it for it in items if it.get("heldout")]
        if not items:
            print("пусто: нет heldout-запросов в файле", file=sys.stderr)
            return 2

    workdir = tempfile.mkdtemp(prefix="skill-eval-")
    config = args.config or make_clean_config(workdir)
    try:
        if not health_check(args.model, config, workdir, args.health_timeout):
            return 1
        print(f"всего запросов: {len(items)}, параллельно: {args.parallel}, "
              f"модель: {args.model}", flush=True)
        results = []
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futs = {pool.submit(eval_query, it, args.model, config, workdir,
                                args.runs, args.timeout): it for it in items}
            for done, fut in enumerate(as_completed(futs), start=1):
                res = fut.result()
                results.append(res)
                status = "OK " if res["pass"] else "FAIL"
                mark = "H" if res.get("heldout") else "t"
                print(f"[{done}/{len(items)}] {status} [{mark}] "
                      f"{res['skill']:24s} "
                      f"should={res['should']} rate={res['rate']:.2f} "
                      f"({res['triggers']}/{res['runs']}) | "
                      f"{res['query'][:60]}", flush=True)

        results.sort(key=lambda r: (r["skill"], r["should"], r["query"]))
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in results)

        print("\n=== СВОДКА ===")
        by_skill = {}
        for r in results:
            by_skill.setdefault(r["skill"], {"should": 0, "should_pass": 0,
                                             "not": 0, "not_pass": 0})
            b = by_skill[r["skill"]]
            if r["should"]:
                b["should"] += 1
                b["should_pass"] += r["pass"]
            else:
                b["not"] += 1
                b["not_pass"] += r["pass"]
        for skill, b in sorted(by_skill.items()):
            sr = b["should_pass"] / b["should"] if b["should"] else 0
            nr = b["not_pass"] / b["not"] if b["not"] else 0
            print(f"{skill:24s} should {sr:.0%} ({b['should_pass']}/{b['should']})  "
                  f"should-not {nr:.0%} ({b['not_pass']}/{b['not']})")
        ho = [r for r in results if r.get("heldout")]
        if ho:
            h_should = sum(1 for r in ho if r["should"])
            h_pass = sum(1 for r in ho if r["should"] and r["pass"])
            h_not = sum(1 for r in ho if not r["should"])
            h_notpass = sum(1 for r in ho if not r["should"] and r["pass"])
            print(f"\n--- HELD-OUT ({len(ho)} запросов, не трогать при "
                  f"оптимизации) ---")
            print(f"should {h_pass}/{h_should}  should-not {h_notpass}/{h_not}")
        print(f"\nвремя: {time.time() - t0:.0f}с, результаты: {args.out}")

        # CI-гейт: пороги на срабатывания (recall) и специфичность (should-not)
        total_should = sum(b["should"] for b in by_skill.values()) or 1
        total_should_pass = sum(b["should_pass"] for b in by_skill.values())
        total_not_raw = sum(b["not"] for b in by_skill.values())
        total_not = total_not_raw or 1
        total_not_pass = sum(b["not_pass"] for b in by_skill.values())
        recall = total_should_pass / total_should
        spec = total_not_pass / total_not
        print(f"\nИТОГ: recall={recall:.0%} (порог {args.min_should:.0%}), "
              f"специфичность={spec:.0%} (порог {args.min_not:.0%})")
        if not total_not_raw:
            print("негативов в наборе нет — специфичность не измеряется, "
                  "гейт по ней не применяется")
        if recall < args.min_should or (total_not_raw and spec < args.min_not):
            print("FAIL: триггер-гейт не пройден — править description скиллов",
                  file=sys.stderr)
            return 1
        return 0
    finally:
        if not args.keep_workdir:
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
