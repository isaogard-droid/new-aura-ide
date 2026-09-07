## Работа с путями

### Различия между ОС

| ОС | Разделитель | Регистр | Корневой путь |
|----|-------------|---------|---------------|
| Windows | `\` (backslash) | Case-insensitive | `C:\` |
| macOS | `/` (forward slash) | Case-insensitive (по умолчанию) | `/` |
| Linux | `/` (forward slash) | Case-sensitive | `/` |

### Проблемы с backslash на Windows

Backslash в Python — escape-последовательность:

```python
# ОШИБКА: Unicode escape error
path = "C:\Users\sam\Documents\data.csv"
# SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes

# Решение 1: Raw string
path = r"C:\Users\sam\Documents\data.csv"

# Решение 2: Forward slashes (работает на всех ОС)
path = "C:/Users/sam/Documents/data.csv"

# Решение 3: pathlib (рекомендуется)
from pathlib import Path
path = Path("C:/Users/sam/Documents/data.csv")
```

### pathlib: современный подход

```python
from pathlib import Path

path = Path.home() / ".config" / "myapp" / "config.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("content", encoding="utf-8")
content = path.read_text(encoding="utf-8")
print(path.name, path.suffix, path.parent)  # имя, расширение, родитель
```

### os.path: старый подход (всё ещё работает)

```python
import os
path = os.path.join(os.path.expanduser("~"), ".config", "myapp", "config.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
```

---

## Системные директории

### Таблица директорий по ОС

| Тип | Windows | macOS | Linux |
|-----|---------|-------|-------|
| **Cache** | `%LOCALAPPDATA%\{app}\Cache` | `~/Library/Caches/{app}` | `$XDG_CACHE_HOME/{app}` или `~/.cache/{app}` |
| **Config** | `%APPDATA%\{app}\config` | `~/Library/Application Support/{app}` | `$XDG_CONFIG_HOME/{app}` или `~/.config/{app}` |
| **Data** | `%LOCALAPPDATA%\{app}\data` | `~/Library/Application Support/{app}` | `$XDG_DATA_HOME/{app}` или `~/.local/share/{app}` |
| **Logs** | `%LOCALAPPDATA%\{app}\logs` | `~/Library/Logs/{app}` | `$XDG_STATE_HOME/{app}/log` или `~/.local/state/{app}/log` |
| **Runtime** | `%TEMP%\{app}` | `~/Library/Caches/{app}/runtime` | `$XDG_RUNTIME_DIR/{app}` или `/run/user/{uid}/{app}` |

### Использование platformdirs

platformdirs вкладывает `{author}\{app}`: Win `AppData\Local\MyCompany\MyApp\Cache` · mac `~/Library/Caches/MyApp` · lnx `~/.cache/MyApp` (остальные типы — таблица выше).

```python
from platformdirs import user_cache_dir, user_config_dir, user_data_dir, user_log_dir, user_runtime_dir

app_name, app_author = "MyApp", "MyCompany"

cache_dir = user_cache_dir(app_name, app_author)     # кэш: можно удалять без потери данных
config_dir = user_config_dir(app_name, app_author)   # настройки пользователя
data_dir = user_data_dir(app_name, app_author)       # данные приложения
log_dir = user_log_dir(app_name, app_author)         # логи
runtime_dir = user_runtime_dir(app_name, app_author) # временные файлы сессии
```

### Ручная реализация (если platformdirs недоступен)

```python
import os
import sys
from pathlib import Path

def get_cache_dir(app_name: str) -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")  # LOCALAPPDATA > APPDATA
        if not base:
            base = Path.home()
        return Path(base) / app_name / "Cache"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / app_name
    else:
        base = os.environ.get("XDG_CACHE_HOME")  # XDG_CACHE_HOME > ~/.cache
        if not base:
            base = Path.home() / ".cache"
        return Path(base) / app_name

# get_config_dir — тот же паттерн: win APPDATA > ~ / mac ~/Library/Application Support / lnx XDG_CONFIG_HOME > ~/.config
```

---
