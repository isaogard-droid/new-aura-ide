#!/usr/bin/env python3
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""ui_utils — утилиты sherpa-voice: пути, цвета, буфер, уведомления,
single-instance, миграции. Нижний слой: не зависит от других модулей
проекта (вынесено из монолита transcribe.py).

Слои: ui_utils → store → publish → chat (transcribe.py — facade).
"""
import os
import shutil
import signal
import sys
import time

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

# Фоновый режим (--once из хоткея, без окна): toggle-управление.
# Второе нажатие клавиши = стоп: новый процесс видит маркер записи и
# создаёт стоп-флаг. Таймер — страховка от вечного «висения».
REC_MARKER = os.path.expanduser("~/.cache/sherpa-voice/recording")
STOP_FLAG = os.path.expanduser("~/.cache/sherpa-voice/stop")
LAST_TEXT_FILE = os.path.expanduser("~/.cache/sherpa-voice/last.txt")
HISTORY_FILE = os.path.expanduser("~/.cache/sherpa-voice/history.md")
VOCAB_FILE = os.path.expanduser("~/.cache/sherpa-voice/vocab.txt")
LOCK_FILE = os.path.expanduser("~/.cache/sherpa-voice/lock")


def _settings_dir():
    """Каталог настроек. Стандарт — XDG (~/.config); если он недоступен для
    записи (read-only HOME: ~/.config даёт EROFS, писаться может только
    ~/.cache), откат на ~/.cache/sherpa-voice,
    чтобы настройки работали на любой системе."""
    preferred = os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
        "sherpa-voice")
    fallback = os.path.expanduser("~/.cache/sherpa-voice")
    for d in (preferred, fallback):
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".write_probe")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("1")
            os.remove(probe)
            return d
        except OSError:
            continue
    return preferred


# Настройки (подмешка, Telegram) должны переживать перезапуски: они в
# каталоге настроек (_settings_dir), а не во временных/кэш-файлах.
SHERPA_CONFIG_DIR = _settings_dir()
MIX_FILE = os.path.join(SHERPA_CONFIG_DIR, "mix.txt")
TELEGRAM_FILE = os.path.join(SHERPA_CONFIG_DIR, "telegram.txt")


def _cleanup_markers():
    """Убирает маркеры записи/стопа. Вызывается в finally и по SIGTERM: если
    процесс убили, маркеры не должны остаться — иначе следующий --once
    сработает как «стоп» вместо «старт»."""
    for p in (STOP_FLAG, REC_MARKER):
        try:
            os.remove(p)
        except OSError:
            pass


def _sigterm_cleanup(signum, frame):
    _cleanup_markers()
    sys.exit(128 + signum)


def _atomic_write(path, text, mode=None):
    """Атомарная запись (temp + rename, POSIX): файл не повреждается, если
    процесс упадёт в середине записи. mode — права (например 0o600)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    if mode is not None:
        os.chmod(tmp, mode)
    os.replace(tmp, path)


def _migrate_settings():
    """Переносит настройки из легаси-места (~/.cache) в текущий каталог
    настроек, если это разные места. Старое не перезаписывает и не удаляет
    (откат). Вызывается при старте."""
    old_dir = os.path.expanduser("~/.cache/sherpa-voice")
    if os.path.abspath(old_dir) == os.path.abspath(SHERPA_CONFIG_DIR):
        return
    if not os.path.isdir(old_dir):
        return
    try:
        os.makedirs(SHERPA_CONFIG_DIR, exist_ok=True)
    except OSError as e:
        print(f"[i] Не создал {SHERPA_CONFIG_DIR}: {e}")
        return
    for name in ("mix.txt", "telegram.txt"):
        old = os.path.join(old_dir, name)
        new = os.path.join(SHERPA_CONFIG_DIR, name)
        if os.path.isfile(old) and not os.path.isfile(new):
            try:
                shutil.copy2(old, new)
                print(f"[i] Настройки перенесены в {new}")
            except OSError as e:
                print(f"[i] Не удалось перенести {old}: {e}")


def _migrate_history():
    """Один раз переносит старый history.txt (строки «[дата-время] текст»)
    в history.md. Старый файл не удаляем — просто перестаём его читать."""
    import re
    old = os.path.expanduser("~/.cache/sherpa-voice/history.txt")
    if not os.path.isfile(old) or os.path.exists(HISTORY_FILE):
        return
    entries = {}
    with open(old, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\[([^\]]+)\]\s*(.*)$", line.strip())
            if m:
                day = m.group(1)[:10]
                entries.setdefault(day, []).append((m.group(1), m.group(2)))
    if not entries:
        return
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for day in sorted(entries):
            f.write(f"## {day}\n")
            f.writelines(f"- `{ts}` {text}\n" for ts, text in entries[day])
    print(f"[i] Старая история перенесена в {os.path.basename(HISTORY_FILE)} "
          f"({sum(len(v) for v in entries.values())} записей).")


def _kill_previous(pid):
    """Завершает прошлый экземпляр, чтобы запуститься заново.
    На Linux проверяет cmdline — не трогает чужой процесс, переиспользовавший PID."""
    if pid == os.getpid():
        return False
    try:
        if os.name == "nt":
            # На Windows нет /proc — проверить cmdline нельзя, а PID может
            # быть переиспользован. Не убиваем вслепую: честно просим
            # закрыть прошлый экземпляр вручную.
            print("[i] Похоже, прошлый экземпляр ещё работает — закройте "
                  "его (диспетчер задач) и запустите снова.")
            return False
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmd = f.read().decode("utf-8", "replace")
        if "transcribe.py" not in cmd:
            return False
        os.kill(pid, signal.SIGTERM)
    except FileNotFoundError:
        return True  # процесса уже нет — просто пробуем занять lock ещё раз
    except ProcessLookupError:
        return True
    except OSError:
        return False
    for _ in range(10):  # ждём, пока процесс завершится (до 2с)
        time.sleep(0.2)
        try:
            os.kill(pid, 0)
        except OSError:
            return True
    return False


_LOCK_FD = None  # держим открытым, чтобы flock жил весь сеанс

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


def acquire_single_instance():
    """Не даёт запуститься второму экземпляру. Зависший прошлый запуск,
    который держит микрофон, — главная причина «не записывает» (см. README).
    Повторный запуск не отказывается, а завершает прошлый экземпляр и
    стартует заново (последний запуск побеждает).
    Linux: flock; Windows: msvcrt.locking (fcntl там нет)."""
    global _LOCK_FD
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    # PID читаем ДО open(..., "w") — иначе truncate обнулит файл и читать будет нечего
    try:
        with open(LOCK_FILE) as f:
            prev_pid = int(f.read().strip())
    except (OSError, ValueError):
        prev_pid = None
    for attempt in (0, 1):
        lock = open(LOCK_FILE, "w")
        try:
            if os.name == "nt":
                import msvcrt
                try:
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    lock.close()
                    if attempt == 0 and prev_pid is not None and _kill_previous(prev_pid):
                        print("[i] Прошлый экземпляр завершён — запускаюсь заново.")
                        prev_pid = None
                        continue
                    print("[✗] Уже запущен другой экземпляр transcribe.py — он держит микрофон.")
                    print("    Найдите и завершите его:  tasklist | findstr transcribe")
                    sys.exit(1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock.close()
            if attempt == 0 and prev_pid is not None and _kill_previous(prev_pid):
                print("[i] Прошлый экземпляр завершён — запускаюсь заново.")
                prev_pid = None
                continue
            print("[✗] Уже запущен другой экземпляр transcribe.py — он держит микрофон.")
            print("    Найдите и завершите его:  ps aux | grep transcribe.py")
            sys.exit(1)
        _LOCK_FD = lock  # не закрываем до выхода из процесса
        lock.write(str(os.getpid()))
        lock.flush()
        return


def copy_to_clipboard(text):
    """Копирует текст в буфер обмена честно: на Wayland нужен wl-copy,
    на X11 — xclip/xsel, на Windows — нативный clipboard pyperclip.
    Если буфер недоступен — возвращает False, чтобы caller сохранил
    текст в файл (без молчаливого провала)."""
    if not HAS_CLIPBOARD:
        return False
    if os.name == "nt":
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            return False
    if os.environ.get("WAYLAND_DISPLAY"):
        if shutil.which("wl-copy"):
            try:
                pyperclip.copy(text)
                return True
            except Exception:
                return False
        print("[i] Wayland-сессия, но wl-copy (wl-clipboard) не установлен — "
              "буфер недоступен, сохраню в файл.")
        return False
    if os.environ.get("DISPLAY"):
        if shutil.which("xclip") or shutil.which("xsel"):
            try:
                pyperclip.copy(text)
                return True
            except Exception:
                return False
        print("[i] X11-сессия, но xclip/xsel не установлены — "
              "буфер недоступен, сохраню в файл.")
        return False
    return False


def notify(title, message):
    """Уведомление через notify-send (для фонового режима без окна).
    Молча пропускается, если notify-send недоступен."""
    for path in ("/usr/bin/notify-send", "/usr/bin/knotify6"):
        if os.path.isfile(path):
            import subprocess
            subprocess.Popen([path, title, message])
            return


# ANSI-цвета статусов (темы как в OpenCode TUI)
C_OK, C_INFO, C_WARN, C_ERR, C_BLUE, C_RST = (
    "\033[32m", "\033[36m", "\033[33m", "\033[31m", "\033[34m", "\033[0m")


def c_ok(s):
    return f"{C_OK}{s}{C_RST}"


def c_info(s):
    return f"{C_INFO}{s}{C_RST}"


def c_warn(s):
    return f"{C_WARN}{s}{C_RST}"


def c_err(s):
    return f"{C_ERR}{s}{C_RST}"


def c_blue(s):
    return f"{C_BLUE}{s}{C_RST}"


# Метки с цветом И текстом (PatternFly: смысл не только цветом —
# доступно цветонезрячим и в логах без ANSI). Использовать для
# статусов вместо голых ✓/✗/i:
def c_ok_lbl(s):
    return f"{C_OK}[✓ OK] {s}{C_RST}"


def c_warn_lbl(s):
    return f"{C_WARN}[! WARN] {s}{C_RST}"


def c_err_lbl(s):
    return f"{C_ERR}[✗ ERR] {s}{C_RST}"

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
