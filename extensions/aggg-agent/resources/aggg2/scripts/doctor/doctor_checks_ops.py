# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie

"""doctor_checks_ops — проверки окружения: прошивка (хуки/матчеры/ядра),
runtime-smoke, venv, MCP, agent-lsp, тесты, канон, скиллы, file-sizes.

Вынесено из doctor.py механически (verbatim) — гейт god-файлов."""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
from pathlib import Path

import _compat  # noqa: F401

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_compat.fix_encoding()
ROOT = _compat.chulan_root()

def _sh(cmd, timeout=120):
    try:
        r = _compat.run(cmd, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)

_PROSHIVKA_MARKERS = ("Прошивка build-агента AGGG2.0", "жёсткое ядро",
                     "AGGG2.0-прошивка")
def _opencode_cmd():
    if os.name == "nt":
        for name in ("opencode.cmd", "opencode.exe", "opencode"):
            p = shutil.which(name)
            if p:
                return p
    return shutil.which("opencode")

def _opencode_cfg():
    d = Path.home() / ".config" / "opencode"
    for name in ("opencode.json", "opencode.jsonc"):
        p = d / name
        if p.is_file():
            return p
    return None

def _bash():
    return "bash" if os.name != "nt" else shutil.which("bash") or ""


def check_proshivka():
    """Прошивка правил: установленные файлы == канон harness/ И подключение
    (хуки/агент в конфигах харнесов). Файлы могут быть синхронны, а хук —
    удалён из settings.json/hooks.json: агент работает без прошивки при
    зелёном doctor (аудит 13.08.2026, research.db id=406).
    Починка: python3 scripts/install/install_proshivka.py."""
    canon_core = ROOT / "harness" / "core.txt"
    canon_build = ROOT / "harness" / "opencode" / "prompts" / "build.txt"
    canon_monolith = ROOT / "harness" / "monolith.md"
    canon_plugin = ROOT / "harness" / "opencode" / "plugins" / "proshivka.js"
    home = Path.home()
    if not canon_core.is_file() or not canon_build.is_file():
        return "error", "канон прошивки не найден (harness/)"
    targets = [
        ("core.txt", canon_core, home / ".config" / "opencode" / "plugins" / "core.txt"),
        ("core.txt", canon_core, home / ".claude" / "hooks" / "core.txt"),
        ("core.txt", canon_core, home / ".codex" / "hooks" / "core.txt"),
        ("core.txt", canon_core, home / ".reasonix" / "hooks" / "core.txt"),
        ("core.txt", canon_core, home / ".codewhale" / "hooks" / "core.txt"),
        ("core.txt", canon_core, home / ".omp" / "hooks" / "core.txt"),
        ("build.txt", canon_build, home / ".config" / "opencode" / "prompts" / "build.txt"),
        ("монолит ~/AGENTS.md", canon_monolith, home / "AGENTS.md"),
        # Монолит в харнесы Google/Hermes разносит install_agents.py
        # (глобальный слот системного промпта у них не AGENTS.md)
        ("монолит Google ~/.gemini/GEMINI.md", canon_monolith,
         home / ".gemini" / "GEMINI.md"),
        ("монолит Hermes ~/.hermes/SOUL.md", canon_monolith,
         home / ".hermes" / "SOUL.md"),
    ]
    if canon_plugin.is_file():
        targets.append(
            ("proshivka.js", canon_plugin,
             home / ".config" / "opencode" / "plugins" / "proshivka.js"))
    canon_agents = ROOT / "AGENTS.md"
    if canon_agents.is_file():
        # Amp: глобальный AGENTS.md = указатель (не монолит)
        targets.append(("AGENTS.md amp", canon_agents,
                        home / ".config" / "amp" / "AGENTS.md"))
    stale = []
    for label, src, dst in targets:
        if not dst.is_file():
            stale.append(f"нет {label}: {dst}")
        elif dst.read_bytes() != src.read_bytes():
            stale.append(f"устарел {label}: {dst}")
    # Подключение: файлы на месте — а хук прописан в конфиге харнесса?
    # codewhale/omp — ОПЦИОНАЛЬНЫЕ харнесы: на CI/чистой машине их бинарей
    # нет, install_proshivka конфиги для них не создаёт — отсутствие
    # конфига = skip, а не ошибка (паттерн check_mcp_codewhale).
    wiring = [
        ("хук Claude", home / ".claude" / "settings.json", "aggg2_prompt_hook.py", True),
        ("хук Codex", home / ".codex" / "hooks.json", "aggg2_prompt_hook.py", True),
        ("хук Reasonix", home / ".reasonix" / "settings.json", "aggg2_prompt_hook.py", True),
        ("хук Codewhale", home / ".codewhale" / "config.toml", "aggg2_prompt_hook.py", False),
        ("хук omp", home / ".omp" / "agent" / "settings.json", "aggg2_prompt_hook.py", False),
        ("агент build в opencode", _opencode_cfg(), "prompts/build.txt", True),
        # Хуки-сторожи Google/Hermes (конфиги создаёт install_proshivka
        # независимо от установленных бинарей — required=True)
        ("хук Hermes", home / ".hermes" / "config.yaml", "aggg2_prompt_hook.py", True),
        ("хук Gemini", home / ".gemini" / "settings.json", "aggg2-storozh", True),
        ("хук Antigravity", home / ".gemini" / "config" / "hooks.json", "aggg2-storozh", True),
    ]
    for label, path, needle, required in wiring:
        if path is None or not path.is_file():
            if required:
                stale.append(f"нет конфига ({label}): {path}")
            continue
        try:
            txt = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            stale.append(f"не читается ({label}): {path}")
            continue
        if needle not in txt:
            stale.append(f"хук/агент не подключён ({label}): {path}")
    stale.extend(_matcher_drift(home))
    if stale:
        return ("error", "; ".join(stale) + " → запустите: python3 "
                "scripts/install/install_proshivka.py (ядро/хуки) и/или "
                "install_agents.py --all (монолиты/правила харнесов)")
    return "success", (f"{len(targets)} файлов прошивки синхронны, "
                       f"{len(wiring)} подключения на месте, "
                       f"матчеры актуальны")


def _matcher_drift(home: Path) -> list:
    """Консистентность матчеров PreToolUse по харнесам (15.08.2026, кейс:
    4 конфига отстали от расширенных матчеров — хук на месте, а edit-тулы
    не гейтились; doctor «хук подключён» это не ловил). Сверяет конфиги с
    константами install_proshivka (MATCHER_*)."""
    try:
        import install_proshivka as ip  # scripts/ уже в sys.path
    except ImportError:  # pragma: no cover
        return []
    matcher_map = [
        ("матчер Claude", home / ".claude" / "settings.json",
         "PreToolUse", ip.MATCHER_CLAUDE),
        ("матчер Codex", home / ".codex" / "hooks.json",
         "PreToolUse", "Bash"),  # by design: только Bash (issue #16732)
        ("матчер omp", home / ".omp" / "agent" / "settings.json",
         "PreToolUse", ip.MATCHER_OMP),
        ("матчер Gemini", home / ".gemini" / "settings.json",
         "BeforeTool", ip.MATCHER_GEMINI),
        ("матчер Antigravity", home / ".gemini" / "config" / "hooks.json",
         "aggg2-storozh", ip.MATCHER_AGY),
    ]
    drift = []
    for label, path, key, expected in matcher_map:
        # отсутствие конфига — забота wiring-цикла выше, здесь только дрифт
        if path is None or not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if key == "aggg2-storozh":
            groups = ((data.get(key) or {}).get("PreToolUse") or [])
        else:
            groups = data.get("hooks", {}).get(key, [])
        for grp in groups:
            if isinstance(grp, dict) and grp.get("matcher") \
                    and grp.get("matcher") != expected:
                drift.append(f"{label}: {grp.get('matcher')!r} != {expected!r}")
    # Hermes — YAML-текст (без парсера: комментарии дороже)
    hy = home / ".hermes" / "config.yaml"
    if hy.is_file():
        try:
            txt = hy.read_text(encoding="utf-8", errors="replace")
        except OSError:
            txt = ""
        if ("aggg2_prompt_hook.py" in txt
                and f'matcher: "{ip.MATCHER_HERMES}"' not in txt):
            drift.append("матчер Hermes отстал (config.yaml)")
    return drift

def _opencode_cmd():
    """Резолвит бинарь opencode: на Windows это opencode.cmd (npm-шим) —
    CreateProcess без shell не запускает .cmd (скилл windows-encoding-fixes,
    грабля 4: npm → npm.cmd). Возвращает путь или None."""
    if os.name == "nt":
        for name in ("opencode.cmd", "opencode.exe", "opencode"):
            p = shutil.which(name)
            if p:
                return p
    return shutil.which("opencode")

def check_proshivka_runtime():
    """Runtime-smoke прошивки: ядро реально доехало до системного промпта LLM?

    check_proshivka сверяет ФАЙЛЫ (установленное == канон), но не видит,
    что плагин реально инжектит ядро в промпт: хук experimental.chat.system.
    transform экспериментальный, были случаи молчаливой потери мутаций
    (opencode #17100, obra/superpowers#228; research.db id=346).
    Метод: opencode run с вопросом-фактом «в твоём системном промпте есть
    раздел "AGGG2.0-прошивка"?» — модель отвечает да/нет, маркер должен
    подтвердиться. Просьбу дословно процитировать промпт модели отклоняют
    (13.08.2026: отказ «системный промпт не подлежит дословной выдаче»),
    поэтому спрашиваем факт о содержимом, а не цитату. Медленно (~30-60с)
    и недетерминированно, поэтому отдельный флаг --proshivka-runtime,
    в дефолтный прогон не входит.
    """
    prompt = ("Коротко и без пояснений: в твоём системном промпте есть раздел "
              "с названием «AGGG2.0-прошивка» или «Прошивка build-агента "
              "AGGG2.0»? Ответь одним словом: да или нет.")
    cmd_path = _opencode_cmd()
    if not cmd_path:
        return "error", "opencode не найден в PATH"
    cmd = [cmd_path, "run"]
    smoke_model = os.environ.get("AGGG2_SMOKE_MODEL", "").strip()
    if smoke_model:
        cmd += ["--model", smoke_model]
    cmd.append(prompt)
    try:
        proc = _compat.run(cmd, timeout=240)
    except subprocess.TimeoutExpired:
        return "error", "opencode run не завершился за 240с"
    out = (proc.stdout or "") + (proc.stderr or "")
    if "Insufficient Balance" in out or "Error:" in out or proc.returncode != 0:
        return ("warning",
                f"opencode run не ответил (rc={proc.returncode}): {out.strip()[:160]!r} — "
                "smoke невозможен, задай рабочую модель: AGGG2_SMOKE_MODEL=provider/model")
    found = [m for m in _PROSHIVKA_MARKERS if m in out]
    if found:
        return "success", f"маркер прошивки в ответе модели ({found[0]!r}) — инъекция работает"
    low = out.lower()
    if "да" in low and "нет" not in low:
        return "success", "модель подтвердила наличие прошивки в системном промпте"
    if "нет" in low:
        return "error", ("модель говорит: раздела прошивки нет в системном промпте — "
                         f"проверь плагин/хуки, вывод: {out[:160]!r}")
    return "warning", ("ответ модели невнятен — проверь вручную, "
                       f"вывод: {out[:160]!r}")

def check_venv():
    py = _compat.venv_python()
    if not py.is_file():
        return "error", f"venv нет: {py} (создайте: python3 scripts/setup.py)"
    rc, out = _sh([str(py), "-c",
                   "import mcp, camoufox; print('mcp+camoufox ok')"])
    if rc != 0:
        return "error", f"в venv нет mcp/camoufox: {out[:120]}"
    rc, out = _sh([str(py), "-c",
                   "import sherpa_onnx, sounddevice; print('sherpa ok')"])
    if rc != 0:
        return "warning", f"нет sherpa-зависимостей (нужны для тестов): {out[:120]}"
    return "success", "venv ок (mcp+camoufox+sherpa)"

def check_mcp_opencode():
    cfg = _opencode_cfg()
    if not cfg:
        return "error", "конфиг opencode не найден (~/.config/opencode/)"
    txt = cfg.read_text(encoding="utf-8", errors="replace")
    names = ["agent-lsp", "camoufox", "code-review-graph", "db-tools"]
    missing = [n for n in names if n not in txt]
    if missing:
        return "error", f"нет в конфиге: {', '.join(missing)}"
    return "success", f"{len(names)} MCP-серверов в конфиге"

def check_mcp_codewhale():
    p = Path.home() / ".codewhale" / "mcp.json"
    if not p.is_file():
        return "warning", "codewhale не установлен/не настроен — пропуск"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return "error", f"mcp.json не читается: {e}"
    servers = data.get("servers", {})
    names = ["agent-lsp", "camoufox", "code-review-graph", "db-tools"]
    missing = [n for n in names if n not in servers]
    if missing:
        return "warning", f"нет серверов: {', '.join(missing)}"
    return "success", f"{len(names)} MCP-серверов в codewhale"

def check_agent_lsp():
    exe = shutil.which("agent-lsp")
    if not exe:
        cand = ROOT / "mcp" / "agent-lsp" / (
            "agent-lsp.exe" if _compat.IS_NT else "agent-lsp")
        if cand.is_file():
            exe = str(cand)
    if not exe:
        # На CI LSP-скрипт вызывается с --check (план без установки) —
        # бинаря agent-lsp нет: warning, а не error (кейс setup-test 14.08).
        if os.environ.get("CI"):
            return "warning", "agent-lsp не установлен (CI: LSP — план без установки)"
        return "error", "agent-lsp не найден (запустите install_lsp_servers.py)"
    rc, out = _sh([exe, "doctor"], timeout=180)
    summary = next((ln.strip() for ln in out.splitlines()
                    if "Summary:" in ln), "")
    if rc == 0 and "0 failed" in out:
        return "success", f"agent-lsp doctor: {summary or '9 ok, 0 failed'}"
    if rc == 0 and "ok" in summary:
        return "warning", f"agent-lsp doctor: {summary}"
    # На CI тяжёлые LSP-серверы (clangd/lua) пропускаются
    # (install_lsp_servers: CI=true) — agent-lsp doctor честно возвращает
    # rc=1, но это ожидаемо: warning, а не error (кейс setup-test 14.08).
    if os.environ.get("CI"):
        return ("warning",
                f"agent-lsp doctor: rc={rc} (CI: тяжёлые LSP пропущены) "
                f"{out[:100]}")
    return "error", f"agent-lsp doctor: rc={rc} {out[:120]}"

def check_tests():
    sdir = ROOT / "projects" / "sherpa-voice"
    # Вложенный репо вне checkout (CI): тестов нет физически — пропуск
    # с честным warning (кейс setup-test 14.08).
    if not sdir.is_dir():
        return "warning", "projects/sherpa-voice нет (вложенный репо вне checkout) — пропуск"
    # Windows: run_tests.ps1 через PowerShell — не зависит от bash и WSL
    # (баг-репорт 2026-08-11: WSL-заглушка bash ломала run_tests.sh).
    # Git Bash + run_tests.sh — fallback, если .ps1 нет.
    if _compat.IS_NT:
        ps1 = sdir / "run_tests.ps1"
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if ps1.is_file() and ps:
            rc, out = _sh([ps, "-NoProfile", "-ExecutionPolicy", "Bypass",
                           "-File", str(ps1), "-Mode", "mirrors"], timeout=300)
            if rc != 0:
                return "error", f"run_tests.ps1 --mirrors: rc={rc} {out[:120]}"
            return "success", "run_tests.ps1 -Mode mirrors OK"
    runner = sdir / "run_tests.sh"
    if not runner.is_file():
        return "error", "run_tests.sh не найден"
    bash = _bash()
    if not bash:
        return ("warning",
                "bash не найден (Windows: поставь Git Bash) — тесты пропущены")
    rc, out = _sh([bash, str(runner), "--mirrors"], timeout=300)
    if rc != 0:
        return "error", f"run_tests --mirrors: rc={rc} {out[:120]}"
    return "success", "run_tests.sh --mirrors OK"

def check_canon_projects():
    """Канон без имён проектов: протокол не хардкодит проекты (id=484/485)."""
    t = ROOT / "scripts" / "tests" / "test_canon_no_projects.py"
    if not t.is_file():
        return "error", "test_canon_no_projects.py не найден"
    rc, out = _sh([sys.executable, str(t)], timeout=60)
    if rc != 0:
        return "error", f"канон содержит имена/пути проектов: {out[:160]}"
    return "success", "канон без имён проектов (белый список соблюдён)"

def check_skills_lint():
    """Скиллы канона валидны по спеке Agent Skills: frontmatter (name ==
    каталог, description с лимитами), атрибуция license/metadata.author.
    Битый frontmatter = скилл не грузится (баг-хант 12.08: 3 скилла падали
    из-за frontmatter) или не триггерится. Предупреждения (description
    длиннее 512 симв) — НЕ ошибки."""
    lint = ROOT / "scripts" / "tools" / "skills" / "lint_skills.py"
    if not lint.is_file():
        return "error", "lint_skills.py не найден"
    rc, out = _sh([sys.executable, str(lint)], timeout=60)
    if rc != 0:
        first = next((ln.strip() for ln in out.splitlines()
                      if ln.startswith("  ✗")), "")
        tail = first[:120] + ("…" if len(first) > 120 else "")
        return "error", f"ошибки в скиллах: {tail}"
    return "success", "скиллы канона валидны (spec-линт)"

def check_file_sizes():
    """Файлы в лимитах (god-файлы запрещены): hard-нарушения = error,
    soft = warning. Лимиты и baseline — scripts/tools/audit/check_file_sizes.py."""
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "tools" / "audit"))
        import check_file_sizes as cfs  # tools/ — после реорганизации scripts/
    except ImportError:  # pragma: no cover
        return "warning", "check_file_sizes.py не импортируется (scripts/tools/)"
    rows = cfs.collect(ROOT)
    errors, warnings, _info = cfs.gate(rows)
    if errors:
        sample = ", ".join(f"{r['rel_path']}:{r['lines']}" for r in errors[:3])
        return "error", f"god-файлы/рост выше hard: {sample}"
    if warnings:
        sample = ", ".join(f"{r['rel_path']}:{r['lines']}" for r in warnings[:3])
        return "warning", f"выше soft-лимита: {sample}"
    return "success", "файлы в лимитах (check_file_sizes)"

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


def check_layer_boundaries():
    """Слои не пересекаются: импорты между слоями — только
    документированные мосты (mcp→db-tools, mcp→scripts._compat,
    db-tools→scripts._compat; agent/ — автономен). Гардрейл от дрейфа
    (паттерн: layer-boundary гейты — codesentinel, research.db id=585)."""
    import sqlite3
    con = sqlite3.connect(ROOT / "db" / "aggg2.db")
    stem_layer = {}
    for rel in [r[0] for r in con.execute(
            "SELECT rel_path FROM files WHERE rel_path LIKE '%.py'")]:
        layer = rel.split("/")[0]
        if layer in ("mcp", "db-tools", "scripts", "agent", "harness"):
            stem = rel.rsplit("/", 1)[-1][:-3]
            stem_layer.setdefault(stem, set()).add(layer)
    allowed = {
        ("mcp", "db-tools"), ("mcp", "scripts"),
        ("db-tools", "scripts"), ("scripts", "scripts"),
        ("scripts", "db-tools"), ("scripts", "harness"),
        ("mcp", "harness"), ("harness", "harness"),
    }
    bad = []
    for rel, module in con.execute("SELECT rel_path, module FROM imports"):
        layer = rel.split("/")[0]
        if layer not in ("mcp", "db-tools", "scripts", "agent", "harness"):
            continue
        targets = stem_layer.get(module)
        if not targets:
            continue
        for target in targets:
            if target != layer and (layer, target) not in allowed:
                bad.append(f"{rel} -> {module}")
                break
    con.close()
    if bad:
        return "error", "слои пересекаются: " + "; ".join(sorted(set(bad))[:5])
    return "success", "слои не пересекаются (мосты документированы)"


def check_context_budget():
    """Контекст opencode в норме: ctx_probe (rules+skills+mcp) < 30k
    токенов. Дорогой промпт = внимание модели тонет (U-кривая)."""
    import subprocess
    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "tools" / "ctx_probe.py"),
             "--harness", "opencode"],
            capture_output=True, text=True, timeout=60)
        line = [ln for ln in r.stdout.splitlines() if ln.startswith("opencode")]
        if not line:
            return "error", "ctx_probe не дал строку opencode"
        total = int(line[0].split()[5])
        if total > 30000:
            return "warning", f"контекст opencode {total} токенов (> 30k)"
        return "success", f"контекст opencode ~{total} токенов"
    except Exception as e:  # noqa: BLE001 — диагностика, не блокируем
        return "warning", f"ctx_probe не отработал: {e!r}"


def check_dir_limits():
    """Лимиты каталогов (docs/canon/ARCHITECTURE.md): ≤ 15 файлов-братьев в
    каталоге слоя (не считая README/tests/кэшей). Паттерн индустрии:
    границы как гейт (Nx module boundaries, Packwerk, archgate)."""
    import os
    LIMIT = 15
    over = []
    for layer in ("mcp", "db-tools", "scripts", "scripts/install",
                  "scripts/doctor", "scripts/tools", "scripts/eval",
                  "harness", "docs"):
        d = ROOT / layer
        if not d.is_dir():
            continue
        try:
            files = [f for f in os.listdir(d)
                     if os.path.isfile(d / f) and not f.startswith(".")
                     and f != "README.md" and not f.endswith(".bak")]
        except OSError:
            continue
        if len(files) > LIMIT:
            over.append(f"{layer}: {len(files)} файлов (> {LIMIT})")
    if over:
        return "warning", "каталоги-переростки: " + "; ".join(over[:4])
    return "success", f"каталоги слоёв в лимите (≤ {LIMIT} файлов)"
