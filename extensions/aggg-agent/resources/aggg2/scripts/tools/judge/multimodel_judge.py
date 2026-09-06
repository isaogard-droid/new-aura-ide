#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Spike: мультимодельное судейство (паттерн Rejudge, индустрия: Multiagent
Debate / Mixture-of-Agents / LLM-as-a-Judge).

Несколько моделей-ревьюеров независимо (изолированные сессии opencode run)
анализируют один объект, судья получает ТОЛЬКО их отчёты и сводит в один
итоговый отчёт, разрешая расхождения. Реализация на нашем стеке: opencode
CLI с --model (как quality_eval.py), без внешних инструментов.

Запуск:
    python3 scripts/tools/judge/multimodel_judge.py --file scripts/_compat.py \
        --query "найди ошибки, риски и уязвимости" \
        --reviewers "opencode/mimo-v2.5-free,opencode/hy3-free,opencode/nemotron-3-ultra-free" \
        --judge "deepseek/deepseek-v4-pro" --out /tmp/judge-out.md

    git diff | python3 scripts/tools/judge/multimodel_judge.py --diff - --query "review this change"

Режимы объекта: --file <путь> (ревьюеры сами читают файл), --diff <путь|'-'>
(содержимое диффа передаётся в промпт, '-' = stdin).

Карта после механической резки god-файла (код перенесён дословно, поведение
не менялось; импортёры модуля видят те же имена — re-export ниже):
    multimodel_judge_prompts.py — REVIEWER_PROMPT, JUDGE_QUERY_PROMPT,
                                 REVIEWER_FOLLOWUP_PROMPT, JUDGE_PROMPT
    multimodel_judge_models.py — CONFIG_NAME, GLOBAL_CONFIG,
                                 SUPPORTED_HARNESSES, DEFAULT_HARNESS,
                                 DEFAULT_REVIEWERS, DEFAULT_JUDGE,
                                 DEFAULT_TIMEOUT, load_config_file,
                                 candidates_from, resolve_models,
                                 resolve_harness
    multimodel_judge_parse.py — extract_json_object, parse_judge_questions
    multimodel_judge_harnesses.py — parse_opencode_output, run_model,
                                    run_opencode/reasonix/codex/claude/
                                    codewhale/omp/deepcode,
                                    parse_codex_output, _plain_stdout
    здесь — MAX_DIFF_CHARS, read_target, main (argparse + фазы судейства)
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # judge/ — mmj хелперы
import tempfile
import time

from mmj.multimodel_judge_harnesses import (
    parse_codex_output,
    parse_opencode_output,
    run_claude,
    run_codewhale,
    run_codex,
    run_deepcode,
    run_model,
    run_omp,
    run_opencode,
    run_reasonix,
)
from mmj.multimodel_judge_models import (
    CONFIG_NAME,
    DEFAULT_HARNESS,
    DEFAULT_JUDGE,
    DEFAULT_REVIEWERS,
    DEFAULT_TIMEOUT,
    GLOBAL_CONFIG,
    SUPPORTED_HARNESSES,
    candidates_from,
    load_config_file,
    resolve_harness,
    resolve_models,
)
from mmj.multimodel_judge_parse import extract_json_object, parse_judge_questions
from mmj.multimodel_judge_prompts import (
    JUDGE_PROMPT,
    JUDGE_QUERY_PROMPT,
    REVIEWER_FOLLOWUP_PROMPT,
    REVIEWER_PROMPT,
)

__all__ = [
    "CONFIG_NAME", "GLOBAL_CONFIG", "SUPPORTED_HARNESSES", "DEFAULT_HARNESS",
    "DEFAULT_REVIEWERS", "DEFAULT_JUDGE", "DEFAULT_TIMEOUT",
    "MAX_DIFF_CHARS",
    "REVIEWER_PROMPT", "JUDGE_QUERY_PROMPT", "REVIEWER_FOLLOWUP_PROMPT",
    "JUDGE_PROMPT",
    "extract_json_object", "parse_judge_questions", "parse_opencode_output",
    "run_model", "run_opencode", "run_reasonix", "parse_codex_output",
    "run_codex", "run_claude", "run_codewhale", "run_omp", "run_deepcode",
    "load_config_file", "candidates_from", "resolve_models", "resolve_harness",
    "read_target", "main",
]

MAX_DIFF_CHARS = 30_000  # обрезка большого диффа (контекст)


def read_target(args) -> tuple[str, str]:
    """Вернуть (вид, содержимое/путь) объекта проверки."""
    if args.file:
        return "ФАЙЛ", str(pathlib.Path(args.file).resolve())
    diff_src = args.diff
    if diff_src == "-":
        diff = sys.stdin.read()
    else:
        diff = pathlib.Path(diff_src).read_text(encoding="utf-8", errors="replace")
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n…(обрезано)"
    return "ДИФФ", diff


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", help="проверяемый файл (ревьюеры прочитают сами)")
    ap.add_argument("--diff", help="файл с диффом или '-' для stdin")
    ap.add_argument("--query", default="найди ошибки, риски и уязвимости в коде",
                    help="задача для ревьюеров")
    ap.add_argument("--reviewers", default=None,
                    help="модели-ревьюеры через запятую (иначе конфиг/дефолты)")
    ap.add_argument("--judge", default=None, help="модель-судья (иначе конфиг/дефолты)")
    ap.add_argument("--config", default=None,
                    help=f"явный конфиг-файл (иначе ./{CONFIG_NAME} → {GLOBAL_CONFIG})")
    ap.add_argument("--harness", default=None, choices=list(SUPPORTED_HARNESSES),
                    help=f"чем запускать модели (иначе конфиг; дефолт {DEFAULT_HARNESS})")
    ap.add_argument("--out", help="файл для полного протокола (md)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help="таймаут на один вызов, секунд")
    args = ap.parse_args()

    if not args.file and not args.diff:
        ap.error("нужен --file или --diff")

    try:
        reviewers, judge = resolve_models(
            os.getcwd(), args.reviewers, args.judge, args.config)
    except ValueError as exc:
        ap.error(str(exc))
    harness = resolve_harness(os.getcwd(), args.harness, args.config)

    # Чистый конфиг: без MCP-серверов воркспейса (лимит тулов у провайдеров,
    # ревьюерам не нужны наши серверные тулы; судья и так не видит воркспейс).
    workdir = tempfile.mkdtemp(prefix="multimodel-judge-")
    config = os.path.join(workdir, "opencode.json")
    with open(config, "w", encoding="utf-8") as f:
        json.dump({"$schema": "https://opencode.ai/config.json", "mcp": {}}, f)

    kind, target = read_target(args)
    t0 = time.time()

    # Фаза 1: панель ревьюеров, параллельно (fan-out, изолированные сессии).
    # cwd=workdir: чтобы НЕ подхватился корневой opencode.jsonc воркспейса
    # (его MCP раздувают тулы; groq режет на 128). Файл передаётся абсолютным
    # путём — ревьюеры читают его сами.
    prompt = REVIEWER_PROMPT.format(query=args.query, target=target)
    reports: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(reviewers)) as pool:
        futures = {pool.submit(run_model, m, prompt, workdir, args.timeout,
                               config, harness): m for m in reviewers}
        for fut in concurrent.futures.as_completed(futures):
            model = futures[fut]
            try:
                reports[model] = fut.result()
            except Exception as exc:  # noqa: BLE001 - spike: любой сбой одного ревьюера не роняет панель
                reports[model] = f"ОШИБКА ВЫЗОВА: {exc}"

    panel_done = time.time()

    # Фаза 2a: судья — уточняющие вопросы ревьюерам (ask_panel-эквивалент).
    # Порядок отчётов перемешиваем: position bias судьи (futureagi п.7).
    shuffled = list(reviewers)
    random.shuffle(shuffled)
    block = "\n\n".join(
        f"### Ревьюер: {model}\n{reports[model]}" for model in shuffled
    )
    q_prompt = JUDGE_QUERY_PROMPT.format(models=", ".join(reviewers), reports=block)
    judge_q = run_model(judge, q_prompt, workdir, args.timeout, config, harness)
    questions, q_ok = parse_judge_questions(judge_q, reviewers)
    questions_done = time.time()

    # Фаза 2b: ревьюеры отвечают на вопросы (параллельно; контекст — свой
    # первый отчёт, как rerunAgent у Rejudge: помнит, что уже сказал).
    followups: dict[str, str] = {}
    if questions:
        by_model: dict[str, list[str]] = {}
        for q in questions:
            by_model.setdefault(q["model"], []).append(q["question"])
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(by_model)) as pool:
            futures = {}
            for m, qs in by_model.items():
                fu_prompt = REVIEWER_FOLLOWUP_PROMPT.format(
                    query=args.query, report=reports[m],
                    questions="\n".join(f"- {q}" for q in qs))
                futures[pool.submit(run_model, m, fu_prompt, workdir,
                                    args.timeout, config, harness)] = m
            for fut in concurrent.futures.as_completed(futures):
                m = futures[fut]
                try:
                    followups[m] = fut.result()
                except Exception as exc:  # noqa: BLE001 - один сбой не роняет раунд
                    followups[m] = f"ОШИБКА ВЫЗОВА: {exc}"
    followups_done = time.time()

    # Фаза 2c: судья — финальный вердикт по отчётам + ответам (раунд 2).
    if followups:
        follow_block = "\n\n".join(
            f"### Ответ ревьюера {m} на уточняющий вопрос\n{followups[m]}"
            for m in reviewers if m in followups)
    else:
        follow_block = "(уточняющих вопросов не было)"
    judge_prompt = JUDGE_PROMPT.format(reports=block, followups=follow_block)
    verdict = run_model(judge, judge_prompt, workdir, args.timeout, config, harness)
    t1 = time.time()

    # Протокол.
    q_text = judge_q if q_ok else "(судья не выдал валидный JSON — раунд вопросов пропущен)"
    fu_text = "\n\n".join(
        f"### {m}\n{followups[m]}" for m in reviewers if m in followups
    ) or "(вопросов не было)"
    lines = [
        "# Мультимодельное судейство (spike)",
        "",
        f"- Объект ({kind}): {target if kind == 'ФАЙЛ' else '<дифф>' if args.diff == '-' else args.diff}",
        f"- Задача: {args.query}",
        f"- Ревьюеры: {', '.join(reviewers)}",
        f"- Судья: {judge}",
        f"- Харнес: {harness}",
        f"- Панель: {panel_done - t0:.0f}с, вопросы: {questions_done - panel_done:.0f}с, "
        f"ответы: {followups_done - questions_done:.0f}с, вердикт: {t1 - followups_done:.0f}с, "
        f"всего: {t1 - t0:.0f}с",
        "",
        "## Итоговый отчёт судьи",
        "",
        verdict,
        "",
        "---",
        "## Уточняющие вопросы судьи",
        "",
        q_text,
        "",
        "## Ответы ревьюеров на вопросы",
        "",
        fu_text,
        "",
        "---",
        "## Отчёты ревьюеров",
        "",
    ]
    for model in reviewers:
        lines += [f"### {model}", "", reports[model], ""]
    protocol = "\n".join(lines)

    if args.out:
        pathlib.Path(args.out).write_text(protocol, encoding="utf-8")
        print(f"[ok] протокол: {args.out}")
    print(verdict)
    import shutil
    shutil.rmtree(workdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
