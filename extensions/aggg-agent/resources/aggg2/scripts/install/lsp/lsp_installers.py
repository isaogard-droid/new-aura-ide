#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


# Оригинал от https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна и лучше предыдущей.


"""Установщики LSP-серверов (npm/go/rustup/pipx/winget/GitHub release).

Вынесено из install_lsp_servers.py (резка soft-файла, docs/canon/FILE-SIZE.md:
per-concern модули + тонкий barrel, перенос verbatim). Отдельный concern:
установка конкретных серверов — без генерации config.json и CLI.
"""


import os
import platform
import shutil
import subprocess
import sys
from contextlib import suppress
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))  # scripts/ — кирпичи канона
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _compat  # noqa: E402 — общий кроссплатформенный модуль (run)
from lsp_data import (  # noqa: E402
    CLANGD_LINUX_PMS,
    CLANGD_WINDOWS_PMS,
    NPM_PACKAGES,
)
from lsp_env import (  # noqa: E402
    ARCH,
    HOME,
    IS_CI,
    IS_NT,
    LOCAL_BIN,
    WORKSPACE_VENV_BIN,
    _npm_cmd,
    cargo_bin,
    go_bin,
    have,
    run,
)


def npm_install(pkg, binary):
    """npm i -g пакета, если бинарь ещё не в PATH."""
    if have(binary):
        print(f"   [–] уже есть: {binary}")
        return
    r = run([_npm_cmd(), "install", "-g", pkg])
    print(f"   [{'✓' if r else '!'}] {binary} (npm i -g {pkg})"
          + ("" if r else " — не удалось"))


# --- 1. npm-серверы (все ОС) ---
def install_npm_servers():
    for pkg, binary in NPM_PACKAGES:
        npm_install(pkg, binary)
    if have("typescript-language-server"):
        print("   [–] уже есть: typescript-language-server")
    else:
        # ГРАБЛЯ: npm i -g typescript ставит TS7 (Go-порт) — в нём нет
        # lib/tsserver.js, tsserver падает. Нужен классический typescript@5.
        ok = run([_npm_cmd(), "install", "-g",
                  "typescript-language-server", "typescript@5"])
        print(f"   [{'✓' if ok else '!'}] typescript-language-server + "
              f"typescript@5 (npm)")
    # tsserver ищет typescript рядом с собой (createRequire от cli.mjs);
    # npm install внутри глобального пакета падает («Cannot read properties
    # of null») — вместо этого symlink на глобальный typescript.
    ts_server = shutil.which("typescript-language-server")
    if ts_server:
        ts_dir = Path(ts_server).resolve().parent.parent
        ts_lib = ts_dir.parent / "typescript"
        target = ts_dir / "node_modules" / "typescript"
        if (ts_lib / "lib" / "tsserver.js").is_file() and not target.exists():
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(ts_lib, target)
                print("   [✓] symlink typescript -> "
                      "typescript-language-server/node_modules")
            except OSError:
                print("   [!] symlink не создался — tsserver может не найти "
                      "typescript (доктор покажет)")


# --- 2. gopls (Go) ---
def install_gopls():
    if have("gopls") or (go_bin() / "gopls").is_file():
        print("   [–] уже есть: gopls")
        return
    if have("go"):
        ok = run(["go", "install", "golang.org/x/tools/gopls@latest"])
        print(f"   [{'✓' if ok else '!'}] gopls (go install)")
    else:
        print("   [!] gopls: go не установлен")


# --- 3. rust-analyzer (Rust) ---
def install_rust_analyzer():
    if have("rust-analyzer"):
        r = _compat.run(["rust-analyzer", "--version"])
        if r.returncode == 0:
            print("   [–] уже есть: rust-analyzer")
            return
        print("   [!] rust-analyzer сломан — переустанавливаю компонент")
    if have("rustup"):
        ok = run(["rustup", "component", "add", "rust-analyzer"])
        print(f"   [{'✓' if ok else '!'}] rust-analyzer (rustup component)")
    else:
        print("   [!] rust-analyzer: rustup не установлен")


# --- 4. pyright (Python) — ГЛОБАЛЬНО, как в индустрии (npm i -g pyright /
#     pipx / pip --user). PEP 668 блокирует системный pip на современных
#     Linux — поэтому не pip в систему. npm первый: он всё равно нужен
#     скрипту для 5 других серверов, и pyright из npm официальный
#     (microsoft/pyright docs/installation.md) ---
def install_pyright():
    if have("pyright-langserver"):
        print("   [–] уже есть: pyright-langserver")
        return
    if have("npm"):
        ok = run([_npm_cmd(), "install", "-g", "pyright"])
        print(f"   [{'✓' if ok else '!'}] pyright-langserver (npm i -g pyright)")
        return
    if have("pipx"):
        ok = run(["pipx", "install", "pyright"])
        print(f"   [{'✓' if ok else '!'}] pyright-langserver (pipx)")
        return
    if have("python3"):
        ok = run([sys.executable, "-m", "pip", "install", "--user", "-q",
                  "pyright"])
        print(f"   [{'✓' if ok else '!'}] pyright-langserver (pip --user)")
        return
    pip = WORKSPACE_VENV_BIN / "pip"
    if pip.is_file():
        ok = run([str(pip), "install", "-q", "pyright"])
        print(f"   [{'✓' if ok else '!'}] pyright-langserver "
              f"(pip в ~/.venvs/aggg2)")
        return
    print("   [!] pyright: нет npm/pipx/python3 — поставь вручную")


# --- 5. clangd (C/C++) — пакет ОС; на CI пропускается ---
def install_clangd():
    if have("clangd"):
        print("   [–] уже есть: clangd")
        return
    if IS_CI:
        print("   [–] CI: clangd пропущен (тяжёлая установка)")
        return
    if IS_NT:
        # winget есть не везде (нет App Installer) — fallback на scoop/choco;
        # при отсутствии всех — честный пропуск (clangd можно поставить позже)
        for pm, pkg in CLANGD_WINDOWS_PMS:
            if not have(pm):
                continue
            ok = run([pm] + pkg)
            print(f"   [{'✓' if ok else '!'}] clangd ({pm})")
            if ok:
                break
        else:
            print("   [!] clangd: нет winget/scoop/choco — поставь вручную")
    elif platform.system() == "Darwin":
        ok = run(["brew", "install", "llvm"])
        print(f"   [{'✓' if ok else '!'}] clangd (brew llvm) — путь: "
              "/opt/homebrew/opt/llvm/bin/clangd")
    else:
        pm = next((p for p, _cmd, _sudo in CLANGD_LINUX_PMS
                   if have(p)), None)
        for p, cmd, sudo in CLANGD_LINUX_PMS:
            if p == pm:
                ok = run(cmd, sudo=sudo)
                print(f"   [{'✓' if ok else '!'}] clangd ({p})")
                break
        else:
            print("   [!] clangd: не знаю менеджер пакетов — поставь вручную")


# --- 6. lua-language-server (Lua) — GitHub release; на CI пропускается ---
def install_lua():
    if have("lua-language-server"):
        print("   [–] уже есть: lua-language-server")
        return
    if IS_CI:
        print("   [–] CI: lua-language-server пропущен (тяжёлая установка)")
        return
    import re
    import zipfile
    # platform.system() на Windows возвращает "Windows" (а не "win32" как
    # sys.platform) — нужен явный ключ "windows"; posix-ключи совпадают
    key = {"linux": "linux", "darwin": "darwin", "windows": "win32"} \
        .get(platform.system().lower())
    variant = "arm64" if ARCH in ("aarch64", "arm64") else "x64"
    r = _compat.run(
        ["curl", "-sL",
         "https://api.github.com/repos/LuaLS/lua-language-server/releases/latest"])
    # Windows-релизы LuaLS — только .zip (win32-x64.zip), posix — .tar.gz.
    # raw-строки: один бэкслеш (r"\.zip"), двойной матчил бы литеральный \.
    # _compat.run: utf-8 + errors=replace — на Windows decode-ошибка в
    # reader-потоке давала r.stdout=None → «ассет не найден» (BUG-4).
    ext = r"\.zip" if IS_NT else r"\.tar\.gz"
    m = re.search(rf'https://[^"]*{key}-{variant}{ext}', r.stdout or "")
    if not m:
        print("   [!] lua-language-server: не удалось получить релиз "
              "(ассет не найден)")
        return
    dest = (HOME / "lua-language-server" if IS_NT
            else HOME / ".local" / "opt" / "lua-language-server")
    dest.mkdir(parents=True, exist_ok=True)
    tmp = HOME / ".cache" / ("lua-ls.zip" if IS_NT else "lua-ls.tar.gz")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    if subprocess.run(["curl", "-sL", m.group(0), "-o", str(tmp)],
                      capture_output=True, check=False).returncode != 0:
        print("   [!] lua-language-server: скачивание не удалось")
        return
    if IS_NT:
        with zipfile.ZipFile(tmp) as z:
            z.extractall(dest)
    else:
        import tarfile
        with tarfile.open(tmp) as t:  # nosemgrep: trailofbits.python.tarfile-extractall-traversal.tarfile-extractall-traversal
            # filter="data" закрывает traversal; nosemgrep — правило не
            # распознаёт filter-митигацию (semgrep 12.08.2026)
            t.extractall(dest, filter="data")  # nosemgrep: trailofbits.python.tarfile-extractall-traversal
    tmp.unlink(missing_ok=True)
    if IS_NT:
        print("   [✓] lua-language-server -> " + str(dest))
    else:
        bin_dir = dest / "bin" / "lua-language-server"
        LOCAL_BIN.mkdir(parents=True, exist_ok=True)
        (LOCAL_BIN / "lua-language-server").unlink(missing_ok=True)
        os.symlink(bin_dir, LOCAL_BIN / "lua-language-server")
        print("   [✓] lua-language-server (GitHub release)")


# --- 7. все бинари в один PATH-каталог (~/.local/bin) — posix ---
def link_all():
    if IS_NT:
        return
    for src in (go_bin() / "gopls", cargo_bin() / "rust-analyzer"):
        if not src.is_file():
            continue
        LOCAL_BIN.mkdir(parents=True, exist_ok=True)
        with suppress(OSError):
            (LOCAL_BIN / src.name).unlink(missing_ok=True)
        os.symlink(src, LOCAL_BIN / src.name)
        print(f"   [✓] symlink {src.name} -> {LOCAL_BIN}")
