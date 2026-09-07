## Кодировки и текст

### Проблема UTF-8 на Windows

Windows по умолчанию — legacy-кодировки (cp1252, cp932 и т.д.), не UTF-8.

**Проблема:**
```python
with open("README.md", "r") as f:
    content = f.read()  # UnicodeDecodeError на Windows
```

**Решение 1: Всегда указывать кодировку**
```python
with open("README.md", "r", encoding="utf-8") as f:
    content = f.read()
```

**Решение 2: UTF-8 mode (Python 3.7+)**
```bash
export PYTHONUTF8=1  # Linux/macOS
set PYTHONUTF8=1     # Windows CMD
$env:PYTHONUTF8=1    # Windows PowerShell

python -Xutf8 script.py
```

**Решение 3: pyproject.toml**
```toml
[tool.python]
utf8-mode = true
```

### Работа с текстовыми файлами

```python
with open("file.bin", "rb") as f: data = f.read()  # бинарные — без кодировки
```

(текстовые: `open("file.txt", "r", encoding="utf-8")` — см. Решение 1 выше)

### Line endings (CRLF vs LF)

Windows: CRLF (`\r\n`) · macOS/Linux: LF (`\n`). Python конвертирует автоматически:

```python
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()  # \r\n → \n

# newline="" — сохранить оригинальные line endings
with open("file.txt", "r", encoding="utf-8", newline="") as f:
    content = f.read()
```

---

## Файловая система

### Case sensitivity

Windows/macOS: case-insensitive (`File.txt` == `file.txt`) · Linux: case-sensitive.

**Проблема / Решение:**
```python
# Работает на Windows, падает на Linux (FileNotFoundError)
with open("Config.json", "r") as f:
    content = f.read()
# Решение: имена файлов — всегда lowercase
with open("config.json", "r", encoding="utf-8") as f:
    content = f.read()
```

### Проверка существования файлов

```python
from pathlib import Path

path = Path("config.json")
if path.exists():
    print("Файл существует")
if path.is_file():
    print("Это файл")
if path.is_dir():
    print("Это директория")

def file_exists_ci(path: Path) -> bool:
    """Case-insensitive проверка существования файла (для Windows/macOS)."""
    if path.exists():
        return True
    parent = path.parent
    if not parent.exists():
        return False
    for item in parent.iterdir():
        if item.name.lower() == path.name.lower():
            return True
    return False
```

---
