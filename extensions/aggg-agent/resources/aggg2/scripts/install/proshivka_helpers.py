# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""proshivka_helpers — константы прошивки (MATCHER_*, CHULAN/SRC/
OPCODE_DIR) + общие хелперы (_matcher_upgrade, deploy_file,
_ensure_json_hook, _python_cmd, _deploy_hooks).

Вынесено из install_proshivka.py механически (verbatim) — гейт god-файлов.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
import shutil
from pathlib import Path

from jsonc_edit import write_json

CHULAN = Path(__file__).resolve().parent.parent.parent
SRC = CHULAN / "harness"

# Матчеры PreToolUse по харнесам (консистентность, docs/canon/FILE-SIZE.md матрица):
# shell-тул + edit-тулы — файл-гейт работает у всех, чей рантайм позволяет.
MATCHER_CLAUDE = "Bash|Edit|Write|MultiEdit|NotebookEdit"
MATCHER_GEMINI = "run_shell_command|write_file|edit_.*"
MATCHER_AGY = ("run_command|write_to_file|replace_file_content|"
               "multi_replace_file_content")
MATCHER_OMP = "Bash|Edit|Write|MultiEdit"
MATCHER_HERMES = "terminal|write_file|edit_.*"


def _matcher_upgrade(path: Path, data: dict, grp: dict, matcher: str, args,
                     key: str) -> bool:
    """Обновить matcher существующей группы, если он отстал (добавились
    edit-тулы). Идемпотентно, с бэкапом — консистентность харнесов."""
    if grp.get("matcher") == matcher:
        return False
    if args.dry_run:
        print(f"[ ] (dry-run) matcher {key}: {grp.get('matcher')!r} "
              f"-> {matcher!r}")
        return False
    grp["matcher"] = matcher
    if path.is_file():
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
    write_json(str(path), data)
    print(f"[✓] matcher {key} обновлён: {matcher} -> {path}")
    return True
OPCODE_DIR = Path.home() / ".config" / "opencode"


def up_to_date(dst: Path, src: Path) -> bool:
    return dst.is_file() and dst.read_bytes() == src.read_bytes()


def deploy_file(src: Path, dst: Path, args) -> bool:
    """Копирует src -> dst с бэкапом. Возвращает True, если что-то сделано."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if up_to_date(dst, src):
        print(f"[=] уже актуально: {dst}")
        return False
    if dst.exists():
        bak = dst.with_suffix(dst.suffix + ".bak")
        if args.dry_run:
            print(f"[ ] (dry-run) бэкап -> {bak}, запись -> {dst}")
            return False
        shutil.copy2(dst, bak)
        print(f"[~] бэкап -> {bak}")
    if args.dry_run:
        print(f"[ ] (dry-run) записал бы -> {dst}")
        return False
    shutil.copy2(src, dst)
    print(f"[✓] -> {dst}")
    return True

def _ensure_json_hook(path: Path, key: str, command: str, args,
                      matcher: str | None = None) -> bool:
    """Вписывает hook события key (command-хендлер) в JSON-файл с merge.

    matcher — фильтр события (например, имена тулов для PreToolUse);
    без matcher — группа без фильтра (события UserPromptSubmit).
    """
    data = {}
    if path.is_file():
        try:
            # utf-8-sig: конфиги с BOM (Windows) не должны убивать парсинг
            # (багрепорт v2.4 BUG-3 — класс «молчаливая потеря конфига»).
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as e:  # noqa: BLE001 — НЕ перезаписываем битый конфиг
            print(f"[!] не могу разобрать конфиг {path}: {e!r}")
            print("    конфиг НЕ тронут — разберись с файлом и повтори")
            return False
    hooks = data.setdefault("hooks", {})
    events = hooks.setdefault(key, [])
    for grp in events:
        for h in grp.get("hooks", []):
            if h.get("command") == command:
                # консистентность: матчер мог расшириться (edit-тулы и т.п.)
                if matcher and grp.get("matcher") != matcher:
                    return _matcher_upgrade(path, data, grp, matcher, args, key)
                print(f"[=] hook уже в конфиге: {key} -> {path}")
                return False
    grp = {"hooks": [{"type": "command", "command": command}]}
    if matcher:
        grp["matcher"] = matcher
    events.append(grp)
    if args.dry_run:
        print(f"[ ] (dry-run) hook {key} -> {path}")
        return False
    if path.is_file():
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
        print(f"[~] бэкап конфига -> {bak}")
    write_json(str(path), data)
    print(f"[✓] hook {key} -> {path}")
    return True


def _python_cmd() -> str:
    """Команда интерпретатора для хуков: на Windows python3 отсутствует —
    там py -3 (или python); на posix — python3."""
    if os.name == "nt":
        return shutil.which("py") or "python"
    return shutil.which("python3") or "python3"


def _deploy_hooks(hooks_dir: Path, args) -> bool:
    """Кладёт хук-скрипт, его подмодули и ядро правил в каталог hooks харнесса."""
    changed = False
    src_hook = SRC / "hooks" / "aggg2_prompt_hook.py"
    src_handlers = SRC / "hooks" / "handlers_misc.py"
    src_gates = SRC / "hooks" / "hook_gates.py"
    src_hints = SRC / "hooks" / "hook_hints.py"
    src_canary = SRC / "hooks" / "canary_gates.py"
    src_sesend = SRC / "hooks" / "session_end_gate.py"
    src_core = SRC / "core.txt"
    if src_hook.is_file():
        changed |= deploy_file(src_hook, hooks_dir / "aggg2_prompt_hook.py", args)
    else:
        print(f"[!] нет источника хука: {src_hook}")
    if src_handlers.is_file():
        changed |= deploy_file(src_handlers, hooks_dir / "handlers_misc.py", args)
    if src_canary.is_file():
        changed |= deploy_file(src_canary, hooks_dir / "canary_gates.py", args)
    if src_sesend.is_file():
        changed |= deploy_file(src_sesend, hooks_dir / "session_end_gate.py", args)
    if src_gates.is_file():
        changed |= deploy_file(src_gates, hooks_dir / "hook_gates.py", args)
    if src_hints.is_file():
        changed |= deploy_file(src_hints, hooks_dir / "hook_hints.py", args)
    if src_core.is_file():
        changed |= deploy_file(src_core, hooks_dir / "core.txt", args)
    else:
        print(f"[!] нет источника ядра: {src_core}")
    return changed

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
