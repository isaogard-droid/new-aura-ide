#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Единый кроссплатформенный установщик AGGG2.0 (Linux/macOS/Windows).

Запуск:
    python3 scripts/setup.py                 # ядро: venv, агенты, MCP, базы
                                             # (настраивает ТОЛЬКО уже
                                             # установленные харнесы)
    python3 scripts/setup.py --check         # только показать план
    python3 scripts/setup.py --with-harnesses # + установить новые CLI-харнесы
                                             #   (опционально, opt-in)

Вызывает готовые кроссплатформенные установщики из scripts/:
install_agents.py (разноска AGENTS.md), install_mcp.py (MCP в харнесы),
install_harnesses.py (харнесы — только по явному --with-harnesses);
затем собирает базы (db-tools/build.py).
Все шаги идемпотентные — можно перезапускать.
"""
import argparse
import contextlib
import shutil
import subprocess
import sys
from pathlib import Path

# Windows-консоль по умолчанию cp1251 — русский вывод падает с
# UnicodeEncodeError. Переключаем на UTF-8 (Python 3.7+).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001 — reconfigure опционален, без него живём
    pass
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


ROOT = Path(__file__).resolve().parent.parent  # корень AGGG2.0
PLATFORM = sys.platform  # win32 / linux / darwin


def run(script: str, label: str, extra: list[str] | None = None) -> None:
    """Запустить один установщик из scripts/install/ тем же интерпретатором."""
    print(f"\n[{label}] {script}")
    cmd = [sys.executable, str(ROOT / "scripts" / "install" / script)]
    if extra:
        cmd += extra
    subprocess.run(cmd, check=True)


def ensure_env() -> None:
    """Создать общий venv воркспейса (~/.venvs/aggg2, если нет) и поставить
    зависимости MCP. Venv вынесен из папки, чтобы проект шерился чисто."""
    venv = Path.home() / ".venvs" / "aggg2"
    if not venv.is_dir():
        print(f"\n[окружение] создаю venv: {venv}")
        venv.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = venv / ("Scripts" if PLATFORM == "win32" else "bin") / "pip"
    req = ROOT / "mcp" / "requirements.txt"
    if req.is_file():
        print(f"[окружение] ставлю зависимости: {req}")
        subprocess.run([str(pip), "install", "-q", "-r", str(req)], check=True)
    # Браузер веб-ресёрча (Camoufox) — качается один раз; при неудаче
    # предупреждаем, но установку не роняем (ресёрч можно докачать позже).
    py = venv / ("Scripts" if PLATFORM == "win32" else "bin") / "python"
    try:
        print("[окружение] браузер Camoufox (скачивается один раз, ~150MB)...")
        subprocess.run([str(py), "-m", "camoufox", "fetch"], check=True, timeout=600)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[!] браузер Camoufox не скачан ({type(e).__name__}); "
              f"докачать позже: {py} -m camoufox fetch")


def ensure_root_env() -> None:
    """Прописать AGGG2_ROOT (реальный корень ЭТОЙ машины) в окружение
    пользователя — паттерн индустрии (JAVA_HOME и т.п.): установщик сам
    узнаёт путь и пишет его, не переспрашивая. Windows — User env через
    реестр (как PYTHONUTF8); posix — export в ~/.bashrc и ~/.zshrc (если
    есть), fallback ~/.profile. Идемпотентно: тот же путь не трогаем,
    другой — обновляем."""
    target = str(ROOT)
    if PLATFORM == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment",
                                0, winreg.KEY_SET_VALUE) as k:
                try:
                    cur, _ = winreg.QueryValueEx(k, "AGGG2_ROOT")
                    if cur == target:
                        print(f"[root-env] AGGG2_ROOT уже прописан: {target}")
                        return
                except OSError:
                    pass
                winreg.SetValueEx(k, "AGGG2_ROOT", 0, winreg.REG_EXPAND_SZ, target)
            print(f"[root-env] AGGG2_ROOT -> User env (реестр): {target}")
        except OSError as e:
            print(f"[!] AGGG2_ROOT не прописан в реестр: {e}")
        return
    # posix: ~/.bashrc, ~/.zshrc (если есть), fallback ~/.profile
    home = Path.home()
    rcs = [p for p in (home / ".bashrc", home / ".zshrc", home / ".profile")
           if p.is_file()] or [home / ".bashrc"]
    line = f'export AGGG2_ROOT="{target}"'
    marker = "export AGGG2_ROOT="
    for rc in rcs:
        try:
            text = rc.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        has = any(ln.startswith(marker) for ln in lines)
        if has:
            replaced = [line if ln.startswith(marker) else ln for ln in lines]
            if replaced == lines:
                print(f"[root-env] AGGG2_ROOT уже прописан в {rc}")
                continue
        else:
            replaced = lines + [
                "",
                "# AGGG2.0: корень воркспейса (docs/canon/SETUP.md «Как находится корень»)",
                line,
            ]
        try:
            rc.write_text("\n".join(replaced) + "\n", encoding="utf-8")
            print(f"[root-env] AGGG2_ROOT -> {rc}: {target}")
        except OSError as e:
            print(f"[!] не удалось обновить {rc}: {e}")


def ensure_githooks() -> None:
    """Локальный pre-commit гейт god-файлов (docs/canon/FILE-SIZE.md): git config
    core.hooksPath .githooks — хук проверяет staged-файлы ДО коммита
    (паттерн индустрии: локальный гейт раньше CI, SonarQube new-code gate).
    Без .git (архив/распакованная копия) — пропуск: коммитов там не будет,
    остаются хук агента + CI + doctor."""
    if not (ROOT / ".git").exists():
        print("[githooks] нет .git (архив/копия) — пропуск")
        return
    hook = ROOT / ".githooks" / "pre-commit"
    if not hook.is_file():
        print("[githooks] .githooks/pre-commit не найден — пропуск")
        return
    with contextlib.suppress(OSError):
        hook.chmod(hook.stat().st_mode | 0o111)
    r = subprocess.run(["git", "config", "core.hooksPath", ".githooks"],
                       cwd=str(ROOT), capture_output=True)
    if r.returncode == 0:
        print("[githooks] core.hooksPath=.githooks (pre-commit гейт god-файлов)")
    else:
        print(f"[!] git config core.hooksPath не удался: "
              f"{r.stderr.decode('utf-8', 'replace')[:100]}")


def check_tools() -> None:
    """Диагностика системных инструментов (не устанавливаем — это забота
    менеджера пакетов ОС; здесь только честный статус)."""
    tools = {
        "python": sys.executable,
        "node": shutil.which("node"),
        "npm": shutil.which("npm"),
        "bun": shutil.which("bun"),
        "curl": shutil.which("curl"),
        "git": shutil.which("git"),
    }
    print("\n[инструменты]")
    for name, path in tools.items():
        print(f"  {name:8s}: {'OK ' + path if path else 'НЕТ'}")
    missing = [n for n, p in tools.items() if not p]
    if missing:
        print("  ! не найдены:", ", ".join(missing))
        print("    npm/node — нужны для npm-харнесов (claude/codex/...); "
              "bun — для omp; git — для обновления через pull")
        print("    Поставь runtime'ы одним скриптом: "
              "./scripts/bootstrap.sh (Windows: scripts/bootstrap.ps1) — "
              "mise поставит недостающие python/node/bun/go/rust без sudo")




# Оригинал от https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна и лучше предыдущей.
def main() -> None:
    global ROOT
    ap = argparse.ArgumentParser(description="Установщик AGGG2.0 (кроссплатформенный)")
    ap.add_argument("--check", action="store_true", help="только показать план")
    ap.add_argument("--skip-env", action="store_true", help="пропустить venv/зависимости")
    ap.add_argument("--skip-agents", action="store_true", help="пропустить разноску AGENTS.md")
    ap.add_argument("--skip-mcp", action="store_true", help="пропустить MCP-серверы")
    ap.add_argument("--skip-proshivka", action="store_true",
                    help="пропустить прошивку правил (build-промпт + плагин)")
    ap.add_argument("--skip-harnesses", action="store_true",
                    help="устарел: харнесы и так не ставятся по умолчанию")
    ap.add_argument("--with-harnesses", action="store_true",
                    help="поставить АГЕНТНЫЕ ХАРНЕСЫ (новые CLI). По умолчанию "
                         "выключено: setup.py настраивает только уже "
                         "установленные на машине харнесы, чужие CLI не "
                         "навязывает (opt-in, а не opt-out)")
    ap.add_argument("--skip-lsp", action="store_true", help="пропустить LSP-серверы (posix)")
    ap.add_argument("--skip-db", action="store_true", help="пропустить сборку баз")
    ap.add_argument("--skip-doctor", action="store_true", help="пропустить самодиагностику")
    args = ap.parse_args()

    # Корень опознаётся маркерами (_compat.chulan_root: любые 2 из
    # VERSION / db-tools/ / scripts/_compat.py), а не одним файлом —
    # переименованная папка и потеря одного маркера не ломают установку.
    try:
        from _compat import chulan_root
        root_found = chulan_root()
        if root_found.resolve() != ROOT.resolve():
            print(f"[i] корень AGGG2.0 по маркерам: {root_found}")
            ROOT = root_found
    except ImportError:  # старые структуры без scripts/_compat.py
        pass
    except RuntimeError as exc:
        print(f"[✗] {exc}")
        sys.exit(1)

    print(f"AGGG2.0: {ROOT}")
    print(f"Платформа: {PLATFORM}")
    check_tools()

    steps = []
    if not args.skip_env:
        steps.append(("ensure_env", "venv проекта + зависимости MCP"))
        steps.append(("ensure_root_env",
                      "прописать AGGG2_ROOT в окружение пользователя"))
    steps.append(("ensure_githooks",
                  "локальный pre-commit гейт god-файлов (core.hooksPath)"))
    if not args.skip_agents:
        steps.append(("install_agents.py", "разноска AGENTS.md + скиллов по харнесам"))
    if not args.skip_mcp:
        steps.append(("install_mcp.py", "MCP-серверы в харнесы"))
    if not args.skip_proshivka:
        steps.append(("install_proshivka.py",
                      "прошивка правил (build-промпт + плагин в opencode)"))
    if not args.skip_lsp:
        steps.append(("install_lsp_servers.py", "LSP-серверы для agent-lsp"))
    if args.with_harnesses:
        if shutil.which("bun") is None and PLATFORM != "win32":
            print("[!] харнесы пропущены: не найден bun (часть харнесов ставится "
                  "через него). Установить: curl -fsSL https://bun.sh/install | bash")
        else:
            steps.append(("install_harnesses.py", "агентные харнесы"))
    elif not args.skip_harnesses:
        # opt-in: чужие CLI не навязываем (dark-pattern «ставить за
        # пользователя» — плохая практика). Хочешь — одной командой.
        print("[i] харнесы не ставятся (опционально): "
              "python3 scripts/install/install_harnesses.py "
              "или setup.py --with-harnesses")
    if not args.skip_db:
        steps.append(("db-tools/build.py", "сборка баз индексов"))
    if not args.skip_doctor:
        steps.append(("doctor.py", "самодиагностика (зеркала/MCP/venv/тесты)"))

    if args.check:
        print("\nПлан:")
        for script, label in steps:
            print(f"  • {script} — {label}")
        if PLATFORM != "win32":
            print("  • vpnctl → ~/.local/bin (симлинк, если есть scripts/vpnctl)")
        else:
            print("  • vpnctl — пропускается на Windows (bash-скрипт)")
        print("\nНичего не выполнялось (--check).")
        return

    for script, label in steps:
        if script == "ensure_env":
            ensure_env()
        elif script == "ensure_root_env":
            ensure_root_env()
        elif script == "ensure_githooks":
            ensure_githooks()
        elif script.startswith("db-tools/"):
            print(f"\n[базы] {script}")
            subprocess.run([sys.executable, str(ROOT / script)], check=True)
        elif script == "install_harnesses.py":
            # Харнесы — опционально: зависят от внешних сервисов (npm, GitHub
            # API, bun). Сбой не должен ронять установку ядра воркспейса.
            try:
                run(script, label, None)
            except subprocess.CalledProcessError:
                print(f"[!] харнесы не поставились (внешний сервис/лимиты); "
                      f"повторить позже: {sys.executable} scripts/install/install_harnesses.py")
        elif script == "install_lsp_servers.py":
            # LSP-серверы тянут внешние сети (npm/go/rustup/GitHub) —
            # сбой не роняет установку ядра; скрипт идемпотентен, можно позже.
            print(f"\n[lsp] {script} — {label}")
            try:
                run(script, label, None)
            except subprocess.CalledProcessError:
                print("[!] LSP-серверы не поставились (сеть/менеджер пакетов); "
                      "повторить позже: python3 scripts/install/install_lsp_servers.py")
        elif script == "doctor.py":
            # Диагностика — информационная: показывает проблемы, но не
            # роняет установку (exit 1 у doctor = есть ошибки, а не сбой).
            print(f"\n[doctor] {label}")
            try:
                subprocess.run([sys.executable, str(ROOT / "scripts" / "doctor" / "doctor.py")],
                               check=False)
            except OSError as e:
                print(f"[!] doctor не запустился: {e}")
        else:
            run(script, label, ["--all", "--yes"] if script == "install_agents.py" else None)

    # vpnctl: симлинк на Linux/macOS (на Windows это bash-скрипт — пропускаем)
    if PLATFORM != "win32" and (ROOT / "scripts" / "vpnctl").is_file():
        bin_dir = Path.home() / ".local" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        link = bin_dir / "vpnctl"
        if link.is_symlink() or link.is_file():
            link.unlink()
        link.symlink_to(ROOT / "scripts" / "vpnctl")
        print(f"\n[vpnctl] {link} → {ROOT / 'scripts' / 'vpnctl'}")

    print("\n[✓] Установка завершена. Проверка: python3 db-tools/search.py \"тест\"")


if __name__ == "__main__":
    main()

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
