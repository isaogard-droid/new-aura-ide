#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""AGGG2.0-прошивка: инъекция ядра + enforcement запретов.

Три события, один скрипт (событие определяется по полям входа):
- UserPromptSubmit — читает core.txt и отдаёт его как additionalContext
  (добавляется системным напоминанием — НЕ заменяет сообщение пользователя);
- PreToolUse — сторож запретов из канона (паттерн индустрии: restraint rules
  need external enforcement, agentpatterns.ai): блокирует опасные команды
  (pkill без скобочного трюка, rm -rf, git reset --hard) и напоминает про
  QA/CHANGELOG при правках кода (allow + additionalContext).

Форматы подтверждены ресёрчем (08.2026):
- Claude Code: code.claude.com/docs/en/hooks (PreToolUse: permissionDecision
  allow/deny, additionalContext; matcher по tool_name);
- Codex: learn.chatgpt.com/docs/hooks (тот же формат вывода, PreToolUse с
  matcher, конфиг ~/.codex/hooks.json, требуется доверие через /hooks);
- Reasonix: internal/hook/hook.go (PreToolUse — gating: exit 2 = блок,
  stderr = причина; payload CamelCase: Event/ToolName/ToolArgs;
  конфиг ~/.reasonix/settings.json hooks.PreToolUse[match,command]);
- Codewhale: docs/HOOKS.md (tool_call_before: контекст в env
  DEEPSEEK_TOOL_NAME/DEEPSEEK_TOOL_ARGS; вердикт — stdout JSON
  {decision: allow|deny|ask, reason, additionalContext}, exit 2 = legacy deny;
  конфиг ~/.codewhale/config.toml [[hooks.hooks]]);
- omp (через omp-hooks, ZeR020): PreToolUse — блок только через exit 2 +
  stderr; stdout при exit 0 инжектится скрытым контекстом модели; режим
  включается env AGGG2_HOOK_MODE=omp (конфиг ~/.omp/agent/settings.json).
- Hermes (shell hooks): pre_tool_call — stdin {hook_event_name, tool_name,
  tool_input}, блок = stdout {"action": "block", "message"} + exit 2
  (agent/shell_hooks.py wire protocol; инъекция контекста — только
  pre_llm_call, не используется: ядро уже в SOUL.md слот #1).
- Gemini CLI (hooks): BeforeTool — matcher run_shell_command; блок =
  stdout {"decision": "deny", "reason"} + exit 2 (System Block, stderr;
  Golden Rule: stdout только JSON). Режим env AGGG2_HOOK_MODE=gemini
  (geminicli.com/docs/hooks/reference).
- Antigravity/agy (hooks.json): PreToolUse — matcher run_command; гейт =
  stdout {"decision": "deny", "reason"} (exit 0), payload camelCase
  {toolCall: {name, args: {CommandLine}}} (antigravity.google/docs/hooks).

Любая ошибка хука = allow (правило не должно ломать работу агента).

Запуск:
    echo '{}' | python3 aggg2_prompt_hook.py
    echo '{"tool_name":"Bash","tool_input":{"command":"pkill -f foo"}}' | python3 aggg2_prompt_hook.py
    echo '{"Event":"PreToolUse","ToolName":"bash","ToolArgs":"{\"command\":\"rm -rf /\"}"}' | python3 aggg2_prompt_hook.py
"""
import json
import os
import re
import sys
from contextlib import suppress
from pathlib import Path

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

HERE = Path(__file__).resolve().parent
CORE = HERE / "core.txt"
if not CORE.is_file():
    CORE = HERE.parent / "core.txt"  # запуск из источника (harness/hooks/): ядро в harness/

# Тулы, правящие код (напоминание QA + CHANGELOG). Имена Claude Code и Codex.
# + gemini-cli (edit, write_file), antigravity (write_to_file,
# replace_file_content, multi_replace_file_content), hermes (edit).
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch",
              "edit_file", "write_file", "Patch", "edit", "write_to_file",
              "replace_file_content", "multi_replace_file_content"}

# Имена шелл-тулов по харнесам: Claude/Codex/omp — "Bash"/"bash",
# Codewhale — "exec_shell", Reasonix — "bash", Hermes — "terminal",
# Gemini CLI — "run_shell_command", Antigravity/agy — "run_command".
SHELL_TOOLS = {"bash", "exec_shell", "terminal", "run_shell_command",
               "run_command"}

# Запреты Bash: (regex, тег). Блок = deny, работает в любом харнесе.
# Матчинг по ДЕОБФУСЦИРОВАННОЙ команде (_deobfuscate): IFS-трюки и
# кавычки-пустышки не должны обходить сторож (паттерн sentinel-hooks:
# red-team обфускаций rm${IFS}-rf, r''m — см. scripts/tests/test_red_team_gates.py).
BLOCK_RULES = [
    # pkill -f без скобочного трюка убивает сам bash хука (CLAUDE.md п.8):
    # deny, если после -f идёт паттерн не с `[` (трюк = '[x]...')
    (re.compile(r"pkill\s+(-[a-zA-Z0-9]+\s+)*-f\s+[\"']?[^\[\"']"), "PKILL-TRICK"),
    # rm -rf корня/дома/текущего каталога — необратимое (канон: подтверждение)
    (re.compile(r"rm\s+-[a-z]*r[a-z]*f?\s+/\*?(\s|$)"), "RM-RF-ОПАСНО"),
    (re.compile(r"rm\s+-[a-z]*r[a-z]*f?\s+~(\s|$)"), "RM-RF-ОПАСНО"),
    (re.compile(r"rm\s+-[a-z]*r[a-z]*f?\s+\.\.?/?(\s|$)"), "RM-RF-ОПАСНО"),
    (re.compile(r"git\s+reset\s+--hard"), "GIT-RESET-HARD"),
    # curl|bash — установка из неофициального источника (CLAUDE.md п.7б:
    # красный флаг, spotlighting/supply-chain; sentinel-hooks блокирует)
    (re.compile(r"curl\s+[^|&\n]*\|\s*(sudo\s+)?(ba|z|da|k|fi)?sh\b"), "CURL-BASH"),
]


def _deobfuscate(command: str) -> str:
    """Снять шелл-обфускации: ${IFS}/$IFS → пробел, ''/"" → пусто.
    r''m -rf / → rm -rf /; rm${IFS}-rf${IFS}/ → rm -rf /."""
    cmd = re.sub(r"\$\{?IFS\}?", " ", command)
    return cmd.replace("''", "").replace('""', "")

# Лимиты файлов (ЗЕРКАЛО scripts/tools/audit/check_file_sizes.py LIMITS — менять ОБА).
# Хук автономен: запускается из каталогов харнесов (~/.claude/hooks/ и т.п.),
# поэтому scripts/ не импортирует — константы продублированы осознанно.

QA_HINT = (
    "НАПОМИНАНИЕ: правишь код — после правок обязателен QA: get_diagnostics "
    "(agent-lsp) → ruff → semgrep → тесты; изменения кода → CHANGELOG "
    "(что/зачем/отвергнутое)."
)
DOC_HINT = (
    "НАПОМИНАНИЕ: правишь канон/скрипт AGGG2.0 — правило в каноне "
    "универсальное, БЕЗ имён конкретных проектов (проект-специфика — в "
    "файлы проекта); проверь СВЯЗАННЫЕ файлы: "
    "python3 scripts/tools/audit/doc_deps.py check <файл> (кто ссылается, зеркала, "
    "разнос). Не обновляй один файл, забыв связанные."
)
DOC_PATTERNS = (
    "AGENTS.md", "CLAUDE.md", "CYCLE.md", "docs/canon/CAMOUFOX.md",
    "docs/canon/DB-FIRST.md", "docs/canon/AGENT-LSP.md",
    "docs/canon/CODE-GRAPH.md", "docs/canon/SETUP.md", "CHANGELOG/",
    "harness/", "db-tools/", "scripts/", "VERSION",
)
PKILL_HINT = (
    "НАПОМИНАНИЕ: pkill -f убивает сам bash — всегда скобочный трюк: "
    'pkill -f "[х]..."'
)
QUARANTINE_HINT = (
    "AGGG2.0-nudge «карантин-первым»: скачанный сторонний скилл "
    "(npx skills add и т.п.) = НЕПРОВЕРЕННЫЙ код с правами агента — СРАЗУ "
    "перенеси из рантайм-каталогов (~/.agents/skills, ~/.claude/skills, "
    "~/.codex/skills, ~/.reasonix/skills, ~/.hermes/skills, "
    "~/.config/opencode/skills) в quarantine-skills/ (корень AGGG2.0). "
    "npx skills add ставит СРАЗУ в НЕСКОЛЬКО каталогов — чисти ВСЕ, канон "
    "оставляй в карантине. База db/quarantine-skills.db (build.py -r "
    "quarantine-skills -o ...) — по требованию, не автоматом; установка "
    "из карантина — только с согласия владельца + запись решения в "
    "research.db (docs/canon/skills.sh.md «Карантин скачанных скиллов»)."
)

# Веб-ресёрч: MCP-тулы Camoufox (mcp__camoufox__web_search и т.п.), CLI-формы
# и шелл-вызовы — маркеры сессии «ресёрч уже был» (гейт «ресёрч-первым»).

# Скиллы: поиск в ЛОКАЛЬНОЙ базе db/skills.db (search.py -b db/skills.db,
# MCP db-tools search db=skills) или загрузка скилла (Skill/skill tool) —
# маркеры сессии «локальный скилл искался» (nudge «скиллы-первым»,
# docs/canon/SKILLS-LOCAL.md). НЕ MCP skills-mcp — удалён, поиск через базу.
def _deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _allow(context: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "additionalContext": context,
        }
    }


# Гейты — соседний модуль; хук запускается standalone (хуки харнесов) —
# свой каталог в sys.path обязателен (иначе ModuleNotFoundError).
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from hook_gates import (
    _DEBUG_BASH,
    _QUARANTINE_BASH,
    _READ_TOOLS,
    _WEB_BASH,
    _analytics_research_nudge,
    _battle_test_nudge,
    _crg_commit_nudge,
    _curl_site_check,
    _dir_limit_hint,
    _dod_nudge,
    _file_size_verdict,
    _findings_nudge,
    _forgotten_findings_nudge,
    _idx_nudge,
    _internal_link_check,
    _local_databases_nudge,
    _log_skill_load,
    _lsp_nudge,
    _mark_code_change,
    _mark_crg,
    _mark_findings,
    _mark_local_databases,
    _mark_qa,
    _mark_semble,
    _mark_skills,
    _mark_tests_run,
    _mark_web,
    _output_secrets_check,
    _product_skill_nudge,
    _repeat_error_nudge,
    _secrets_check,
    _semble_nudge,
    _semble_read_nudge,
    _simplify_nudge,
    _skill_router,
    _skills_nudge,
    _sources_nudge,
    _test_nudge,
    _web_nudge,
    _wiki_grep_check,
    _windows_ci_nudge,
    _workspace_db_nudge,
)


def decide_pre_tool_use(tool_name: str, tool_input: dict,
                        session_id: str | None = None) -> dict:
    """Решение по вызову тула: deny (блок) или allow+напоминание. None = тишина."""
    command = str(tool_input.get("command") or "")
    _mark_skills(session_id, tool_name, command)
    _mark_local_databases(session_id, tool_name, command)
    _mark_findings(session_id, tool_name, command)
    _mark_crg(session_id, tool_name, command)
    _mark_semble(session_id, tool_name, command)
    _mark_qa(session_id, command)
    _mark_code_change(session_id, tool_name, command)
    _mark_tests_run(session_id, command)
    _log_skill_load(session_id, tool_name, tool_input)

    # Wiki-grep-block: grep/rg по Wiki/ = deny
    if tool_name.lower() in SHELL_TOOLS:
        wiki_block = _wiki_grep_check(command)
        if wiki_block:
            return _deny(wiki_block)
        # curl-блок для сайтов: curl https://site.com = deny
        curl_block = _curl_site_check(command)
        if curl_block:
            return _deny(curl_block)
        # CRG-гейт перед commit: git commit без CRG = nudge
        crg_nudge = _crg_commit_nudge(session_id, command)
        if crg_nudge:
            return _allow(crg_nudge)

    if (_mark_web(session_id, tool_name, command)
            and tool_name.lower() not in SHELL_TOOLS):
        # веб-ресёрч (Camoufox MCP): nudge «скиллы-первым» — локальный
        # скилл до веба (docs/canon/SKILLS-LOCAL.md); nudge «local-databases-первым» —
        # локальные базы знаний до веба (docs/canon/LOCAL_DATABASES.md); nudge
        # «находки-в-базу» — после N веб-вызовов напомнить о findings.py add
        nudges = []
        skills_n = _skills_nudge(session_id)
        if skills_n:
            nudges.append(skills_n)
        local_db_n = _local_databases_nudge(session_id)
        if local_db_n:
            nudges.append(local_db_n)
        findings_n = _findings_nudge(session_id)
        if findings_n:
            nudges.append(findings_n)
        return _allow(" ".join(nudges)) if nudges else None
    # bash с веб-маркером: сессия помечена, но блок-правила ниже всё
    # равно отрабатывают (pkill/rm в той же команде — deny)
    if tool_name.lower() not in SHELL_TOOLS:
        if tool_name in _READ_TOOLS:
            nudge = _idx_nudge(session_id, tool_name)
            if not nudge:
                # База уже была — следующая ступень лестницы: semble
                nudge = _semble_read_nudge(session_id, tool_name)
            if nudge:
                return _allow(nudge)
        if tool_name in EDIT_TOOLS:
            target = ""
            with suppress(Exception):
                target = str(tool_input.get("file_path") or tool_input.get("path")
                             or tool_input.get("filePath")
                             or tool_input.get("TargetFile") or "")
            fs = None
            if target:
                fs = _file_size_verdict(tool_input, target)
                if fs and fs[0] == "deny":
                    return _deny(fs[1])
                # Секреты-гейт: проверка контента на реальные API-ключи/пароли
                content = str(tool_input.get("content") or tool_input.get("new_string") or "")
                secret = _secrets_check(content)
                if secret:
                    secret_type, secret_val = secret
                    return _deny(
                        f"БЛОК: обнаружен потенциальный секрет ({secret_type}) в контенте. "
                        f"Используйте плейсхолдеры (YOUR_API_KEY, YOUR_PASSWORD и т.п.), "
                        f"даже в research.db. Секреты — только плейсхолдеры (core.txt п.6)."
                    )
                # Внутренние ссылки в продукте: research.db id=N в .md файлах = блок
                internal_link = _internal_link_check(content, target)
                if internal_link:
                    return _deny(internal_link)
            dir_hint = _dir_limit_hint(target) if target else ""
            hint0 = dir_hint
            if target and target.endswith((".py", ".js", ".ts", ".sh", ".go",
                                           ".rs", ".java", ".c", ".cpp")):
                hint = (hint0 + " " + QA_HINT) if dir_hint else QA_HINT
                web_nudge = _web_nudge(session_id)
                if web_nudge:
                    hint = web_nudge + " " + hint
                # Боевое крещение: если утверждает "улучшил/ускорил" → дай цифры
                battle_n = _battle_test_nudge(content)
                if battle_n:
                    hint += " " + battle_n
                # 5. Тесты после правки
                test_n = _test_nudge(session_id, tool_name, command)
                if test_n:
                    hint += " " + test_n
                # 7. Секреты в выводе
                output_secret = _output_secrets_check(content)
                if output_secret:
                    return _deny(output_secret)
                if fs and fs[0] == "nudge":
                    hint += " " + fs[1]
                return _allow(hint)
            if target and DOC_PATTERNS and any(
                    p in target.replace("\\", "/") for p in DOC_PATTERNS):
                hint = DOC_HINT
                if fs and fs[0] == "nudge":
                    hint += " " + fs[1]
                return _allow(hint)
            if fs and fs[0] == "nudge":
                return _allow(fs[1])
        return None
    command = ""
    with suppress(Exception):
        command = str(tool_input.get("command") or "")
    if not command:
        return None
    clean = _deobfuscate(command)
    for rule, tag in BLOCK_RULES:
        if rule.search(clean):
            if tag == "PKILL-TRICK":
                return _deny("БЛОК: pkill -f без скобочного трюка убьёт сам "
                             "bash. Используй pkill -f \"[х]...\".")
            if tag == "RM-RF-ОПАСНО":
                return _deny("БЛОК: rm -rf опасного пути. Необратимое — "
                             "подтверди у пользователя, сначала покажи цель.")
            if tag == "CURL-BASH":
                return _deny("БЛОК: curl | bash — установка из неофициального "
                             "источника (CLAUDE.md п.7б: красный флаг, "
                             "spotlighting). Используй официальные доки/репо.")
            return _deny("БЛОК: git reset --hard уничтожает незакоммиченное. "
                         "Используй git stash/rebase или подтверди у "
                         "пользователя.")
    if re.search(r"rm\s+-[a-z]*r", clean) or "git push --force" in clean:
        return _allow("НАПОМИНАНИЕ: необратимая/деструктивная команда — "
                      "убедись, что это осознанно, и цель показана "
                      "пользователю.")
    if "pkill" in clean and not re.search(r"-f\s+\"?\[", clean):
        return _allow(PKILL_HINT)
    if _QUARANTINE_BASH.search(command):
        # установка стороннего скилла: nudge «карантин-первым»
        # (скачал → сразу в quarantine-skills/, docs/canon/skills.sh.md)
        return _allow(QUARANTINE_HINT)
    # Windows/CI — загрузка скилла windows-encoding-fixes перед кодом
    windows_n = _windows_ci_nudge(command)
    if windows_n:
        return _allow(windows_n)
    # LSP для вопросов по коду: типы/связи/символы → agent-lsp
    lsp_n = _lsp_nudge(command)
    if lsp_n:
        return _allow(lsp_n)
    # Смысловой вопрос про код → semble (лестница code-search-ladder)
    semble_n = _semble_nudge(command)
    if semble_n:
        return _allow(semble_n)
    # 9. Забытый findings.py (проверяем ДО DoD)
    forgotten_n = _forgotten_findings_nudge(session_id)
    if forgotten_n:
        return _allow(forgotten_n)
    # 1. DoD перед "готово"
    dod_n = _dod_nudge(session_id, command)
    if dod_n:
        return _allow(dod_n)
    # 2. Ресёрч для аналитики
    analytics_n = _analytics_research_nudge(session_id, command)
    if analytics_n:
        return _allow(analytics_n)
    # 3. База для воркспейса
    workspace_n = _workspace_db_nudge(session_id, command)
    if workspace_n:
        return _allow(workspace_n)
    # 4. Скилл для типа задачи
    product_n = _product_skill_nudge(command)
    if product_n:
        return _allow(product_n)
    # 6. Повторная ошибка
    error_n = _repeat_error_nudge(session_id, command)
    if error_n:
        return _allow(error_n)
    # 8. Объяснение сложности
    simplify_n = _simplify_nudge(command)
    if simplify_n:
        return _allow(simplify_n)
    if (_WEB_BASH.search(command) or _DEBUG_BASH.search(command)):
        # веб-команда ИЛИ дебаг (журнал/логи): nudge «скиллы-первым»
        # (локальный скилл/чужие скиллы до фактов — грабля 17.08) +
        # nudge «local-databases-первым» (локальные базы знаний до веба) +
        # nudge «находки-в-базу» (после N веб-вызовов напомнить о findings.py add) +
        # nudge «норматив 10 источников» (если < 10 веб-вызовов)
        nudges = []
        skills_n = _skills_nudge(session_id)
        if skills_n:
            nudges.append(skills_n)
        local_db_n = _local_databases_nudge(session_id)
        if local_db_n:
            nudges.append(local_db_n)
        findings_n = _findings_nudge(session_id)
        if findings_n:
            nudges.append(findings_n)
        sources_n = _sources_nudge(session_id)
        if sources_n:
            nudges.append(sources_n)
        # 9. Забытый findings.py
        forgotten_n = _forgotten_findings_nudge(session_id)
        if forgotten_n:
            nudges.append(forgotten_n)
        if nudges:
            return _allow(" ".join(nudges))
    nudge = _idx_nudge(session_id, "bash", command)
    if not nudge:
        # База уже была — следующая ступень лестницы: semble (bash-чтение)
        nudge = _semble_read_nudge(session_id, "bash", command)
    if nudge:
        return _allow(nudge)
    return None


def decide_post_tool_use(tool_name: str, tool_input: dict,
                         tool_response: dict) -> str | None:
    """PostToolUse (Claude Code/Codex): skills_search.py завершился НЕ результатом
    (exit 2 «НЕ СМОГ» / «ничего не найдено» / трейсбек) → фидбек модели
    «фоллбэк на камуфокс-ресёрч скиллов ОБЯЗАТЕЛЕН» (core.txt п.3;
    паттерн: AWS AGENTOPS04-BP03 fallback chain, PostToolUse-фидбек)."""
    if tool_name != "Bash":
        return None
    cmd = str((tool_input or {}).get("command") or "")
    if "skills_search.py" not in cmd:
        return None
    text = json.dumps(tool_response or {}, ensure_ascii=False)
    if not re.search(r"не смог|ничего не найдено|Traceback|No such file", text):
        return None
    return ("AGGG2.0-nudge «фоллбэк скиллов»: skills_search.py НЕ дал результата "
            "(не смог/пусто) — ОБЯЗАТЕЛЕН камуфокс-ресёрч скиллов: web_search 3-5 "
            "запросов с разных сторон («<тема> agent skill», site:skills.sh, "
            "GitHub API) + fetch_page первоисточников (SKILL.md через raw GitHub). "
            "«Скрипт не работает» без фоллбэка = НЕ ответ "
            "(docs/canon/skills.sh.md «Порядок поиска», core.txt п.3)")


def main():
    from handlers_misc import (
        _antigravity_handle,
        _codewhale_handle,
        _codewhale_mode,
        _gemini_handle,
        _hermes_handle,
        _omp_handle,
        _omp_mode,
        _reasonix_tool_input,
        bind,
    )
    bind(decide_pre_tool_use, EDIT_TOOLS)
    data = {}
    with suppress(Exception):  # вход не критичен, ядро статично
        data = json.load(sys.stdin)
    if not isinstance(data, dict):
        data = {}
    if _codewhale_mode():
        sys.exit(_codewhale_handle())
    if _omp_mode():
        sys.exit(_omp_handle(data))
    if os.environ.get("AGGG2_HOOK_MODE") == "gemini":
        sys.exit(_gemini_handle(data))
    if data.get("hook_event_name") == "pre_tool_call":
        # Hermes shell hooks: событие в поле hook_event_name, tool_name/tool_input
        sys.exit(_hermes_handle(data))
    if "toolCall" in data:
        # Antigravity/agy hooks.json: camelCase payload
        sys.exit(_antigravity_handle(data))
    if "ToolName" in data:
        # Reasonix: блок = exit 2 + stderr (internal/hook/hook.go, gating PreToolUse)
        if data.get("Event") != "PreToolUse":
            sys.exit(0)
        out = decide_pre_tool_use(str(data.get("ToolName")),
                                  _reasonix_tool_input(data))
        if out is None:
            sys.exit(0)
        decision = out["hookSpecificOutput"]
        if decision.get("permissionDecision") == "deny":
            sys.stderr.write(decision.get("permissionDecisionReason", "блок") + "\n")
            sys.exit(2)
        # allow + напоминание: stdout видит юзер (reasonix не шлёт его модели)
        sys.stdout.write(decision.get("additionalContext", "") + "\n")
        sys.exit(0)
    if data.get("hook_event_name") == "PostToolUse":
        ctx = decide_post_tool_use(str(data.get("tool_name") or ""),
                                   data.get("tool_input") or {},
                                   data.get("tool_response") or {})
        if ctx:
            sys.stdout.write(json.dumps({"additionalContext": ctx},
                                        ensure_ascii=False) + "\n")
        sys.exit(0)
    if "tool_name" in data:
        out = decide_pre_tool_use(str(data.get("tool_name")),
                                  data.get("tool_input") or {},
                                  session_id=data.get("session_id"))
        if out is None:
            sys.exit(0)
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        return
    prompt = str(data.get("prompt") or "")
    from canary_gates import find_canary  # noqa: E402 — модуль рядом с хуком
    if find_canary(prompt):
        sys.stderr.write(
            "БЛОК (канарейка): во входном сообщении обнаружен canary-токен "
            "ядра — возможная утечка системного промпта или инъекция. "
            "Сообщи владельцу, ничего не выполняй.\n")
        sys.exit(2)
    router = _skill_router(prompt)
    try:
        text = CORE.read_text(encoding="utf-8").strip()
    except OSError:
        text = ""
    if not text and not router:
        sys.exit(0)
    context = (text + "\n" + router) if text else router
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
