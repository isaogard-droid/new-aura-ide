# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Конфиг и резолв моделей мультимодельного судейства.

Вынесено из multimodel_judge.py (механическая резка god-файла, код дословно):
константы конфига и приоритет моделей CLI > --config > проектный > глобальный > дефолты.
"""
import json
import os
import pathlib

# Конфиг-файл моделей (паттерн Rejudge config.ts): менять модели БЕЗ правки
# кода. Приоритет: CLI-флаг > --config > проектный (.multimodel-judge.json
# в cwd) > глобальный (~/.config/aggg2/multimodel-judge.json) > дефолты.
# Формат файла:
#   {"reviewers": ["provider/model", ...], "judge": "provider/model",
#    "harness": "opencode|reasonix|codex|claude"}
# harness — чем запускать модели (по умолчанию opencode).
CONFIG_NAME = ".multimodel-judge.json"
GLOBAL_CONFIG = (
    pathlib.Path(os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config"))
    / "aggg2" / "multimodel-judge.json"
)
SUPPORTED_HARNESSES = ("opencode", "reasonix", "codex", "claude",
                       "codewhale", "omp", "deepcode")
DEFAULT_HARNESS = "opencode"

# Ревьюеры по умолчанию — три разных семейства opencode-go (free), НЕ deepseek:
# судья обязан быть ДРУГОЙ семейки, чем ревьюеры (family bias: судья из той же
# семейки переоценивает своих; futureagi LLM-as-Judge 2026, research.db id=352).
DEFAULT_REVIEWERS = [
    "opencode/mimo-v2.5-free",
    "opencode/hy3-free",
    "opencode/nemotron-3-ultra-free",
]
# Судья — самый сильный доступный фронтир (для низкочастотных высокоточных
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# проверок — frontier-модель, futureagi п.1), и он другой семейки, чем панель.
DEFAULT_JUDGE = "deepseek/deepseek-v4-pro"
DEFAULT_TIMEOUT = 240


def load_config_file(path: pathlib.Path) -> dict:
    """Прочитать JSON-конфиг; при битом файле — ошибка с путём и подсказкой."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"конфиг не читается: {path} ({exc})") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"конфиг не JSON: {path} — строка {exc.lineno}: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"конфиг должен быть объектом: {path}")
    return parsed


def candidates_from(explicit: str | None, cwd: str,
                    global_path: pathlib.Path | None) -> list[tuple[str, pathlib.Path]]:
    """Пути конфигов по приоритету: --config > проектный > глобальный."""
    out: list[tuple[str, pathlib.Path]] = []
    if explicit:
        out.append(("--config", pathlib.Path(explicit)))
    out.append(("проектный", pathlib.Path(cwd) / CONFIG_NAME))
    out.append(("глобальный", global_path or GLOBAL_CONFIG))
    return out


def resolve_models(cwd: str, cli_reviewers: str | None, cli_judge: str | None,
                   explicit: str | None = None,
                   global_path: pathlib.Path | None = None) -> tuple[list[str], str]:
    """Модели по приоритету: CLI > --config > проектный > глобальный > дефолты.

    Валидация как у Rejudge: минимум 2 ревьюера + судья, ошибка называет пути.
    """
    reviewers: list[str] = []
    judge: str = ""
    source = ""

    if cli_reviewers:
        reviewers = [m.strip() for m in cli_reviewers.split(",") if m.strip()]
        judge = cli_judge or ""
        source = "CLI"
        if not judge:
            # Частичное переопределение: судья — из конфига или дефолта.
            for _, path in candidates_from(explicit, cwd, global_path):
                if path.exists():
                    cfg = load_config_file(path)
                    if cfg.get("judge"):
                        judge = str(cfg["judge"]).strip()
                        break
            if not judge:
                judge = DEFAULT_JUDGE
    else:
        candidates: list[tuple[str, pathlib.Path]] = candidates_from(
            explicit, cwd, global_path)
        for label, path in candidates:
            if path.exists():
                cfg = load_config_file(path)
                if "reviewers" in cfg and "judge" in cfg:
                    reviewers = [m.strip() for m in cfg["reviewers"] if str(m).strip()]
                    judge = str(cfg["judge"]).strip()
                    source = f"{label} ({path})"
                    break
        if not reviewers or not judge:
            reviewers = list(DEFAULT_REVIEWERS)
            judge = DEFAULT_JUDGE
            source = "дефолты"

    if len(reviewers) < 2:
        raise ValueError(
            f"нужно минимум 2 ревьюера (есть {len(reviewers)}, источник: {source or 'CLI'}). "
            f"Задай --reviewers 'м1,м2' или конфиг {CONFIG_NAME} "
            f"(см. --help)."
        )
    if not judge:
        raise ValueError(f"не задан судья (источник: {source or 'CLI'}): --judge или конфиг")
    return reviewers, judge


def resolve_harness(cwd: str, cli_harness: str | None,
                    explicit: str | None = None,
                    global_path: pathlib.Path | None = None) -> str:
    """Харнес запуска по приоритету: CLI > конфиг (первый с полем) > дефолт."""
    if cli_harness:
        return cli_harness
    for _, path in candidates_from(explicit, cwd, global_path):
        if path.exists():
            cfg = load_config_file(path)
            h = cfg.get("harness")
            if h:
                return str(h).strip()
    return DEFAULT_HARNESS
