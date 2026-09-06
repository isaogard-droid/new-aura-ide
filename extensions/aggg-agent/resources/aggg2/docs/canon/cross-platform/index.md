# Кроссплатформенность: Windows/macOS/Linux

**Дата:** 2026-01-19 · **Версия:** 1.0 · **Статус:** Актуально

Разделы: [paths.md](paths.md) — пути/системные директории · [encoding.md](encoding.md) — кодировки/line endings/ФС · [commands.md](commands.md) — команды/антипаттерны · [sources.md](sources.md) — источники

---

## Введение

Код работает одинаково на Windows, macOS и Linux без модификаций.

---

## Основные принципы

### 1. Никогда не хардкодить пути

**Плохо:**
```python
config_path = "/home/user/.config/app/config.json"  # Только Linux
config_path = "C:\\Users\\User\\AppData\\config.json"  # Только Windows
```

**Хорошо:**
```python
from pathlib import Path
config_path = Path.home() / ".config" / "app" / "config.json"
```

### 2. Использовать platform-specific библиотеки

Системные директории — через `platformdirs`: `user_cache_dir("MyApp", "MyCompany")`, `user_config_dir(...)` (реальные пути по ОС — paths.md).

### 3. Всегда указывать кодировку

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

### 4. Использовать pathlib вместо os.path

`Path.home() / ".config" / "app"` вместо `os.path.join(os.path.expanduser("~"), ...)`.

---

## Чеклист

### Перед коммитом проверьте:

- [ ] Нет хардкод путей (`/home/user`, `C:\Users`)
- [ ] Используется `pathlib` или `os.path.join`
- [ ] Указана кодировка `encoding="utf-8"` для всех текстовых файлов
- [ ] Используются `platformdirs` для системных директорий
- [ ] Нет `os.system()`, используется `subprocess`
- [ ] Имена файлов в lowercase
- [ ] Протестировано на Windows, macOS и Linux
- [ ] CI/CD пайплайн включает тесты на всех трёх ОС

### Автоматическая проверка

```yaml
# .github/workflows/test.yml
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
        with: {python-version: '3.11'}
      - run: pip install -r requirements.txt
      - run: pytest
```

---

**Главное правило:** Если код работает только на одной ОС — это баг, а не фича.

---

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub
