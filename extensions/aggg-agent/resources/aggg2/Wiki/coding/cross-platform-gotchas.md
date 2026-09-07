---
type: Howto
title: "cross-platform-gotchas"
description: "Кроссплатформенные грабли Python-скриптов и установщиков (Linux/macOS/Windows): platform.system vs sys.platform, raw-regex, FileNotFoundError от subprocess.run, fallback менеджеров пакетов, PATH из реестра Windows, bash = WSL-заглушка. Дубль windows-encoding-fixes оставлен как справочник"
date: 2026-08-16
tags: [skill-notes, coding, cross-platform, windows, python]
source: skills/cross-platform-gotchas/ (перенесено 16.08.2026)
status: stable
---

# cross-platform-gotchas — скилл-на-полке (Howto)

Перенесено из `skills/cross-platform-gotchas/` по протоколу `docs/canon/WIKI.md` (скилл-на-полке: дублирует вшитый в канон `windows-encoding-fixes`, в пуле скиллов не остаётся). Полная инструкция ниже.

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->

# Кроссплатформенные грабли в скриптах и установщиках

Универсальный набор ошибок из багрепорта установки AGGG2.0 на Windows
(2026-08-11). Каждая грабля — симптом → причина →
фикс. Проверять свой код по этому чеклисту, если он должен работать
на нескольких ОС (особенно Windows).

> Кодировки/CRLF/BOM/консоль Windows — см. скилл `windows-encoding-fixes` (в пуле).

## 1. platform.system() и sys.platform — это РАЗНЫЕ вещи

**Симптом:** словарь платформ построен на одном API, lookup — по
другому; ключ не находится (`None`), код тихо идёт не туда или падает.

**Причина:** на Windows `platform.system()` возвращает `"Windows"`,
а `sys.platform` — `"win32"`. На Linux: `"Linux"` vs `"linux"`.
Смешивание в одном выражении даёт промах.

**Фикс:** не смешивать. Один источник для всех словарей:
```python
# плохо: ключи под sys.platform, lookup по platform.system()
key = {"win32": "win32", "linux": "linux"}.get(platform.system().lower())  # None на Windows!

# хорошо: явный ключ для platform.system() ИЛИ везде sys.platform
key = {"windows": "win32", "linux": "linux", "darwin": "darwin"} \
    .get(platform.system().lower())
# или: ключ = sys.platform, если словарь на нём
```

## 2. Regex в raw-строках: двойной бэкслеш матчит НЕ то

**Симптом:** `re.search(rf'...{ext}', url)` никогда не находит совпадение,
хотя в данных оно есть.

**Причина:** в raw-строке `r"\\.zip"` — это ДВА символа: `\\` (литеральный
бэкслеш) + `.` (wildcard «любой символ»), т.е. ищется `\.` в тексте URL —
а нужен один экранированный бэкслеш `\.` (точка). В raw-строках бэкслеш
не удваивается для экранирования — он и так литерал.

**Фикс:** в raw-строках один бэкслеш:
```python
ext = r"\.zip"        # правильно: точка
# ext = r"\\.zip"     # неправильно: литеральный \ + любой символ
```

## 3. subprocess.run с check=False всё равно бросает FileNotFoundError

**Симптом:** скрипт умирает с `FileNotFoundError: [WinError 2]` на
`subprocess.run(["winget", ...])`, хотя `check=False` и все ошибки
«обрабатываются» по returncode.

**Причина:** `check=False` перехватывает только ненулевой returncode.
Если бинарь **вообще не в PATH** — Python не может его запустить и
бросает исключение ДО старта процесса.

**Фикс:** оборачивать или проверять наличие заранее:
```python
def run(cmd, sudo=False):
    c = ["sudo"] + cmd if sudo and not os.name == "nt" else cmd
    try:
        return subprocess.run(c, capture_output=True, text=True,
                              check=False).returncode == 0
    except FileNotFoundError:
        return False  # честное «не удалось», а не падение
```

## 4. Менеджер пакетов на Windows не гарантирован — нужен fallback

**Симптом:** `winget install ...` — `FileNotFoundError` или «не найдено»:
на машине нет App Installer / winget не установлен.

**Фикс:** цепочка fallback + честный пропуск, если нет ни одного:
```python
for pm, pkg in (("winget", ["install", "--id", "LLVM.clangd", "-e", ...]),
                ("scoop", ["install", "llvm"]),
                ("choco", ["install", "-y", "llvm"])):
    if not shutil.which(pm):
        continue
    if run([pm] + pkg):
        break
else:
    print("[!] clangd: нет winget/scoop/choco — поставь вручную")
```
Сначала проверять `shutil.which(pm)` — это и fallback, и защита от
грабли №3.

## 5. Windows: свежепоставленные бинари не видны процессу

**Симптом:** скрипт поставил gopls/rust-analyzer через `go install` /
`scoop install`, а `shutil.which("gopls")` — `None`. Новый процесс
(перезапуск) видит, текущий — нет.

**Причина:** PATH меняется в реестре, но `os.environ` уже зафиксирован
при старте процесса.

**Фикс:** прочитать Machine+User PATH из реестра и подмешать в начале
`main()` (до всех проверок `have()`/`shutil.which()`):
```python
def win_refresh_path():
    if os.name != "nt":
        return
    import winreg
    parts = []
    for hive, key in (
            (winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            (winreg.HKEY_CURRENT_USER, r"Environment")):
        try:
            with winreg.OpenKey(hive, key) as k:
                val, _ = winreg.QueryValueEx(k, "Path")
                if val:
                    parts.append(val)
        except OSError:
            pass
    if parts:
        os.environ["PATH"] = os.pathsep.join(parts) + os.pathsep + os.environ.get("PATH", "")
```

## 6. bash на Windows — это WSL-заглушка, а не bash

**Симптом:** `bash script.sh` → `rc=-1 [WinError 2]` или «WSL: не
установлено». `shutil.which("bash")` находит `C:\Windows\System32\bash.exe`
— это заглушка WSL, которая без WSL падает.

**Фикс:** искать настоящий bash в обход System32, затем Git Bash:
```python
def _bash():
    if os.name == "nt":
        p = shutil.which("bash")
        if p and "System32" not in p:
            return p
        git_bash = (Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
                    / "Git" / "bin" / "bash.exe")
        if git_bash.is_file():
            return str(git_bash)
        return None  # вызывающий: warning, а не падение
    return shutil.which("bash") or "bash"
```
Нет bash → честный warning/пропуск шага, а не ошибка всей проверки.

## 7. Единый источник правды: копия не должна быть источником

**Симптом:** плагин/скрипт читает данные рядом с собой (копию),
а канон лежит в другом месте. После обновления канона копия устаревает,
функция тихо перестаёт работать.

**Причина:** DRY-нарушение: две копии одного знания, менявшиеся
врозь (в AGGG2.0: `core.txt` искался в `harness/opencode/plugins/`,
а источник правды — `harness/core.txt`).

**Фикс:** при деплое копий — читать/брать ТОЛЬКО из канона:
```python
core_src = ROOT / "harness" / "core.txt"          # канон
deploy_file(core_src, dst_plugins / "core.txt")   # копия для рантайма
```
И проверка «уже актуально» по байтам (`read_bytes() == read_bytes()`),
чтобы повторные запуски не писали зря.

## Чеклист перед написанием кроссплатформенного скрипта

- [ ] Все словари платформ — на одном API (`platform.system()` или `sys.platform`), с явными ключами
- [ ] Regex в raw-строках: один бэкслеш для спецсимволов
- [ ] `subprocess.run` обёрнут в try/except FileNotFoundError (или `shutil.which` перед вызовом)
- [ ] Менеджеры пакетов Windows — fallback-цепочка + честный пропуск
- [ ] PATH из реестра подмешан до проверок `which()` (Windows)
- [ ] bash ищется в обход System32 (WSL-заглушка), fallback — Git Bash
- [ ] Копии читаются из единого канона, актуальность по байтам
- [ ] Кодировка stdout — UTF-8 (см. windows-encoding-fixes, если ещё не сделано)

## When NOT to use

- Только Linux-скрипт без амбиций кроссплатформенности — чеклист избыточен.
- Проблема в кодировках/CRLF/BOM — это скилл `windows-encoding-fixes`, не этот пост.
- Обычный продуктовый код без работы с процессами/ОС — здесь про системные грабли.

## References

- Багрепорт Windows-установки с фиксами
- Файлы-примеры фиксов: `scripts/install/install_lsp_servers.py` (run, win_refresh_path, clangd fallback, lua), `scripts/doctor/doctor.py` (_bash), `scripts/install/install_proshivka.py` (core.txt из канона)
- Спецификация скиллов: agentskills.io/specification

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->
