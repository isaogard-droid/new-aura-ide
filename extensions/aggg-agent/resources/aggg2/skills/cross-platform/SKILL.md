---
name: cross-platform
description: "Код для Windows/macOS/Linux: пути (pathlib), системные директории, UTF-8, line endings, case sensitivity, subprocess. Триггеры: «кроссплатформенно», «работает на Windows», «CRLF», «кодировка». Не для одноОС-кода."
triggers:
  - "кроссплатформенно"
  - "работает на Windows"
  - "проблема с путями"
  - "backslash"
  - "forward slash"
  - "CRLF"
  - "line endings"
  - "кодировка"
  - "UTF-8"
  - "sys.platform"
  - "Windows/macOS/Linux"
  - "case sensitive"
  - "case insensitive"
  - "platformdirs"
  - "pathlib"
  - "os.path"
  - "subprocess"
  - "os.system"
---

# Cross-Platform: Windows/macOS/Linux

Полное руководство: `docs/canon/CROSS_PLATFORM.md` в корне AGGG2.0.

## Когда загружать

**ВСЕГДА:** код под Windows/macOS/Linux; хардкод путей (`/home/user`, `C:\Users`); работа с ФС; системные директории (кэш/конфиг/данные); кодировки; subprocess/os.system; CI/CD на 3 ОС. **НЕ:** код одной ОС; личный скрипт.

## Основные правила

### 1. Никогда не хардкодить пути

```python
from pathlib import Path
config_path = Path.home() / ".config" / "app" / "config.json"
```

### 2. Использовать platformdirs для системных директорий

```python
from platformdirs import user_cache_dir, user_config_dir
cache_dir = user_cache_dir("MyApp", "MyCompany")
config_dir = user_config_dir("MyApp", "MyCompany")
```

| Тип | Windows | macOS | Linux |
|---|---|---|---|
| Cache | `%LOCALAPPDATA%\{app}\Cache` | `~/Library/Caches/{app}` | `$XDG_CACHE_HOME/{app}` или `~/.cache/{app}` |
| Config | `%APPDATA%\{app}\config` | `~/Library/Application Support/{app}` | `$XDG_CONFIG_HOME/{app}` или `~/.config/{app}` |
| Data | `%LOCALAPPDATA%\{app}\data` | `~/Library/Application Support/{app}` | `$XDG_DATA_HOME/{app}` или `~/.local/share/{app}` |

### 3. Всегда указывать кодировку

```python
with open("file.txt", "r", encoding="utf-8") as f:  # без encoding может упасть на Windows
    content = f.read()
```

### 4. Использовать pathlib вместо os.path

```python
path = Path.home() / ".config" / "app"  # не os.path.join(expanduser...)
```

### 5. Избегать os.system, использовать subprocess

```python
import subprocess, sys
def clear_screen():
    if sys.platform == "win32":
        subprocess.run(["cmd", "/c", "cls"], check=True)
    else:
        subprocess.run(["clear"], check=True)
```

### 6. Помнить о case sensitivity

Windows/macOS: case-insensitive (`File.txt` == `file.txt`); Linux: case-sensitive. Решение: всегда lowercase.

## Ручная реализация кроссплатформенных путей

Если platformdirs недоступен:

```python
import sys, os
from pathlib import Path

def get_cache_dir(app_name: str) -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or Path.home()
        return Path(base) / app_name / "Cache"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / app_name
    else:
        base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
        return Path(base) / app_name
```

## Антипаттерны

### 1. Хардкод путей
`/etc/myapp/config.json` (Unix), `C:\Program Files\...` (Windows) → platformdirs + Path.

### 2. Хардкод разделителей
`"config/app/settings.json"` (не Windows), `"config\\app\\..."` (не Unix) → `Path("config") / "app" / "settings.json"`.

### 3. Игнорирование кодировки
`open("file.txt", "r")` может упасть на Windows → `encoding="utf-8"`.

### 4. Использование os.system
`rm -rf` только Unix, `cls` только Windows → subprocess / shutil.rmtree.

### 5. Игнорирование case sensitivity
`open("Config.json")` работает на Windows, падает на Linux → всегда lowercase.

## Чеклист перед коммитом

- [ ] нет хардкод путей; pathlib или os.path.join
- [ ] `encoding="utf-8"` для всех текстовых файлов
- [ ] platformdirs для системных директорий
- [ ] нет `os.system()`; имена файлов lowercase
- [ ] CI/CD тестирует на Windows, macOS и Linux

## CI/CD конфигурация

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: pytest
```

## Примеры из AGGG2.0

Тот же паттерн `_get_cache_dir()` — в `skills_search.py` и `hook_gates.py` (`_STATE_DIR`).

## Связанные скиллы и доки

- **docs/canon/CROSS_PLATFORM.md** — полное руководство (20 источников)
- **windows-encoding-fixes** — Windows: кодировки, CRLF, BOM
- **local-databases** — тоже кроссплатформенные пути

## Источники

Полный список 20 источников в `docs/canon/CROSS_PLATFORM.md`: Stack Overflow (пути, AppData), Python docs (pathlib, os.path, subprocess, UTF-8), platformdirs, XDG Base Directory, Sentry/DEV/alexwlchan.

---

**Главное правило:** Если код работает только на одной ОС — это баг, а не фича.
