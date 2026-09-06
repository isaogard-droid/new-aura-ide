#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Spike: мульти-агентный оркестратор (паттерн orchestrator-worker, Anthropic).

Планер (сильная модель) разбивает задачу на подзадачи (JSON-план, hard cap),
воркеры выполняют их ПАРАЛЛЕЛЬНО (изолированные сессии, разные модели по
желанию), синтезатор (та же сильная модель) собирает результаты в один отчёт.

Фазы: PLAN (планировщик) → EXECUTE (воркеры, fan-out) → SYNTHESIS (сводка).

Запуск:
    python3 scripts/tools/judge/multiorch.py --task "проанализируй X и предложи Y" --out /tmp/orch.md
    python3 scripts/tools/judge/multiorch.py --task "..." --worker-model opencode/mimo-v2.5-free --cap 4

Переиспользует бэкенды multimodel_judge (opencode/reasonix/codex/...).
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import shutil

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import multimodel_judge as mj  # noqa: E402 - наш паттерн импорта (scripts/)

PLANNER_PROMPT = """Ты — планировщик мульти-агентной системы. Разбей задачу на
ПОДЗАДАЧИ, которые воркеры выполнят параллельно и независимо.

Правила:
- От 2 до {cap} подзадач (не больше {cap} — жёсткий лимит).
- Каждая подзадача должна быть самодостаточной: воркеру не нужны результаты
  других воркеров.
- Для каждой: id (число), title (коротко), task (полная инструкция воркеру:
  что сделать, в каком виде вернуть результат).
- Воркеры read-only: пусть анализируют, ищут, читают, считают — НЕ правят файлы.

Верни ТОЛЬКО JSON, без пояснений:
{{"tasks": [{{"id": 1, "title": "...", "task": "..."}}]}}

Исходная задача: {task}"""

WORKER_PROMPT = """Ты — воркер в мульти-агентной системе. Выполни свою подзадачу
независимо от других воркеров. Только читай и анализируй — НЕ редактируй файлы
и НЕ запускай изменяющих команд.

Подзадача {task_id}: {title}

Инструкция: {task}

Верни компактный результат (текстом, без воды). Что нашёл — с фактами и
ссылками на файлы/строки, где это уместно. Если подзадача невыполнима —
скажи прямо, что именно мешает."""

SYNTHESIS_PROMPT = """Ты — синтезатор мульти-агентной системы. Воркеры выполнили
подзадачи ПАРАЛЛЕЛЬНО и независимо. Собери их результаты в ОДИН итоговый отчёт
по исходной задаче.

Исходная задача: {task}

Правила:
1) Итог — первым (главный вывод по задаче).
2) Затем результаты по подзадачам (компактно, ключевое).
3) Противоречия между воркерами — укажи явно и предложи, как их разрешить.
4) Пробелы — чего воркеры не покрыли и что стоит сделать дальше.

Пиши от своего имени, не упоминай "воркер 1/2/3". Без воды.

## Результаты воркеров

{results}"""

DEFAULT_PLANNER = "deepseek/deepseek-v4-pro"
DEFAULT_WORKER = "opencode/mimo-v2.5-free"
DEFAULT_CAP = 5


def parse_plan(text: str, cap: int) -> tuple[list[dict], bool]:
    """Разобрать JSON-план планировщика: {"tasks": [...]}.

    Возвращает (tasks, ok). ok=False — план не распарсился: оркестрация
    останавливается с диагнозом. Валидация: tasks — список, id/title/task
    непустые, количество не превышает cap. Скобки внутри инструкций
    (например, 'верни {"issues": [...]}') не ломают парсинг.
    """
    obj = mj.extract_json_object(text)
    if obj is None:
        return [], False
    try:
        data = json.loads(obj)
    except json.JSONDecodeError:
        return [], False
    raw = data.get("tasks")
    if not isinstance(raw, list) or not raw:
        return [], False
    tasks = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        task = str(item.get("task", "")).strip()
        if not title or not task:
            continue
        tasks.append({
            "id": item.get("id", len(tasks) + 1),
            "title": title,
            "task": task,
        })
    if not tasks:
        return [], False
    return tasks[:cap], True


def run_worker(model: str, prompt: str, cwd: str, timeout: int,
               config: str, harness: str) -> str:
    """Один воркер через бэкенд multimodel_judge (с защитой от сбоев)."""
    try:
        return mj.run_model(model, prompt, cwd, timeout, config, harness)
    except Exception as exc:  # noqa: BLE001 - сбой одного воркера не роняет панель
        return f"ОШИБКА ВЫЗОВА: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", required=True, help="исходная задача для оркестрации")
    ap.add_argument("--planner", default=DEFAULT_PLANNER, help="модель-планировщик/синтезатор")
    ap.add_argument("--worker-model", default=DEFAULT_WORKER, help="модель воркеров")
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP, help="максимум подзадач (hard cap)")
    ap.add_argument("--harness", default=mj.DEFAULT_HARNESS,
                    choices=list(mj.SUPPORTED_HARNESSES), help="бэкенд запуска")
    ap.add_argument("--out", help="файл для полного протокола (md)")
    ap.add_argument("--timeout", type=int, default=240, help="таймаут на один вызов, секунд")
    args = ap.parse_args()

    if args.cap < 2 or args.cap > 10:
        ap.error("--cap от 2 до 10")

    workdir = tempfile.mkdtemp(prefix="multiorch-")
    t0 = time.time()
    try:
        config = os.path.join(workdir, "opencode.json")
        with open(config, "w", encoding="utf-8") as f:
            json.dump({"$schema": "https://opencode.ai/config.json", "mcp": {}}, f)

        # Фаза 1: PLAN — планировщик разбивает задачу.
        plan_prompt = PLANNER_PROMPT.format(cap=args.cap, task=args.task)
        plan_text = run_worker(args.planner, plan_prompt, workdir,
                               args.timeout, config, args.harness)
        tasks, plan_ok = parse_plan(plan_text, args.cap)
        if not plan_ok:
            print("ОШИБКА: планировщик не выдал валидный JSON-план:")
            print(plan_text[:1000])
            return 2
        plan_done = time.time()

        # Фаза 2: EXECUTE — воркеры параллельно (fan-out, изоляция сессий).
        results: dict[int, str] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as pool:
            futures = {}
            for t in tasks:
                prompt = WORKER_PROMPT.format(task_id=t["id"], title=t["title"], task=t["task"])
                futures[pool.submit(run_worker, args.worker_model, prompt, workdir,
                                    args.timeout, config, args.harness)] = t["id"]
            for fut in concurrent.futures.as_completed(futures):
                results[futures[fut]] = fut.result()
        workers_done = time.time()

        # Фаза 3: SYNTHESIS — синтезатор собирает итоговый отчёт.
        results_block = "\n\n".join(
            f"### Подзадача {t['id']}: {t['title']}\n{results.get(t['id'], '(нет результата)')}"
            for t in tasks)
        synth_prompt = SYNTHESIS_PROMPT.format(task=args.task, results=results_block)
        final = run_worker(args.planner, synth_prompt, workdir,
                           args.timeout, config, args.harness)
        t1 = time.time()

        protocol = "\n".join([
            "# Мульти-агентная оркестрация (orchestrator-worker)",
            "",
            f"- Задача: {args.task}",
            f"- Планировщик/синтез: {args.planner}; воркеры: {args.worker_model} x{len(tasks)}",
            f"- Харнес: {args.harness}",
            f"- План: {plan_done - t0:.0f}с, воркеры: {workers_done - plan_done:.0f}с, "
            f"синтез: {t1 - workers_done:.0f}с, всего: {t1 - t0:.0f}с",
            "",
            "## Итоговый отчёт",
            "",
            final,
            "",
            "---",
            "## План",
            "",
            plan_text,
            "",
            "---",
            "## Результаты воркеров",
            "",
            results_block,
            "",
        ])
        if args.out:
            pathlib.Path(args.out).write_text(protocol, encoding="utf-8")
            print(f"[ok] протокол: {args.out}")
        print(final)
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
