---
name: windows-encoding-fixes
description: "Windows: кодировка stdout (cp1251/UTF-8, UnicodeEncodeError), CRLF/LF, BOM PowerShell 5.1, npm.cmd, venv Scripts vs bin, PYTHONIOENCODING/PYTHONUTF8. Проверено на 2 багрепортах Windows 10."
compatibility: Windows (win32), PowerShell 5.1, MINGW64, Python 3.12
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Windows: кодировки, консоль, кроссплатформенность

Из 2 багрепортов установки AGGG2.0 на Windows 10 (research.db id=141, 146). Каждая грабля — симптом/причина/фикс. Применять к ЛЮБОМУ скрипту, который должен работать и на Windows.

## 1. Кодировка stdout: cp1251 убивает русский вывод

**Симптом:** `UnicodeEncodeError: '\u2713' ... codec can't encode` на `✓`/`✗`/кириллице; при `script > log 2>&1` и в cp1251-консоли.
**Причина:** консоль по умолчанию cp1251; Python 3.12 при перенаправлении берёт кодировку консоли.
**Фикс (в каждом CLI-скрипте):**
```python
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: S110,BLE001
    pass
```
В AGGG2.0 — единый `scripts/_compat.py: fix_encoding()`. Bash: `export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"`. Системно (SETUP.md): `[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")`.

## 2. Запись файлов: CRLF ломает md5-проверки

**Симптом:** `Path.write_text()` пишет `\r\n`; канон — `\n`; md5-проверки зеркал ложно падают.
**Фикс записи:** `dst.write_text(content, encoding="utf-8", newline="\n")`; проверка: `if dst.read_bytes() == content.encode("utf-8"): ...`
**Фикс проверки (bash):** `first=$(tr -d '\r' < "${MIRRORS[0]}" | md5sum | cut -d' ' -f1)`

## 3. PowerShell 5.1: UTF-8 без BOM читается как cp1251

**Симптом:** `bootstrap.ps1` игнорирует `--check`, кракозябры, падает на тире «—».
**Фикс:** .ps1 в UTF-8 **with BOM** (EF BB BF):
```python
if not data.startswith(b"\xef\xbb\xbf"):
    p.write_bytes(b"\xef\xbb\xbf" + data)
```
Проверка: `head -c 3 file.ps1 | od -An -tx1` → `ef bb bf`.

## 4. npm на Windows — это npm.cmd

**Симптом:** `subprocess.run(["npm", ...])` → `FileNotFoundError: [WinError 2]` (CreateProcess без shell не запускает .cmd).
**Фикс:**
```python
def _npm_cmd():
    if os.name == "nt":
        for name in ("npm.cmd", "npm"):
            p = shutil.which(name)
            if p:
                return p
    return "npm"
```

## 5. venv: bin vs Scripts, .exe

**Симптом:** `venv/bin/python` нет — на Windows `venv\Scripts\python.exe`.
**Фикс (резолвер в `_compat.py`):**
```python
VENV_BIN = VENV / ("Scripts" if os.name == "nt" else "bin")
# Windows-бинарь: d / "Scripts" / f"{name}.exe"  vs  d / "bin" / name
```
В bash: перебирать `Scripts/python.exe` и `bin/python`.

## 6. winget кладёт бинари не в PATH

**Симптом:** `shutil.which("clangd")` не находит, хотя установлен (`%LOCALAPPDATA%\Microsoft\WinGet\Links\`).
**Фикс:**
```python
win_get = Path(os.environ.get("LOCALAPPDATA", HOME)) / "Microsoft" / "WinGet" / "Links"
extra = [str(win_get / "clangd.exe")] if os.name == "nt" else []
```

## 7. GitHub-релизы: форматы ассетов по платформам

**Симптом:** ищет `win32-x64.tar.gz`, проект отдаёт `.zip` (LuaLS), или наоборот.
**Фикс:**
```python
ext = r"\.zip" if IS_NT else r"\.tar\.gz"
m = re.search(rf'https://[^"]*{key}-{variant}{ext}', json)
# распаковка: zipfile.ZipFile (NT) vs tarfile.open (posix)
```

## 8. bash в PATH Windows — WSL-заглушка

**Симптом:** `C:\Windows\System32\bash.exe` — заглушка WSL («используйте wsl.exe --list»).
**Фикс:** требовать Git for Windows (`C:\Program Files\Git\bin\bash.exe`) или PowerShell-обёртки; на `bash` из PATH не рассчитывать.

## 9. Camoufox на Windows: три класса багов (08.2026, issues daijro/camoufox)

**9a. Python из MS Store сандбоксит AppData\Local (#282).** `camoufox fetch` пишет success, но `camoufox.exe` нет (перенаправление в `Packages\PythonSoftwareFoundation...\LocalCache`). Фикс: Python с python.org; проверка: `sys.executable` содержит `WindowsApps` → предупредить.

**9b. headless падает с STATUS_BREAKPOINT 0x80000003 (#614).** Часть билдов — мгновенный краш headless (headed работает). Фикс: fallback `headless=False, windows_hide=True`; в `mcp/camoufox_worker.py` — автоматически в `_launch()` (только NT).

**9c. SxS mozglue / нет MSVC CRT (#624/#650).** «side-by-side configuration is incorrect» / Playwright `spawn UNKNOWN`. Фиксы: VC++ Redistributable (x64), установка вне AppData\Local (`CAMOUFOX_INSTALL_DIR=C:\Users\...\.camoufox`), v152+.

**Диагностика:** `python3 scripts/install/update_camoufox.py --check`; см. `mcp/README.md` «Camoufox на Windows».

## 10. subprocess: кодировка вывода детей (BUG-1/4)

**Симптом:** `UnicodeDecodeError: 'charmap' codec can't decode byte 0x98` в reader-потоках (потеря вывода; у LuaLS stdout → None) или кракозябры вместо «Проверяю зеркала» (doctor.py).
**Причина:** `subprocess.run(..., text=True)` без кодировки берёт ANSI (cp1251), а консольные дети пишут OEM (cp866, GetConsoleOutputCP); двух кодировок нет (CPython issue #105312).
**Фикс с двух сторон:**
```python
# родитель: scripts/_compat.py run() — utf-8 + errors=replace, детям PYTHONUTF8=1:
r = _compat.run(cmd, timeout=120)          # вместо subprocess.run(text=True)
```
```powershell
# ребёнок: .ps1 в начале:
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [Console]::OutputEncoding
```
**Отвергнуто:** `encoding='oem'` (только 3.13+); `GetOEMCP()` в родителе (не лечит python-детей, пишущих UTF-8); `errors="strict"` (один байт роняет захват).

## Универсальные грабли (индустрия: blog.shellnetsecurity.com, PEP 686, pythonfriday.dev #130)

| Грабля | Фикс |
|---|---|
| Хардкод `/` в путях | `Path.home() / "x"`, `os.path.join()` |
| Регистр файлов (Config.json == config.json на NTFS/macOS) | единый регистр имён |
| `$HOME` не задан без Git Bash | `Path.home()`; bash `${HOME:-$USERPROFILE}` |
| TMPDIR/TEMP различаются | `tempfile.gettempdir()` |
| Утилит find/which/grep нет или другие | `shutil.which`, python вместо unix-пайплайнов |
| curl в PowerShell = Invoke-WebRequest | `curl.exe` явно |
| Windows держит открытые файлы (PermissionError) | `with`-блоки, не удалять открытое |
| bash нет нативно | один шелл (Git Bash) или Python |
| shell=True решает PATH, но грязно | явные пути, shutil.which, .cmd-обёртки |
| PEP 686: UTF-8 по умолчанию с 3.15 | уже сейчас `encoding="utf-8"` явно |

## Чеклист «скрипт готов к Windows»

- [ ] `fix_encoding()` в начале (stdout utf-8)
- [ ] вывод детей — `_compat.run()`; .ps1-дети — `[Console]::OutputEncoding`
- [ ] запись с `newline="\n"`, сравнение по байтам
- [ ] venv через резолвер (Scripts vs bin, .exe)
- [ ] npm → npm.cmd; winget-ссылки extra-путь
- [ ] .ps1 — UTF-8 with BOM; md5 с `tr -d '\r'`
- [ ] ассеты по платформе (zip vs tar.gz)
- [ ] пути — pathlib/Path.home(); файлы с явным `encoding="utf-8"`
- [ ] temp — `tempfile.gettempdir()`, не `/tmp`
- [ ] `python3 scripts/doctor/doctor.py` на Windows (0 ошибок)

## Ссылки

- `scripts/_compat.py` — единый кроссплатформенный модуль (AGGG2.0)
- blog.shellnetsecurity.com «Cross-Platform Scripting Tips and Tricks» (01.2026); PEP 686; pythonfriday.dev #130

## Этапы (handoff)

- **Вход из:** `task-cycle` (Windows-задача), `workspace-setup`
- **Дальше:** `lsp-code-depth`, `testing-discipline`

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
