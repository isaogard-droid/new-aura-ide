# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""harness_map — данные харнесов AGGG2.0 (HARNESSES, пути скиллов,
субагентов) + мелкие утилиты (expand, _warn_secrets).

Вынесено из install_agents.py механически (verbatim) — гейт god-файлов
(docs/canon/FILE-SIZE.md). install_agents.py реэкспортирует публичные имена."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # scripts/ — кирпичи канона
from pathlib import Path

# Субагенты харнессов (проверено ресёрчем 08.2026, research.db id=314/315/316):
# - opencode: ~/.config/opencode/agents/*.md (opencode.ai/docs/agents)
# - claude:   ~/.claude/agents/*.md (code.claude.com/docs/en/sub-agents)
# - codex:    ~/.codex/agents/*.toml (simonwillison.net codex-subagents;
#             схема TOML: deepwiki.com/proflead/codex-agents-library)
# - omp:      ~/.omp/agent/agents/*.md (can1357/oh-my-pi Task Delegation:
#             packages/coding-agent/src/task/agents.ts — frontmatter
#             name/description/tools/spawns/model/thinkingLevel/prewalk)
# - codewhale: ~/.codewhale/agents/*.toml (Hmbown/CodeWhale issues/3367:
#             user-defined personas v0.8.65, схема TOML
#             name/description/role_hint/model_class_hint/instructions/tools)
# - reasonix: профиль runAs: subagent через `reasonix subagent create`
#             (DeepSeek-Reasonix docs/SUBAGENT_PROFILES.md)
# - antigravity/agy: ~/.gemini/config/agents/*.md (блог Introducing Custom
#             Agents: frontmatter name/description/model/tools, флаги
#             mainAgent/subagent — наши md совместимы)
# - gemini: ~/.gemini/agents/*.md (guide Google Cloud «Mastering Gemini CLI
#             Subagents»: frontmatter name/description/tools/model)
# deepcode — субагентов НЕТ (только skills: deepcode.vegamo.cn docs
# agent-skills, подтверждено README deepcode-cli).
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


HARNESSES = [
    {
        "name": "opencode",
        "paths": {
            "posix": "~/.config/opencode/AGENTS.md",
            "nt": "%USERPROFILE%\\.config\\opencode\\AGENTS.md",
        },
        "skills": {
            "posix": "~/.config/opencode/skills/",
            "nt": "%USERPROFILE%\\.config\\opencode\\skills\\",
        },
        "agents": {
            "posix": "~/.config/opencode/agents/",
            "nt": "%USERPROFILE%\\.config\\opencode\\agents\\",
        },
        "source": "https://opencode.ai/docs/rules/",
        "install": {
            "posix": "curl -fsSL https://opencode.ai/install | bash",
            "nt": "npm i -g opencode-ai",  # офиц. методы (opencode.ai/download): curl/npm/bun/brew; install.ps1 не существует (404)
        },
        "repo": "https://opencode.ai",
    },
    {
        # OpenCode 2 (beta): читает ТЕ ЖЕ глобальные пути, что и v1
        # (migrate-v1: конфиг/AGENTS.md/скиллы/агенты совместимы) — поэтому
        # пути совпадают с записью "opencode" (идемпотентно). Отличия:
        # бинарь opencode2, установка через beta-тег, плагин прошивки V1
        # НЕ работает (breaking change — порт после стабилизации API).
        "name": "opencode2",
        "paths": {
            "posix": "~/.config/opencode/AGENTS.md",
            "nt": "%USERPROFILE%\\.config\\opencode\\AGENTS.md",
        },
        "skills": {
            "posix": "~/.config/opencode/skills/",
            "nt": "%USERPROFILE%\\.config\\opencode\\skills\\",
        },
        "agents": {
            "posix": "~/.config/opencode/agents/",
            "nt": "%USERPROFILE%\\.config\\opencode\\agents\\",
        },
        "source": "https://opencode.ai/v2/docs/migrate-v1",
        "install": {
            # офиц. метод из гайда миграции (beta-тег; v1 и v2 живут рядом)
            "posix": "npm install -g @opencode-ai/cli@beta",
            "nt": "npm install -g @opencode-ai/cli@beta",
        },
        "repo": "https://opencode.ai/v2/docs",
    },
    {
        "name": "claude",
        "paths": {
            "posix": "~/.claude/CLAUDE.md",
            "nt": "%USERPROFILE%\\.claude\\CLAUDE.md",
        },
        "skills": {
            "posix": "~/.claude/skills/",
            "nt": "%USERPROFILE%\\.claude\\skills\\",
        },
        "agents": {
            "posix": "~/.claude/agents/",
            "nt": "%USERPROFILE%\\.claude\\agents\\",
        },
        "source": "docs.anthropic.com (Claude Code memory)",
        "install": {
            "posix": "npm install -g @anthropic-ai/claude-code",
            "nt": "npm install -g @anthropic-ai/claude-code",
        },
        "repo": "https://docs.anthropic.com/en/docs/claude-code/setup",
    },
    {
        "name": "codex",
        "paths": {
            "posix": "~/.codex/AGENTS.md",
            "nt": "%USERPROFILE%\\.codex\\AGENTS.md",
        },
        "skills": {
            "posix": "~/.codex/skills/",
            "nt": "%USERPROFILE%\\.codex\\skills\\",
        },
        "agents": {
            "posix": "~/.codex/agents/",
            "nt": "%USERPROFILE%\\.codex\\agents\\",
        },
        "source": "https://learn.chatgpt.com/docs/agent-configuration/agents-md",
        "install": {
            "posix": "npm install -g @openai/codex",
            "nt": "npm install -g @openai/codex",
        },
        "repo": "https://github.com/openai/codex",
    },
    {
        "name": "reasonix",
        "paths": {
            "posix": "~/.reasonix/AGENTS.md",
            "nt": None,  # не подтверждено для Windows
        },
        "skills": {
            "posix": "~/.reasonix/skills/",
            "nt": "%USERPROFILE%\\.reasonix\\skills\\",
        },  # подтверждено фактом на машине: ~/.reasonix/skills/ существует (reverser);
        # registry (reasonix.io/skills/) — для публикации, локально читает skills/ и ~/.agents/skills
        "source": "факт с машины (~/.reasonix/AGENTS.md и ~/.reasonix/skills/ существуют)",
        "install": {
            "posix": "npm install -g reasonix",
            "nt": "npm install -g reasonix",
        },
        "repo": "npm: reasonix (cache-first DeepSeek coding agent)",
    },
    {
        "name": "codewhale",
        "paths": {
            "posix": "~/.codewhale/AGENTS.md",
            "nt": "%USERPROFILE%\\.codewhale\\AGENTS.md",
        },
        "skills": {
            "posix": "~/.codewhale/skills/",
            "nt": "%USERPROFILE%\\.codewhale\\skills\\",
        },
        "agents": {
            "posix": "~/.codewhale/agents/",
            "nt": "%USERPROFILE%\\.codewhale\\agents\\",
        },
        "source": "docs/CONFIGURATION.md: AGENTS.md читается в репах; глобально подключается через instructions = [...] в ~/.codewhale/config.toml",
        "install": {
            "posix": "npm install -g codewhale",
            "nt": "npm install -g codewhale",
        },
        "repo": "https://github.com/Hmbown/CodeWhale",
    },
    {
        "name": "omp",
        "paths": {
            "posix": "~/.omp/agent/AGENTS.md",
            "nt": "%USERPROFILE%\\.omp\\agent\\AGENTS.md",
        },
        "skills": {
            "posix": "~/.omp/agent/skills/",
            "nt": "%USERPROFILE%\\.omp\\agent\\skills\\",
        },
        "agents": {
            "posix": "~/.omp/agent/agents/",
            "nt": "%USERPROFILE%\\.omp\\agent\\agents\\",
        },
        "source": "omp.sh (oh-my-pi): наследует правила .claude/.codex и читает AGENTS.md в репах; отдельный глобальный файл не задокументирован — кладём по соглашению",
        "install": {
            "posix": "bun install -g @oh-my-pi/pi-coding-agent  # или: curl -fsSL https://omp.sh/install | sh",
            "nt": "irm https://omp.sh/install.ps1 | iex",
        },
        "repo": "https://github.com/can1357/oh-my-pi",
    },
    {
        "name": "deepcode",
        "paths": {
            "posix": "~/.deepcode/AGENTS.md",
            "nt": "%USERPROFILE%\\.deepcode\\AGENTS.md",
        },
        "skills": {
            "posix": "~/.deepcode/skills/",
            "nt": "%USERPROFILE%\\.deepcode\\skills\\",
        },
        "source": "@vegamo/deepcode-cli (npm): читает глобальный ~/.deepcode/AGENTS.md (подтверждено исходником dist/cli.js:79870)",
        "install": {
            "posix": "npm install -g @vegamo/deepcode-cli",
            "nt": "npm install -g @vegamo/deepcode-cli",
        },
        "repo": "https://github.com/lessweb/deepcode-cli",
    },
    {
        # Antigravity 2.0 (IDE Google). Глобальные правила — ~/.gemini/GEMINI.md
        # (AGENTS.md не имеет глобального слота: читается из корня проекта, v1.20.3+).
        # src: GEMINI.md впрыскивается в КАЖДЫЙ промпт (системный слой) — туда идёт
        # МОНОЛИТ (персона + ядро правил), а не указатель: указатель осмыслен только
        # при доступе к воркспейсу AGGG2.0, полный CLAUDE.md для always-on тяжёл.
        # install нет: это GUI-приложение, ставится с antigravity.google —
        # install_harnesses.py пропускает запись без команды.
        "name": "antigravity",
        "src": "harness/monolith.md",
        "paths": {
            "posix": "~/.gemini/GEMINI.md",
            "nt": "%USERPROFILE%\\.gemini\\GEMINI.md",
        },
        "skills": {
            "posix": "~/.gemini/config/skills/",
            "nt": "%USERPROFILE%\\.gemini\\config\\skills\\",
        },
        "agents": {
            "posix": "~/.gemini/config/agents/",
            "nt": "%USERPROFILE%\\.gemini\\config\\agents\\",
        },
        "source": "antigravity.google/docs/rules-workflows + /docs/skills + блог Introducing Custom Agents (агенты: ~/.gemini/config/agents/)",
        "install": {
            "posix": None,  # GUI: качать Antigravity 2.0 с antigravity.google
            "nt": None,
        },
        "repo": "https://antigravity.google/docs",
    },
    {
        # Antigravity CLI (`agy`). Глобальные правила — тот же ~/.gemini/GEMINI.md
        # (монолит, см. комментарий записи antigravity).
        # Скиллы: docs/skills называет config/skills/, docs/cli/gcli-migration —
        # antigravity-cli/skills/; кладём в оба (идемпотентно, копия дёшева).
        "name": "agy",
        "src": "harness/monolith.md",
        "paths": {
            "posix": "~/.gemini/GEMINI.md",
            "nt": "%USERPROFILE%\\.gemini\\GEMINI.md",
        },
        "skills": {
            "posix": [
                "~/.gemini/antigravity-cli/skills/",
                "~/.gemini/config/skills/",
            ],
            "nt": [
                "%USERPROFILE%\\.gemini\\antigravity-cli\\skills\\",
                "%USERPROFILE%\\.gemini\\config\\skills\\",
            ],
        },
        "agents": {
            "posix": "~/.gemini/config/agents/",
            "nt": "%USERPROFILE%\\.gemini\\config\\agents\\",
        },
        "source": "antigravity.google/docs/cli/install + /docs/cli/gcli-migration + /docs/skills",
        "install": {
            "posix": "curl -fsSL https://antigravity.google/cli/install.sh | bash",
            "nt": "irm https://antigravity.google/cli/install.ps1 | iex",
        },
        "repo": "https://github.com/google-antigravity/antigravity-cli",
    },
    {
        # Gemini CLI (npm @google/gemini-cli). Глобальный контекст —
        # ~/.gemini/GEMINI.md (монолит, см. комментарий записи antigravity);
        # AGENTS.md — дефолтный контекст-файл воркспейса (PR #28240).
        # Скиллы читает из ~/.gemini/skills/ ИЛИ алиаса ~/.agents/skills/
        # (алиас приоритетнее) — общий каталог уже покрывает.
        # ВНИМАНИЕ: с 18.06.2026 индивиды переводятся на agy; gemini-cli
        # остаётся для Enterprise-лицензий и как OSS.
        "name": "gemini",
        "src": "harness/monolith.md",
        "paths": {
            "posix": "~/.gemini/GEMINI.md",
            "nt": "%USERPROFILE%\\.gemini\\GEMINI.md",
        },
        "skills": None,  # покрыт общим ~/.agents/skills/ (документированный алиас)
        "agents": {
            "posix": "~/.gemini/agents/",
            "nt": "%USERPROFILE%\\.gemini\\agents\\",
        },
        "source": "geminicli.com/docs/cli/gemini-md + google-gemini/gemini-cli PR #28240; субагенты: ~/.gemini/agents/*.md (guide Google Cloud)",
        "install": {
            "posix": "npm install -g @google/gemini-cli",
            "nt": "npm install -g @google/gemini-cli",
        },
        "repo": "https://github.com/google-gemini/gemini-cli",
    },
    {
        # Hermes Agent (Nous Research): CLI (`hermes`) и Desktop — один
        # агент-ядро и конфиг ~/.hermes/ (HERMES_HOME), поэтому одна запись.
        # Глобальный слот #1 системного промпта — ~/.hermes/SOUL.md (идентичность
        # инстанса): туда монолит (src). Глобального AGENTS.md нет — AGENTS.md/
        # CLAUDE.md читаются из корня проекта (цепочка git-root → cwd, first
        # match: .hermes.md → AGENTS.md → CLAUDE.md → .cursorrules).
        # Субагенты динамические (delegate_task) — файлового каталога не
        # задокументировано, agents пропущен. Desktop: `hermes desktop` после
        # CLI-установки или установщик с сайта (GUI).
        "name": "hermes",
        "src": "harness/monolith.md",
        "paths": {
            "posix": "~/.hermes/SOUL.md",
            "nt": "%USERPROFILE%\\.hermes\\SOUL.md",
        },
        "skills": {
            "posix": "~/.hermes/skills/",
            "nt": "%USERPROFILE%\\.hermes\\skills\\",
        },
        "source": "hermes-agent.nousresearch.com/docs (features/context-files, features/skills, features/personality, getting-started/installation)",
        "install": {
            "posix": "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash",
            "nt": "iex (irm https://hermes-agent.nousresearch.com/install.ps1)",
        },
        "repo": "https://github.com/NousResearch/hermes-agent",
    },
    {
        # Amp (Sourcegraph): глобальный AGENTS.md — ~/.config/amp/AGENTS.md
        # (ampcode.com/manual: всегда включается, как и ~/.config/AGENTS.md).
        # Скиллы: user-level ~/.config/agents/skills/ (ampcode.com/news/
        # agent-skills); Amp также читает ~/.claude/skills/ (совместимость).
        # MCP/субагенты: не задокументированы — пропускаем.
        "name": "amp",
        "paths": {
            "posix": "~/.config/amp/AGENTS.md",
            "nt": "%USERPROFILE%\\.config\\amp\\AGENTS.md",
        },
        "skills": {
            "posix": "~/.config/agents/skills/",
            "nt": "%USERPROFILE%\\.config\\agents\\skills\\",
        },
        "source": "ampcode.com/manual (AGENTS.md всегда включается) + ampcode.com/news/agent-skills (user-level ~/.config/agents/skills/)",
        "install": {
            "posix": "curl -fsSL https://ampcode.com/install.sh | bash",
            "nt": None,  # Windows: установщик не задокументирован — вручную
        },
        "repo": "https://ampcode.com/manual",
    },
    {
        # Cursor CLI (`agent`): глобального AGENTS.md нет — читает AGENTS.md/
        # CLAUDE.md из корня проекта (cursor.com/docs/cli/using) и правила
        # .cursor/rules/ — прошивать глобально нечего. Скиллы/субагенты не
        # задокументированы. MCP — отдельно в install_mcp.py (~/.cursor/mcp.json).
        # Запись нужна для install_harnesses (установка) и --list (карта).
        "name": "cursor",
        "paths": {"posix": None, "nt": None},
        "skills": None,
        "source": "cursor.com/docs/cli/using: AGENTS.md/CLAUDE.md из корня проекта, глобального нет (ничего не пишем); MCP — install_mcp.py",
        "install": {
            "posix": "curl https://cursor.com/install -fsS | bash",
            "nt": "irm 'https://cursor.com/install?win32=true' | iex",
        },
        "repo": "https://cursor.com/docs/cli",
    },
    {
        # Windsurf (IDE/CLI): глобальные правила — ~/.codeium/windsurf/memories/
        # global_rules.md (лимит 6000 симв.; монолит 4КБ — влезает). MCP —
        # install_mcp.py (~/.codeium/windsurf/mcp_config.json). Скиллы/
        # субагенты не задокументированы.
        "name": "windsurf",
        "src": "harness/monolith.md",
        "paths": {
            "posix": "~/.codeium/windsurf/memories/global_rules.md",
            "nt": "%USERPROFILE%\\.codeium\\windsurf\\memories\\global_rules.md",
        },
        "skills": None,
        "source": "гайды Windsurf rules (thepromptshelf: ~/.codeium/windsurf/memories/global_rules.md, лимит 6000 симв.)",
        "install": {
            "posix": None,  # ставится с windsurf.com (IDE/CLI) — команды нет
            "nt": None,
        },
        "repo": "https://windsurf.com",
    },
    {
        # GitHub Copilot CLI: пользовательские инструкции —
        # ~/.copilot/copilot-instructions.md (docs.github.com add-custom-
        # instructions, user-level) — туда монолит. Субагенты —
        # ~/.copilot/agents/*.agent.md (docs.github.com create-custom-agents-
        # for-cli). AGENTS.md/CLAUDE.md/GEMINI.md читает из репо сам.
        # Скиллы/MCP не задокументированы.
        "name": "copilot",
        "src": "harness/monolith.md",
        "paths": {
            "posix": "~/.copilot/copilot-instructions.md",
            "nt": "%USERPROFILE%\\.copilot\\copilot-instructions.md",
        },
        "skills": None,
        "agents": {
            "posix": "~/.copilot/agents/",
            "nt": "%USERPROFILE%\\.copilot\\agents\\",
        },
        "source": "docs.github.com/en/copilot (add-custom-instructions: user-level ~/.copilot/copilot-instructions.md; create-custom-agents-for-cli: ~/.copilot/agents/*.agent.md)",
        "install": {
            "posix": "npm install -g @github/copilot",
            "nt": "npm install -g @github/copilot",
        },
        "repo": "https://github.com/github/copilot-cli",
    },
]

# Имена харнессов (для парсинга файлов субагентов <имя>.<харнес>.<ext>)
HARNESS_NAMES = {h["name"] for h in HARNESSES}

# Общий стандарт Agent Skills (zed, deepcode shared, omp и др.) —
# кладём канон скиллов и туда, чтобы они работали в любом совместимом харнесе.
AGENTS_SKILLS_DIRS = {
    "posix": "~/.agents/skills/",
    "nt": "%USERPROFILE%\\.agents\\skills\\",
}


def expand(p, platform):
    """Превращает шаблон пути (с ~ и %USERPROFILE%) в абсолютный путь."""
    if not p:
        return None
    if platform == "nt":
        up = os.environ.get("USERPROFILE") or str(Path.home())
        p = p.replace("%USERPROFILE%", up)
    else:
        # expanduser вместо replace("~"): не трогает ~ в середине строки
        p = str(Path(p).expanduser())
    return Path(p)


_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),            # OpenAI-style
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),     # GitHub tokens
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),               # AWS access key
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def _warn_secrets(label, text):
    """Предупреждение, если контент похож на реальный секрет (канон:
    только плейсхолдеры — CLAUDE.md п.10). Не блокирует, только сигнал."""
    for pat in _SECRET_PATTERNS:
        m = pat.search(text)
        if m:
            print(f"[!] {label}: похоже на секрет ({m.group(0)[:12]}…) — "
                  f"канон: только плейсхолдеры (YOUR_API_KEY)",
                  file=sys.stderr)
            return

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
