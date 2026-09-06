## Системные команды

### Избегайте os.system

**Плохо:**
```python
import os
os.system("cls")     # Только Windows
os.system("clear")   # Только Linux/macOS
```

**Хорошо:**
```python
import subprocess
import sys

def clear_screen():
    """Кроссплатформенная очистка экрана."""
    if sys.platform == "win32":
        subprocess.run(["cmd", "/c", "cls"], check=True)
    else:
        subprocess.run(["clear"], check=True)
```

### Использование subprocess

```python
import subprocess
import sys

result = subprocess.run(["ls", "-l"], capture_output=True, text=True, check=True)
print(result.stdout)

# Кроссплатформенный вариант: if sys.platform == "win32": cmd = ["dir", directory]
# else: cmd = ["ls", "-l", directory] → subprocess.run(cmd, capture_output=True, text=True, check=True)
```

### Переменные окружения

```python
import os
from pathlib import Path

username = os.environ.get("USER") or os.environ.get("USERNAME")
home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
os.environ["MY_VAR"] = "value"
home = Path.home()  # работает на всех ОС
```

---

## Антипаттерны

### 1. Хардкод путей

**Плохо:**
```python
config_path = "/etc/myapp/config.json"  # Только Unix
config_path = "C:\\Program Files\\MyApp\\config.json"  # Только Windows
```

**Хорошо:**
```python
from platformdirs import user_config_dir
from pathlib import Path

config_dir = Path(user_config_dir("MyApp"))
config_path = config_dir / "config.json"
```

### 2. Хардкод разделителей путей

**Плохо:**
```python
path = "config/app/settings.json"  # Может не работать на Windows
path = "config\\app\\settings.json"  # Может не работать на Unix
```

**Хорошо:**
```python
from pathlib import Path
path = Path("config") / "app" / "settings.json"
```

### 3. Игнорирование кодировки

**Плохо:**
```python
with open("file.txt", "r") as f:
    content = f.read()  # Может упасть на Windows
```

**Хорошо:**
```python
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()
```

### 4. Использование os.system

**Плохо:**
```python
import os
os.system("rm -rf /tmp/cache")  # Только Unix
os.system("rmdir /s /q C:\\temp\\cache")  # Только Windows
```

**Хорошо:**
```python
import shutil
from pathlib import Path

cache_dir = Path("/tmp/cache")  # или используйте platformdirs
if cache_dir.exists():
    shutil.rmtree(cache_dir)
```

### 5. Игнорирование case sensitivity

**Плохо:**
```python
# Работает на Windows, падает на Linux
with open("Config.json", "r") as f:
    content = f.read()
```

**Хорошо:**
```python
# Всегда lowercase
with open("config.json", "r", encoding="utf-8") as f:
    content = f.read()
```

---
