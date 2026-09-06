# Адаптация sherpa-voice под Windows — план
Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->


> Статус: **5 из 6 узлов уже реализованы в коде** (проверено по коду,
> 08.2026). Осталось: живая проверка на Windows-стенде или CI, и узел 3
> (автозапуск — инструкция, не код). Ниже — состояние каждого узла.

## Статус узлов

| # | Узел | Статус |
|---|---|---|
| 1 | `fcntl` → `msvcrt.locking` | ✅ в коде: `acquire_single_instance()` имеет ветку `os.name == "nt"` (transcribe.py) |
| 2 | `run.bat` | ✅ есть рядом со скриптом |
| 3 | Автозапуск (Startup) | 📋 инструкция ниже; файл-пример не заводили |
| 4 | Буфер обмена на Windows | ✅ в коде: ветка `os.name == "nt"` → `pyperclip.copy` (transcribe.py) |
| 5 | Поиск микрофона | ✅ в коде: на `nt` возвращает None (дефолтный WASAPI вход) |
| 6 | PDF-шрифт | ✅ в коде: `PDF_FONTS` включает `C:/Windows/Fonts/arial.ttf` |
| 7 | **ffmpeg для голосовых из Telegram** | ⚠️ зависимость, не покрыта: `_tg_voice_to_wav` вызывает ffmpeg (telegram.py). На Linux не проверяется при установке, на Windows не гарантирован. Установка: `winget install ffmpeg`. Проверка при ошибке — понятное сообщение есть (с 08.2026). В CI (см. workflow) голосовые не тестируются — нужен живой стенд |

Проверка кода не заменяет живого прогона: ветки `os.name == "nt"`
написаны без Windows-стенда, их надо подтвердить запуском (см. «Проверка»
ниже).

## Что уже работает на Windows без правок

| Компонент | Почему |
|---|---|
| sherpa-onnx | официальные wheels для Windows |
| sounddevice | WASAPI/MME, интерфейс тот же (но имена устройств другие) |
| numpy, soxr | есть Windows-wheels |
| pyperclip | нативный win32 clipboard (но см. п. 4) |
| reportlab | чистый Python, TTF поддерживает |
| .env / DeepSeek (urllib) | стандартная библиотека |

## Узлы, которые надо чинить

### 1. `fcntl` — нет на Windows (lock-файл молча отключается)

`acquire_single_instance()` ловит `ImportError` и возвращается без lock —
на Windows зависший процесс снова будет тихо держать микрофон (та самая
грабля из README). Замена: `msvcrt.locking(handle, msvcrt.LK_NBLCK, 1)`
по первому байту lock-файла. Один файл, ветка `os.name == "nt"`.

### 2. `run.sh` — bash, на Windows нужен лаунчер

- `run.bat` рядом со скриптом:
  ```bat
  @echo off
  cd /d "%~dp0"
  if not exist venv (
      py -3 -m venv venv
      venv\Scripts\pip install -r requirements.txt
  )
  venv\Scripts\python transcribe.py %*
  ```
- venv на Windows: `venv\Scripts\python.exe`, а не `venv/bin/python`.

### 3. Автозапуск — папка Startup, не .desktop
aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


```bat
@echo off
start "" "C:\путь\к\sherpa-voice\run.bat"
```
положить в `shell:startup` (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`).

### 4. Копирование в буфер — на Windows сейчас вернёт False

`copy_to_clipboard()` проверяет `WAYLAND_DISPLAY` и `DISPLAY`; на Windows
обоих нет → «Буфер недоступен», хотя win32-буфер работает отлично.
Фикс: ветка `os.name == "nt"` → сразу `pyperclip.copy(text)`.

### 5. Поиск микрофона — логика под ALSA не совпадёт

`find_input_device()` ищет подстроки `hw:0,0`, `hw:`, `sysdefault` —
на Windows имён таких нет, вернётся `None` (дефолтный вход). Для Windows
лучше сразу возвращать `None` и полагаться на default + `--device` по
имени («Микрофон (Realtek...)»), как в `mic_check.py`.

### 6. PDF-шрифт — Linux-путь не существует

`PDF_FONT_REGULAR/BOLD` зашиты на `/usr/share/fonts/liberation-sans-fonts/…`.
На Windows использовать `C:\Windows\Fonts\arial.ttf` (кириллица есть):
решение — искать шрифт по списку путей и брать первый существующий.

## Что не менять

- Модели (tar.bz2 читается Python-`tarfile` без внешних утилит)
- `.env`, промпты, меню, полировку — всё одинаково
- `--file`, `--streaming`, `--once` — работают как есть

## Проверка

1. `py -m venv venv` + `venv\Scripts\pip install -r requirements.txt`
2. `venv\Scripts\python transcribe.py --file test.wav` (офлайн и `--streaming`)
3. `venv\Scripts\python mic_check.py` — увидеть свои входы (WASAPI)
4. Живой цикл: Enter → запись → Enter → полировка → буфер
5. Экспорт MD/PDF (после фикса шрифта)
6. `--once` (одна запись и выход)




---

*Принадлежит и разработано: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна, новая — ещё лучше.***

Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->
