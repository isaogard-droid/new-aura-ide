# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""proshivka_permissions — permission.ask на god-файлы:
apply_opencode_permissions (opencode v2 permission.edit) и
apply_claude_permissions (settings.json permissions.ask).

Вынесено из install_proshivka.py механически (verbatim) — гейт god-файлов.
"""
import contextlib
import json
import os
import shutil
import sys
from pathlib import Path

# Паттерн db-tools/: свой каталог — соседи (proshivka_helpers),
# scripts/ — кирпичи канона (jsonc_edit). Без этого прямой запуск/
# импорт падает с ModuleNotFoundError после реорга scripts/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from jsonc_edit import load_jsonc, write_json  # noqa: E402
from proshivka_helpers import OPCODE_DIR  # noqa: E402


def apply_opencode_permissions(args) -> bool:
    """opencode v2 permissions: 'ask' на правки baseline god-файлов
    (docs/canon/FILE-SIZE.md). v2 не имеет tool.execute.before — это ЕДИНСТВЕННЫЙ
    нативный сторож правок в v2 (permission.edit, паттерн opencode.ai/docs/
    permissions: granular object syntax, last match wins; 'ask' в TUI
    спрашивает подтверждение, deny не ставим — резку файлов блокировать
    нельзя). Список — из scripts/file_size_baseline.json (один источник).
    Управляемые нами ключи чистим по снапшоту ~/.config/aggg2/
    file-size-paths.json: ушёл из baseline — ушёл и ask (не оставляем
    мусор в чужом конфиге)."""
    baseline = Path(__file__).resolve().parent.parent / "file_size_baseline.json"
    if not baseline.is_file():
        return False
    try:
        god_paths = [p for p in json.loads(
            baseline.read_text(encoding="utf-8"))
            if isinstance(p, str) and not p.startswith("_")]
    except (OSError, json.JSONDecodeError):
        return False
    if not god_paths:
        return False
    path = OPCODE_DIR / "opencode.json"
    if not path.is_file():
        path = OPCODE_DIR / "opencode.jsonc"
    data = {}
    if path.is_file():
        try:
            data = load_jsonc(str(path))
        except Exception as e:  # noqa: BLE001 — битый конфиг НЕ перезаписываем
            print(f"[!] permissions: не могу разобрать конфиг {path}: {e!r}")
            return False
    snap_dir = Path.home() / ".config" / "aggg2"
    snap_path = snap_dir / "file-size-paths.json"
    old_paths = []
    with contextlib.suppress(OSError, json.JSONDecodeError):
        old_paths = json.loads(snap_path.read_text(encoding="utf-8"))
    perm = data.setdefault("permission", {})
    edit = perm.setdefault("edit", {})
    if not isinstance(edit, dict):
        # Легаси v1: "permission": {"edit": "allow"} — строка вместо
        # объекта; v2-семантика: {"*": <значение>} (last match wins,
        # конкретные пути ниже перекроют "*").
        perm["edit"] = {"*": edit}
        edit = perm["edit"]
    edit.setdefault("*", "allow")
    # Чистим только те ключи, что ставили МЫ раньше (снапшот)
    for p in old_paths:
        if p != "*" and p not in god_paths:
            edit.pop(p, None)
    # Ставим ask на актуальные god-файлы
    for p in god_paths:
        edit[p] = "ask"
    if args.dry_run:
        print(f"[ ] (dry-run) permission.edit ask -> {len(god_paths)} файлов")
        return False
    if path.is_file():
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
        print(f"[~] бэкап конфига -> {bak}")
    write_json(str(path), data)
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_path.write_text(json.dumps(god_paths, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"[✓] permission.edit 'ask' на god-файлы ({len(god_paths)}) -> {path}")
    return True


def apply_claude_permissions(args) -> bool:
    """Claude Code permissions: 'ask' на правки baseline god-файлов —
    паритет с opencode v2 (code.claude.com/docs/en/permissions: правила
    Tool(specifier), deny > ask > allow; enforced Claude Code, не моделью).
    Список — из scripts/file_size_baseline.json (один источник). Наши
    правила чистим по снапшоту ~/.config/aggg2/claude-file-size-paths.json."""
    baseline = Path(__file__).resolve().parent.parent / "file_size_baseline.json"
    if not baseline.is_file():
        return False
    try:
        god_paths = [p for p in json.loads(
            baseline.read_text(encoding="utf-8"))
            if isinstance(p, str) and not p.startswith("_")]
    except (OSError, json.JSONDecodeError):
        return False
    settings = Path.home() / ".claude" / "settings.json"
    data = {}
    if settings.is_file():
        try:
            data = load_jsonc(str(settings))
        except Exception as e:  # noqa: BLE001 — битый конфиг НЕ перезаписываем
            print(f"[!] claude permissions: не разобрать {settings}: {e!r}")
            return False
    snap_path = Path.home() / ".config" / "aggg2" / "claude-file-size-paths.json"
    old_rules = []
    with contextlib.suppress(OSError, json.JSONDecodeError):
        old_rules = json.loads(snap_path.read_text(encoding="utf-8"))
    perm = data.setdefault("permissions", {})
    ask = perm.setdefault("ask", [])
    ask[:] = [r for r in ask if r not in old_rules]  # убрать наши прошлые
    new_rules = [f"{tool}({p})" for tool in
                 ("Edit", "Write", "MultiEdit", "NotebookEdit")
                 for p in god_paths]
    ask.extend(new_rules)
    if args.dry_run:
        if new_rules:
            print(f"[ ] (dry-run) claude permissions.ask -> {len(new_rules)}")
        return False
    if settings.is_file():
        bak = settings.with_suffix(settings.suffix + ".bak")
        shutil.copy2(settings, bak)
        print(f"[~] бэкап конфига -> {bak}")
    write_json(str(settings), data)
    snap_path.parent.mkdir(parents=True, exist_ok=True)
    snap_path.write_text(json.dumps(new_rules, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    if new_rules:
        print(f"[✓] claude permissions.ask на god-файлы "
              f"({len(new_rules)}) -> {settings}")
    return bool(new_rules)

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
