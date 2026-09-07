# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Запуск моделей через харнесы мультимодельного судейства.

Вынесено из multimodel_judge.py (механическая резка god-файла, код дословно):
parse_opencode_output, run_model + run_* (opencode/reasonix/codex/claude/
codewhale/omp/deepcode), parse_codex_output, _plain_stdout.
"""
import json
import os
import subprocess

from mmj.multimodel_judge_models import DEFAULT_HARNESS


def parse_opencode_output(stdout: str, stderr: str = "") -> str:
    """Вытащить текстовый ответ из JSON-потока событий opencode run.

    Пустой текст + error-событие или ошибка в stderr -> диагноз вместо тишины.
    """
    texts = []
    errors = []
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "text" and ev.get("part", {}).get("type") == "text":
            texts.append(ev["part"].get("text", ""))
        if ev.get("type") == "error":
            err = ev.get("error", {})
            errors.append(str(err.get("message", err)))
    if texts:
        return "\n".join(texts).strip()
    if errors:
        return f"ОШИБКА API: {'; '.join(errors)[:2000]}"
    tail = stderr.strip().splitlines()[-3:]
    if tail:
        return f"(пусто; stderr: {' | '.join(tail)[:500]})"
    return "(пусто)"


def run_model(model: str, prompt: str, cwd: str, timeout: int,
              config: str, harness: str = DEFAULT_HARNESS) -> str:
    """Один вызов модели через выбранный харнес (изолированная сессия).

    opencode — основной бэкенд (проверен); reasonix/codex/claude — headless
    CLI своих харнессов. Все требуют сеть и авторизацию харнесса на машине.
    """
    if harness == "reasonix":
        return run_reasonix(model, prompt, timeout)
    if harness == "codex":
        return run_codex(model, prompt, timeout)
    if harness == "claude":
        return run_claude(model, prompt, timeout)
    if harness == "codewhale":
        return run_codewhale(model, prompt, timeout)
    if harness == "omp":
        return run_omp(model, prompt, timeout)
    if harness == "deepcode":
        return run_deepcode(model, prompt, timeout)
    return run_opencode(model, prompt, cwd, timeout, config)


def run_opencode(model: str, prompt: str, cwd: str, timeout: int,
                 config: str) -> str:
    """opencode run --format json --model (чистый конфиг без MCP: ревьюерам
    не нужны наши серверные тулы; судья и так не видит воркспейс)."""
    cmd = ["opencode", "run", "--format", "json", "--model", model, prompt]
    env = {**os.environ, "OPENCODE_CONFIG": config}
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=cwd, env=env, check=False,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT (не уложился в лимит)"
    return parse_opencode_output(proc.stdout or "", proc.stderr or "")


def run_reasonix(model: str, prompt: str, timeout: int) -> str:
    """reasonix run --model — headless, ответ в stdout (текст)."""
    cmd = ["reasonix", "run", "--model", model, prompt]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT (не уложился в лимит)"
    text = (proc.stdout or "").strip()
    if text:
        return text
    tail = (proc.stderr or "").strip().splitlines()[-3:]
    return f"(пусто; stderr: {' | '.join(tail)[:500]})" if tail else "(пусто)"


def parse_codex_output(stdout: str) -> str:
    """Вытащить финальный ответ из JSON-lines потока codex exec --json.

    События: turn.completed / item.completed с item.content (строка или
    массив частей {type: text}). Незнакомые события игнорируем.
    """
    texts = []
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (ev.get("item") or {}).get("content")
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    texts.append(part.get("text", ""))
    return "\n".join(t for t in texts if t).strip() or "(пусто)"


def run_codex(model: str, prompt: str, timeout: int) -> str:
    """codex exec --json -c model=... — headless, JSON-lines на stdout.

    --skip-git-repo-check: вне git-каталога codex отказывается работать.
    Модель — в формате codex (напр. gpt-5.4-mini), не provider/model.
    """
    cmd = ["codex", "exec", "--json", "--skip-git-repo-check",
           "-c", f"model={model}", prompt]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT (не уложился в лимит)"
    parsed = parse_codex_output(proc.stdout or "")
    if parsed != "(пусто)":
        return parsed
    tail = (proc.stderr or "").strip().splitlines()[-3:]
    return f"(пусто; stderr: {' | '.join(tail)[:500]})" if tail else "(пусто)"


def run_claude(model: str, prompt: str, timeout: int) -> str:
    """claude -p --model — headless print mode, ответ в stdout (текст)."""
    cmd = ["claude", "-p", "--model", model, prompt]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT (не уложился в лимит)"
    text = (proc.stdout or "").strip()
    if text:
        return text
    tail = (proc.stderr or "").strip().splitlines()[-3:]
    return f"(пусто; stderr: {' | '.join(tail)[:500]})" if tail else "(пусто)"


def _plain_stdout(cmd: list[str], timeout: int) -> str:
    """Общий запуск headless CLI, ответ в stdout (текст)."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT (не уложился в лимит)"
    text = (proc.stdout or "").strip()
    if text:
        return text
    tail = (proc.stderr or "").strip().splitlines()[-3:]
    return f"(пусто; stderr: {' | '.join(tail)[:500]})" if tail else "(пусто)"


def run_codewhale(model: str, prompt: str, timeout: int) -> str:
    """codewhale exec — one-shot ответ; модель — из конфига codewhale
    (--model у exec не пробрасывается)."""
    return _plain_stdout(["codewhale", "exec", prompt], timeout)


def run_omp(model: str, prompt: str, timeout: int) -> str:
    """omp -p --model — non-interactive print mode (модель поддерживается)."""
    return _plain_stdout(["omp", "-p", "--model", model, prompt], timeout)


def run_deepcode(model: str, prompt: str, timeout: int) -> str:
    """deepcode -p — non-interactive; модель — из ~/.deepcode/settings.json."""
    return _plain_stdout(["deepcode", "-p", prompt], timeout)
