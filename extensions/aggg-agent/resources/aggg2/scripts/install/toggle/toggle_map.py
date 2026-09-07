# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""toggle_map — карта слоёв прошивки по харнесам для переключателя
(toggle_proshivka.py): конфиги, артефакты-файлы, каталоги скиллов и
субагентов. Каждая запись — (путь, владельцы): shared-файл выключается
только когда все владельцы off; ALL — только при --all.

Вынесено из toggle_proshivka.py механически (verbatim) — гейт god-файлов
(docs/canon/FILE-SIZE.md).
"""
from pathlib import Path

HOME = Path.home()

ALL = "ALL"


def _live_opencode_cfg() -> Path:
    """Живой файл конфига opencode (json при наличии, иначе jsonc)."""
    d = HOME / ".config" / "opencode"
    for name in ("opencode.json", "opencode.jsonc"):
        p = d / name
        if p.is_file():
            return p
    return d / "opencode.json"


# ---------- карта слоёв: (путь, владельцы) ----------

CONFIGS = [
    (_live_opencode_cfg(), "opencode", ("opencode",)),
    (HOME / ".claude" / "settings.json", "claude-settings", ("claude",)),
    (HOME / ".claude.json", "claude-mcp", ("claude",)),
    (HOME / ".codex" / "hooks.json", "hooks", ("codex",)),
    (HOME / ".codex" / "config.toml", "codex-toml", ("codex",)),
    (HOME / ".reasonix" / "settings.json", "reasonix", ("reasonix",)),
    (HOME / ".codewhale" / "config.toml", "codewhale-toml", ("codewhale",)),
    (HOME / ".codewhale" / "mcp.json", "mcp-servers", ("codewhale",)),
    (HOME / ".omp" / "agent" / "settings.json", "hooks", ("omp",)),
    (HOME / ".omp" / "agent" / "mcp.json", "mcp-mcpServers", ("omp",)),
    (HOME / ".hermes" / "config.yaml", "hermes-yaml", ("hermes",)),
    (HOME / ".gemini" / "settings.json", "gemini", ("gemini",)),
    (HOME / ".gemini" / "config" / "hooks.json", "agy-hooks",
     ("antigravity", "agy")),
    (HOME / ".gemini" / "config" / "mcp_config.json", "mcp-mcpServers",
     ("antigravity", "agy")),
    (HOME / ".deepcode" / "settings.json", "mcp-mcpServers", ("deepcode",)),
    (HOME / ".cursor" / "mcp.json", "mcp-mcpServers", ("cursor",)),
    (HOME / ".codeium" / "windsurf" / "mcp_config.json", "mcp-mcpServers",
     ("windsurf",)),
    (HOME / ".kiro" / "settings" / "mcp.json", "mcp-mcpServers", ("kiro",)),
]

ARTIFACTS = [
    (HOME / "AGENTS.md", (ALL,)),  # монолит — общий для всех харнесов
    (HOME / ".config" / "opencode" / "plugins" / "proshivka.js", ("opencode",)),
    (HOME / ".config" / "opencode" / "plugins" / "core.txt", ("opencode",)),
    (HOME / ".config" / "opencode" / "prompts" / "build.txt", ("opencode",)),
    (HOME / ".config" / "opencode" / "AGENTS.md", ("opencode",)),
    (HOME / ".claude" / "CLAUDE.md", ("claude",)),
    (HOME / ".claude" / "hooks" / "aggg2_prompt_hook.py", ("claude",)),
    (HOME / ".claude" / "hooks" / "core.txt", ("claude",)),
    (HOME / ".codex" / "AGENTS.md", ("codex",)),
    (HOME / ".codex" / "hooks" / "aggg2_prompt_hook.py", ("codex",)),
    (HOME / ".codex" / "hooks" / "core.txt", ("codex",)),
    (HOME / ".reasonix" / "AGENTS.md", ("reasonix",)),
    (HOME / ".reasonix" / "hooks" / "aggg2_prompt_hook.py", ("reasonix",)),
    (HOME / ".reasonix" / "hooks" / "core.txt", ("reasonix",)),
    (HOME / ".codewhale" / "AGENTS.md", ("codewhale",)),
    (HOME / ".codewhale" / "hooks" / "aggg2_prompt_hook.py", ("codewhale",)),
    (HOME / ".codewhale" / "hooks" / "core.txt", ("codewhale",)),
    (HOME / ".omp" / "agent" / "AGENTS.md", ("omp",)),
    (HOME / ".omp" / "hooks" / "aggg2_prompt_hook.py", ("omp",)),
    (HOME / ".omp" / "hooks" / "core.txt", ("omp",)),
    (HOME / ".hermes" / "SOUL.md", ("hermes",)),
    (HOME / ".hermes" / "hooks" / "aggg2_prompt_hook.py", ("hermes",)),
    (HOME / ".gemini" / "GEMINI.md", ("antigravity", "agy", "gemini")),
    (HOME / ".gemini" / "hooks" / "aggg2_prompt_hook.py",
     ("antigravity", "agy", "gemini")),
    (HOME / ".config" / "amp" / "AGENTS.md", ("amp",)),
    (HOME / ".copilot" / "copilot-instructions.md", ("copilot",)),
    (HOME / ".codeium" / "windsurf" / "memories" / "global_rules.md",
     ("windsurf",)),
]

SKILL_DIRS = [
    (HOME / ".config" / "opencode" / "skills", ("opencode",)),
    (HOME / ".claude" / "skills", ("claude",)),
    (HOME / ".codex" / "skills", ("codex",)),
    (HOME / ".reasonix" / "skills", ("reasonix",)),
    (HOME / ".codewhale" / "skills", ("codewhale",)),
    (HOME / ".omp" / "agent" / "skills", ("omp",)),
    (HOME / ".deepcode" / "skills", ("deepcode",)),
    (HOME / ".gemini" / "config" / "skills", ("antigravity", "agy")),
    (HOME / ".gemini" / "antigravity-cli" / "skills", ("agy",)),
    (HOME / ".hermes" / "skills", ("hermes",)),
    (HOME / ".config" / "agents" / "skills", ("amp",)),
    (HOME / ".agents" / "skills", (ALL,)),  # общий стандарт Agent Skills
]

AGENT_DIRS = [
    (HOME / ".config" / "opencode" / "agents", ("opencode",)),
    (HOME / ".claude" / "agents", ("claude",)),
    (HOME / ".codex" / "agents", ("codex",)),
    (HOME / ".codewhale" / "agents", ("codewhale",)),
    (HOME / ".omp" / "agent" / "agents", ("omp",)),
    (HOME / ".gemini" / "config" / "agents", ("antigravity", "agy")),
    (HOME / ".gemini" / "agents", ("gemini",)),
    (HOME / ".copilot" / "agents", ("copilot",)),
]

def _harness_names() -> list:
    """Все имена харнесов (объединение владельцев слоёв, без ALL)."""
    names = set()
    for _, _, owners in CONFIGS:
        names.update(n for n in owners if n != ALL)
    for _, owners in ARTIFACTS:
        names.update(n for n in owners if n != ALL)
    for _, owners in SKILL_DIRS:
        names.update(n for n in owners if n != ALL)
    for _, owners in AGENT_DIRS:
        names.update(n for n in owners if n != ALL)
    return sorted(names)


HARNESS_NAMES = _harness_names()
