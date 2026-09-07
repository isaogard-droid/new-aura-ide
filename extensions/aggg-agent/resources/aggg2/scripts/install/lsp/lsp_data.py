#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""lsp_data — данные установщика LSP-серверов (install_lsp_servers.py).

Данные отделены от кода (паттерн declarative config, см. reshearch):
код — логика установки/проверки, здесь — ЧТО ставить и КАК запускать.
Правится без касания логики.

Пути в extra — шаблоны с резолверами (см. RESOLVERS в install_lsp_servers.py):
    {go_bin}/gopls, {npm_bin}/typescript-language-server, {win_get}/clangd.exe …
Резолвер, вернувший None (например, win_get на posix), делает шаблон
невалидным — такой путь пропускается.

Канон: research.db id=268 (вынос данных из install_lsp_servers.py).
"""

# npm-пакеты: (пакет, бинарь). typescript-language-server — особая логика
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# (typescript@5 + symlink), живёт в коде.
NPM_PACKAGES = [
    ("bash-language-server", "bash-language-server"),
    ("vscode-json-languageserver", "vscode-json-languageserver"),
    ("yaml-language-server", "yaml-language-server"),
    ("dockerfile-language-server-nodejs", "docker-langserver"),
]

# Аргументы запуска LSP-серверов (проверено эмпирически 08.2026 +
# npm README): --stdio — stdio-серверы (без аргументов yaml/json/docker
# падают: «Connection input stream is not set»); start — подкоманда
# bash-language-server (все клиенты: vim/neovim/eglot используют её).
SERVER_ARGS = {
    "pyright-langserver": ["--stdio"],
    "typescript-language-server": ["--stdio"],
    "yaml-language-server": ["--stdio"],
    "vscode-json-languageserver": ["--stdio"],
    "vscode-json-language-server": ["--stdio"],
    "docker-langserver": ["--stdio"],
    "bash-language-server": ["start"],
}

# Маппинг языков → серверы. names — бинари в порядке проверки; extra —
# шаблоны fallback-путей (резолвятся в коде).
LANG_SERVERS = [
    {"exts": ["go"], "names": ["gopls"],
     "extra": ["{go_bin}/gopls"]},
    {"exts": ["rs"], "names": ["rust-analyzer"],
     "extra": ["{cargo_bin}/rust-analyzer"]},
    {"exts": ["ts", "tsx", "js", "jsx"], "names": ["typescript-language-server"],
     "extra": ["{npm_bin}/typescript-language-server"]},
    {"exts": ["c", "cpp", "h", "hpp"], "names": ["clangd"],
     "extra": ["{win_get}/clangd.exe"]},  # win_get = None на posix → путь пропускается
    {"exts": ["sh", "bash"], "names": ["bash-language-server"],
     "extra": ["{npm_bin}/bash-language-server"]},
    {"exts": ["json"], "names": ["vscode-json-language-server",
                                 "vscode-json-languageserver"],
     "extra": ["{npm_bin}/vscode-json-languageserver"]},
    {"exts": ["yaml", "yml"], "names": ["yaml-language-server"],
     "extra": ["{npm_bin}/yaml-language-server"]},
    {"exts": ["dockerfile"], "names": ["docker-langserver"],
     "extra": ["{npm_bin}/docker-langserver"]},
    {"exts": ["lua"], "names": ["lua-language-server"],
     "extra": ["{local_bin}/lua-language-server",
               "{home}/lua-language-server/bin/lua-language-server.exe"]},
]

# clangd: менеджеры пакетов по ОС (порядок = приоритет fallback).
CLANGD_WINDOWS_PMS = [
    ("winget", ["install", "--id", "LLVM.clangd", "-e",
                "--accept-package-agreements",
                "--accept-source-agreements"]),
    ("scoop", ["install", "llvm"]),
    ("choco", ["install", "-y", "llvm"]),
]

CLANGD_LINUX_PMS = [
    ("dnf", ["dnf", "install", "-y", "clang-tools-extra"], True),   # sudo
    ("apt", ["apt-get", "install", "-y", "clangd"], True),          # sudo
    ("pacman", ["pacman", "-S", "--noconfirm", "clang"], False),
    ("apk", ["apk", "add", "clang-extra-tools"], False),
]

# Бинари для --check (план). Выводятся из LANG_SERVERS + pyright —
# дубль списка вручную не нужен (DRY).
def check_bins(lang_servers=None, extra=("pyright-langserver",)):
    """Уникальные имена бинарей для плана: из LANG_SERVERS + extra."""
    seen, out = set(), []
    for s in (lang_servers or LANG_SERVERS):
        for n in s["names"]:
            if n not in seen:
                seen.add(n)
                out.append(n)
    for n in extra:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
