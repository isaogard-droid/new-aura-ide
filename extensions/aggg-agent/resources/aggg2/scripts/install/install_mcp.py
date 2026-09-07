#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Кроссплатформенный установщик MCP-серверов чулана в агентные харнесы.

Ставит наши MCP-серверы (agent-lsp, camoufox-ресёрч, code-review-graph,
db-tools) в конфиги харнесов, которые поддерживают MCP. Форматы взяты из
доков каждого харнеса; неподтверждённые харнесы честно пропускаются.

Кроссплатформенность (Linux/macOS/Windows):
- пути команд вычисляются от корня чулана (CHULAN), а не от {HOME}/aggg2 —
  алиас чулана может отсутствовать на свежей машине;
- venv разрешается платформенно: venv\\Scripts (nt) vs venv/bin (posix);
- для opencode выбирается ЖИВОЙ файл конфига: opencode.json при наличии,
  иначе opencode.jsonc (на Windows живёт .json, на Linux — .jsonc);
- повторные запуски не накапливают устаревшие записи: все известные ключи
  SERVERS удаляются перед записью, включая отфильтрованные платформой.

Запуск:
    python3 install_mcp.py --list                 # что куда ставится
    python3 install_mcp.py                        # установить всё возможное
    python3 install_mcp.py --harness opencode deepcode
    python3 install_mcp.py --server camoufox


Резка soft-файла (docs/canon/FILE-SIZE.md): форматы записи конфигов харнесов
(apply_* + APPLY) вынесены в mcp_appliers.py — перенос verbatim.
Здесь: реестр серверов/харнесов (CHULAN..HARNESSES), backup, check_deps
и CLI (main).


"""
import argparse
import json
import os
import shutil
import subprocess
import sys

# Windows-консоль по умолчанию cp1251 — русский вывод падает с
# UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass


# Карта после резки (docs/canon/FILE-SIZE.md): реестр серверов/харнесов и CLI живут
# здесь; форматы записи конфигов (apply_* + APPLY) — в mcp_appliers.py
# (перенос verbatim, импортёры install_mcp не меняются). _known_server_names
# из реестра appliers берут на месте вызова: from install_mcp import
# _known_server_names (в apply_opencode/apply_hermes).
# Паттерн db-tools/: свой каталог — соседи (mcp_appliers),
# scripts/ — кирпичи канона (jsonc_edit/_compat).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


CHULAN = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
MCP_DIR = os.path.join(CHULAN, "mcp")
IS_NT = os.name == "nt"
HOME = os.path.expanduser("~")

# Имена всех серверов чулана: при повторном запуске эти ключи удаляются из
# конфигов перед записью (в т.ч. убранные платформенным фильтром), чтобы
# устаревшие записи с путями прежних прогонов не оставались.
# Базовые (core) серверы воркспейса. Полный список — _known_server_names():
# core + автообнаруженные серверы агентов (agent/*/mcp/), см. _agent_servers.
SERVER_NAMES = ["agent-lsp", "battle", "camoufox", "code-review-graph",
                "db-tools", "semble"]


def _venv_dir():
    """Общий venv воркспейса: ~/.venvs/aggg2 (вынесенный из папки, чтобы
    проект шерился чисто). Создаётся setup.py (ensure_env)."""
    return os.path.join(os.path.expanduser("~"), ".venvs", "aggg2")


def _venv_python():
    if IS_NT:
        return os.path.join(_venv_dir(), "Scripts", "python.exe")
    return os.path.join(_venv_dir(), "bin", "python")

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


def _venv_bin(name):
    if IS_NT:
        return os.path.join(_venv_dir(), "Scripts", f"{name}.exe")
    return os.path.join(_venv_dir(), "bin", name)


def _agent_lsp():
    """agent-lsp: официальный скрипт ставит в /usr/local/bin (darwin/linux);
    на Windows — релизный архив (agent-lsp_windows_amd64.zip, Windows
    официально поддерживается). Сначала ищем в PATH, потом рядом с сервером."""
    exe = "agent-lsp.exe" if IS_NT else "agent-lsp"
    found = shutil.which(exe)
    if found:
        return found
    local = os.path.join(MCP_DIR, "agent-lsp", exe)
    if os.path.isfile(local):
        return local
    if IS_NT:
        return local  # честно укажем ожидаемое место, не выдумывая
    return "/usr/local/bin/agent-lsp"


def _agent_servers():
    """Автообнаружение MCP-серверов агентов (convention over configuration,
    паттерн Claude Code plugins: компоненты в дефолтных каталогах
    обнаруживаются сами, манифест — только метаданные).

    Конвенция: agent/<имя>/mcp/*.py|*.sh = сервер (имя = имя файла).
    Allow-list доставки — agent/<имя>/mcp/manifest.json:
        {"<сервер>": {"harnesses": ["opencode", ...]}}
    По умолчанию (нет записи) — ["opencode"] (least privilege).
    Новый MCP у агента подхватывается БЕЗ правки этого скрипта.
    """
    py = _venv_python()
    servers = {}
    agents_dir = os.path.join(CHULAN, "agent")
    if not os.path.isdir(agents_dir):
        return servers
    for name in sorted(os.listdir(agents_dir)):
        mcp_dir = os.path.join(agents_dir, name, "mcp")
        if not os.path.isdir(mcp_dir):
            continue
        manifest = {}
        mpath = os.path.join(mcp_dir, "manifest.json")
        if os.path.isfile(mpath):
            try:
                with open(mpath, encoding="utf-8") as f:
                    manifest = json.load(f) or {}
            except (OSError, ValueError):
                manifest = {}
        for fn in sorted(os.listdir(mcp_dir)):
            if fn == "manifest.json":
                continue
            if not fn.endswith((".py", ".sh")):
                continue
            full = os.path.join(mcp_dir, fn)
            if not os.path.isfile(full):
                continue
            sname = fn[:-3]  # имя без расширения
            meta = manifest.get(sname, {})
            # пустой "harnesses": [] = НЕ доставлять никуда (изоляция:
            # сервер живёт у субагента, тулы зовутся через FastMCP CLI);
            # отсутствие ключа = legacy-дефолт ["opencode"]
            harnesses = (meta.get("harnesses") or []
                          if "harnesses" in meta else ["opencode"])
            command = [full] if fn.endswith(".sh") else [py, full]
            servers[sname] = {"harnesses": list(harnesses),
                              "command": command}
    return servers


def _servers():
    """Команды серверов: абсолютные пути от корня чулана, платформенные
    venv-разрешения. MCP-серверы запускаются интерпретатором venv проекта —
    туда ставятся зависимости (см. mcp/requirements.txt).

    Core-серверы воркспейса — здесь; серверы АГЕНТОВ (agent/*/mcp/) —
    автообнаружением (_agent_servers): реестр не знает о конкретных
    агентах, он читает их папки при каждом запуске."""
    py = _venv_python()
    servers = {
        "agent-lsp": {
            "command": [_agent_lsp(), "--config",
                        os.path.join(MCP_DIR, "agent-lsp", "config.json")],
        },
        "camoufox": {
            "command": [py, os.path.join(MCP_DIR, os.path.join("camoufox", "camoufox_research.py"))],
        },
        "code-review-graph": {
            "command": [_venv_bin("code-review-graph"), "mcp"],
            # CRG определяет repo_root: env CRG_REPO_ROOT → git-root от cwd
            # → cwd (find_project_root, issue #155). Агентский харнес
            # запускается из HOME (не git-репо) — без явного корня тулы
            # читают ПУСТУЮ базу ~/.code-review-graph/ (грабля 13.08.2026).
            # В конфигах харнесов ключ называется по-разному: opencode —
            # "environment" (не "env"!), claude/codex/deepcode — "env".
            "env": {"CRG_REPO_ROOT": CHULAN},
        },
        "db-tools": {
            "command": [py, os.path.join(MCP_DIR, "db_tools_mcp.py")],
        },
        "battle": {
            "command": [py, os.path.join(MCP_DIR, "gui_battle_mcp.py")],
        },
        "semble": {
            "command": [py, os.path.join(MCP_DIR, "semble_mcp.py")],
        },
    }
    servers.update(_agent_servers())
    return servers


def _for_harness(servers, harness_name):
    """least privilege: сервер с allow-list 'harnesses' идёт только в
    разрешённые харнесы; без поля — core-сервер, всем (паттерн
    Core + project-specific). Чистая функция — тестируется."""
    return {sn: s for sn, s in servers.items()
            if "harnesses" not in s or harness_name in s["harnesses"]}


def _known_server_names():
    """Все известные имена серверов (core + автообнаруженные у агентов) —
    для чистки устаревших записей в конфигах харнесов."""
    return list(_servers())


def _opencode_file():
    """Живой файл конфига opencode: opencode.json при наличии, иначе
    opencode.jsonc (на Windows живёт .json, на Linux — .jsonc; запись в
    инертный файл означает, что серверы никогда не загрузятся)."""
    d = os.path.join(HOME, ".config", "opencode")
    for name in ("opencode.json", "opencode.jsonc"):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return os.path.join(d, "opencode.json")


HARNESSES = {
    "opencode": {"file": _opencode_file(), "kind": "opencode"},
    "claude": {"file": os.path.join(HOME, ".claude.json"), "kind": "claude"},
    "codex": {"file": os.path.join(HOME, ".codex", "config.toml"),
              "kind": "codex"},
    "deepcode": {"file": os.path.join(HOME, ".deepcode", "settings.json"),
                 "kind": "deepcode"},
    # codewhale: формат задокументирован (github.com/Hmbown/CodeWhale
    # docs/MCP.md) — ~/.codewhale/mcp.json, ключ servers, поля command/args/env.
    "codewhale": {"file": os.path.join(HOME, ".codewhale", "mcp.json"),
                  "kind": "codewhale"},
    # hermes: ~/.hermes/config.yaml, top-level блок mcp_servers (YAML);
    # схема: command (строка) + args + env (docs/reference/mcp-config-reference)
    "hermes": {"file": os.path.join(HOME, ".hermes", "config.yaml"),
               "kind": "hermes"},
    # antigravity/agy: общий ~/.gemini/config/mcp_config.json, mcpServers
    # (antigravity.google/docs/mcp) — у обоих один файл, идемпотентно
    "antigravity": {"file": os.path.join(HOME, ".gemini", "config",
                                          "mcp_config.json"),
                    "kind": "google-mcp"},
    "agy": {"file": os.path.join(HOME, ".gemini", "config",
                                 "mcp_config.json"),
            "kind": "google-mcp"},
    # gemini: ~/.gemini/settings.json, top-level mcpServers
    # (geminicli.com/docs/tools/mcp-server)
    "gemini": {"file": os.path.join(HOME, ".gemini", "settings.json"),
               "kind": "gemini"},
    # omp: ~/.omp/agent/mcp.json, mcpServers + type stdio
    # (can1357/oh-my-pi docs/mcp-config.md)
    "omp": {"file": os.path.join(HOME, ".omp", "agent", "mcp.json"),
            "kind": "omp-mcp"},
    # cursor: ~/.cursor/mcp.json (cursor.com/docs/cli/using: CLI читает
    # mcp.json; оmp docs: трансляция из ~/.cursor/mcp.json)
    "cursor": {"file": os.path.join(HOME, ".cursor", "mcp.json"),
               "kind": "mcp-json"},
    # windsurf: ~/.codeium/windsurf/mcp_config.json (omp docs/mcp-config.md —
    # трансляция; гайды windsurf mcp setup)
    "windsurf": {"file": os.path.join(HOME, ".codeium", "windsurf",
                                      "mcp_config.json"),
                 "kind": "mcp-json"},
    # kiro (Amazon): ~/.kiro/settings/mcp.json (kiro.dev/docs/mcp/
    # configuration — user level, mcpServers command/args/env)
    "kiro": {"file": os.path.join(HOME, ".kiro", "settings", "mcp.json"),
             "kind": "mcp-json"},
    # reasonix: отдельный MCP-конфиг, но схема не подтверждена — пропускается
    # crush: ключ mcp в ~/.config/crush/crush.json есть, схема записи не
    # подтверждена — пропускается (проверить при аудите)
}


def backup(path):
    if os.path.exists(path):
        bak = path + ".bak"
        shutil.copy2(path, bak)
        print(f"[~] бэкап -> {bak}")


from mcp_appliers import (  # форматы записи конфигов (вынесено, docs/canon/FILE-SIZE.md)
    APPLY,
    apply_claude,
    apply_codewhale,
    apply_codex,
    apply_deepcode,
    apply_gemini,
    apply_google_mcp,
    apply_hermes,
    apply_mcp_json,
    apply_omp_mcp,
    apply_opencode,
)

__all__ = [
    "APPLY",
    "HARNESSES",
    "SERVER_NAMES",
    "apply_claude",
    "apply_codex",
    "apply_codewhale",
    "apply_deepcode",
    "apply_gemini",
    "apply_google_mcp",
    "apply_hermes",
    "apply_mcp_json",
    "apply_omp_mcp",
    "apply_opencode",
    "backup",
    "check_deps",
    "main",
]


def check_deps():
    """Зависимости MCP-серверов живут в venv проекта (mcp, camoufox,
    code-review-graph). Если venv пуст — серверы не стартовали бы; говорим
    честно до записи конфигов, а не после."""
    py = _venv_python()
    if not os.path.isfile(py):
        print(f"[!] venv проекта не найден: {py}")
        print("    Создайте его и установите зависимости: см. mcp/requirements.txt")
        return
    try:
        r = subprocess.run(
            [py, "-c", "import mcp, camoufox"],
            capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"[!] не удалось проверить зависимости: {e}")
        return
    if r.returncode != 0:
        print("[!] в venv проекта нет mcp/camoufox — серверы не запустятся.")
        print("    Установите: "
              + ("venv\\Scripts\\pip install -r mcp\\requirements.txt"
                 if IS_NT else "venv/bin/pip install -r mcp/requirements.txt"))
        print("    Браузер: " + ("python -m camoufox fetch" if IS_NT
                                 else "venv/bin/python -m camoufox fetch"))
    else:
        print("[✓] зависимости MCP (mcp, camoufox) в venv на месте")


def main():
    ap = argparse.ArgumentParser(description="Установщик MCP-серверов")
    ap.add_argument("--list", action="store_true", help="показать план")
    ap.add_argument("--harness", nargs="*", help="только эти харнесы")
    ap.add_argument("--server", nargs="*", help="только эти серверы")
    args = ap.parse_args()

    servers = {k: v for k, v in _servers().items()
               if (not args.server) or k in args.server}
    harnesses = {k: v for k, v in HARNESSES.items()
                 if (not args.harness) or k in args.harness}

    if args.list:
        print(f"чулан: {CHULAN}")
        print(f"opencode: {'jsonc-файл' if HARNESSES['opencode']['file'].endswith('.jsonc') else 'json-файл'}"
              f" -> {HARNESSES['opencode']['file']}")
        for hn, h in harnesses.items():
            print(f"{hn:10s} -> {h['file']}")
            for sn, s in _for_harness(servers, hn).items():
                print(f"    {sn}: {' '.join(s['command'])}")
        return

    check_deps()

    ok, skipped = [], []
    for hn, h in harnesses.items():
        kind = h["kind"]
        if kind not in APPLY:
            skipped.append((hn, "формат MCP не задокументирован"))
            continue
        if hn == "cursor":
            # Cursor CLI: сторож-хуков нет (CLI не отправляет все события,
            # forum.cursor.com 148316) — MCP доставляется БЕЗ enforcement.
            # Явно предупредить, чтобы не казалось, что прошивка полная.
            print("[!] cursor: MCP ставится без сторожа-хуков (у Cursor CLI "
                  "хуки отправляют не все события) — прошивка неполная, "
                  "осознанно.")
        h_servers = _for_harness(servers, hn)
        if not h_servers:
            continue
        backup(h["file"])
        # clean_stale: полная установка (без --server) чистит устаревшие
        # записи известных серверов; частичная — только доставляет своё
        APPLY[kind](h["file"], h_servers, not bool(args.server))
        ok.append((hn, len(h_servers)))
        print(f"[✓] {hn}: {len(h_servers)} MCP-серверов -> {h['file']}")

    for hn, why in skipped:
        print(f"[!] {hn}: пропущен — {why}")
    print(f"\nитого: обновлено {len(ok)}, пропущено {len(skipped)}")
    if ok:
        # БАГ AGGG2-2026-08-16-01: у харнесов нет ретрая MCP-подключений —
        # сессия, стартовавшая до обновления конфига, держит «failed»
        # застывшим до перезапуска.
        print("[i] Перезапусти opencode (и другие харнесы), чтобы MCP-серверы "
              "подхватили новый конфиг: ретрая подключений у харнесов нет, "
              "статус failed застывает до перезапуска сессии")


if __name__ == "__main__":
    main()

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
