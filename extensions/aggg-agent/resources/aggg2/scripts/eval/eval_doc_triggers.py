#!/usr/bin/env python3
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Trigger-rate eval для КАНОН-ДОКОВ AGGG2.0 (методика agentevals.io skill-trigger).

Замеряет, открывает ли агент нужный канон-док (Read с путём дока) или грузит
скилл-близнец (skill tool) при задаче соответствующего типа. Детект: события
tool_use `opencode run --format json`.

По умолчанию — РЕАЛЬНЫЙ конфиг opencode (~/.config/opencode): замеряется
ПОЛНАЯ система (прошивка core.txt п.8 «КАНОН-ДОКИ ПО ТИПУ ЗАДАЧИ» + скиллы).
--clean — чистый временный конфиг (нижняя граница: сила description скиллов
без прошивки; доки в нём недоступны, поэтому триггер = только скилл).

Запуск:
    python3 scripts/eval/eval_doc_triggers.py --queries scripts/eval/eval_doc_queries.json
    python3 scripts/eval/eval_doc_triggers.py --queries q.json --runs 2 --parallel 4

Формат queries.json (JSON-массив):
    [{"doc": "FABLE-JUDGE.md", "skills": ["fable-judge"], "should": true,
      "query": "..."}]

Вывод: построчно прогресс, в конце сводка по докам (should / should-not
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


def make_clean_config(workdir: str) -> str:
    """Чистый конфиг opencode (без MCP и прошивки) — нижняя граница."""
    cfg = os.path.join(workdir, "opencode.json")
    with open(cfg, "w", encoding="utf-8") as f:
        json.dump({"$schema": "https://opencode.ai/config.json", "mcp": {}}, f)
    return cfg


def _detect_doc(out: str, doc: str, skills: list) -> bool:
    """True, если агент прочитал док (Read по пути) или загрузил скилл-близнец.

    Грабля (13.08.2026): opencode шлёт ключ filePath (camelCase), не
    file_path — смотреть оба; попытка Read (status=error) тоже считается
    триггером (агент знал, какой док нужен).
    """
    for line in out.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") != "tool_use":
            continue
        part = ev.get("part", {})
        tool = part.get("tool")
        state = part.get("state", {}) or {}
        inp = state.get("input", {}) or {}
        if tool == "read":
            fp = str(inp.get("file_path") or inp.get("filePath") or "")
            if doc in fp:
                return True
        if tool == "skill":
            name = str(inp.get("name") or "")
            if name in skills:
                return True
    return False


def run_once(query: str, doc: str, skills: list, model: str, config,
             workdir: str, timeout: int) -> bool:
    """Один запуск opencode: True, если док/скилл сработал.

    Грабля (13.08.2026): тяжёлые цепочки (skill → база → Camoufox → read)
    не укладывались в 150с — TimeoutExpired засчитывался фейлом без разбора.
    При таймауте разбираем частичный вывод: если триггер уже был в потоке —
    прогон засчитан.
    """
    cmd = ["opencode", "run", "--format", "json", "--model", model, query]
    env = dict(os.environ)
    if config:
        env["OPENCODE_CONFIG"] = config
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, cwd=workdir, env=env,
                              check=False)
        out = proc.stdout or ""
    except subprocess.TimeoutExpired as exc:
        out = exc.output or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
    return _detect_doc(out, doc, skills)


def eval_query(item: dict, model: str, config, workdir: str,
               max_runs: int, timeout: int) -> dict:
    """До max_runs прогонов с ранним стопом при ясном результате."""
    doc = item["doc"]
    skills = item.get("skills") or []
    should = item["should"]
    query = item["query"]
    triggers = 0
    runs = 0
    for _ in range(max_runs):
        runs += 1
        if run_once(query, doc, skills, model, config, workdir, timeout):
            triggers += 1
        if runs == 2:
            if should and triggers == 2:
                break
            if not should and triggers == 0:
                break
    rate = triggers / runs
    return {
        "doc": doc,
        "should": should,
        "query": query,
        "triggers": triggers,
        "runs": runs,
        "rate": rate,
        "pass": (rate >= 0.5) == should,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queries", required=True,
                    help="JSON-массив запросов [{'doc','skills','should','query'}]")
    ap.add_argument("--out", default="docs/eval/doc_eval_results.jsonl",
                    help="куда писать результаты (JSONL)")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help="модель opencode (provider/model)")
    ap.add_argument("--runs", type=int, default=2,
                    help="максимум прогонов на запрос (по умолчанию 2)")
    ap.add_argument("--parallel", type=int, default=4,
                    help="параллельных запусков opencode")
    ap.add_argument("--timeout", type=int, default=300,
                    help="таймаут одного запуска opencode, сек")
    ap.add_argument("--clean", action="store_true",
                    help="чистый конфиг без прошивки/MCP (нижняя граница)")
    ap.add_argument("--config",
                    help="свой конфиг opencode (по умолчанию: реальный)")
    ap.add_argument("--keep-workdir", action="store_true",
                    help="не удалять временную папку после прогона")
    ap.add_argument("--workdir",
                    help="рабочий каталог прогонов вместо временного — для CI:"
                         " корень репо, чтобы канон-доки были видны агенту")
    ap.add_argument("--min-should", type=float, default=0.8,
                    help="мин. доля срабатываний на позитивах (recall); ниже — exit 1")
    ap.add_argument("--min-not", type=float, default=0.7,
                    help="мин. доля НЕсрабатываний на негативах; ниже — exit 1")
    args = ap.parse_args()

    with open(args.queries, encoding="utf-8") as f:
        items = json.load(f)
    if not items:
        print("пусто: нет запросов", file=sys.stderr)
        return 2

    workdir = args.workdir or tempfile.mkdtemp(prefix="doc-eval-")
    own_workdir = args.workdir is None
    config = args.config if args.config is not None else (
        make_clean_config(workdir) if args.clean else None)
    try:
        mode = "чистый конфиг (без прошивки)" if (args.clean or args.config) \
            else "реальный конфиг (с прошивкой)"
        print(f"всего запросов: {len(items)}, параллельно: {args.parallel}, "
              f"модель: {args.model}, режим: {mode}", flush=True)
        results = []
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futs = {pool.submit(eval_query, it, args.model, config, workdir,
                                args.runs, args.timeout): it for it in items}
            for done, fut in enumerate(as_completed(futs), start=1):
                res = fut.result()
                results.append(res)
                status = "OK " if res["pass"] else "FAIL"
                print(f"[{done}/{len(items)}] {status} {res['doc']:24s} "
                      f"should={res['should']} rate={res['rate']:.2f} "
                      f"({res['triggers']}/{res['runs']}) | "
                      f"{res['query'][:60]}", flush=True)

        results.sort(key=lambda r: (r["doc"], r["should"], r["query"]))
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in results)

        print("\n=== СВОДКА ===")
        by_doc = {}
        for r in results:
            by_doc.setdefault(r["doc"], {"should": 0, "should_pass": 0,
                                         "not": 0, "not_pass": 0})
            b = by_doc[r["doc"]]
            if r["should"]:
                b["should"] += 1
                b["should_pass"] += r["pass"]
            else:
                b["not"] += 1
                b["not_pass"] += r["pass"]
        for doc, b in sorted(by_doc.items()):
            sr = b["should_pass"] / b["should"] if b["should"] else 0
            nr = b["not_pass"] / b["not"] if b["not"] else 0
            print(f"{doc:24s} should {sr:.0%} ({b['should_pass']}/{b['should']})  "
                  f"should-not {nr:.0%} ({b['not_pass']}/{b['not']})")
        print(f"\nвремя: {time.time() - t0:.0f}с, результаты: {args.out}")

        total_should = sum(b["should"] for b in by_doc.values()) or 1
        total_should_pass = sum(b["should_pass"] for b in by_doc.values())
        total_not_raw = sum(b["not"] for b in by_doc.values())
        total_not = total_not_raw or 1
        total_not_pass = sum(b["not_pass"] for b in by_doc.values())
        recall = total_should_pass / total_should
        spec = total_not_pass / total_not
        print(f"\nИТОГ: recall={recall:.0%} (порог {args.min_should:.0%}), "
              f"специфичность={spec:.0%} (порог {args.min_not:.0%})")
        if not total_not_raw:
            print("негативов в наборе нет — специфичность не измеряется, "
                  "гейт по ней не применяется")
        if recall < args.min_should or (total_not_raw and spec < args.min_not):
            print("FAIL: триггер-гейт не пройден — усилить п.8 ядра/описания",
                  file=sys.stderr)
            return 1
        return 0
    finally:
        if own_workdir and not args.keep_workdir:
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
