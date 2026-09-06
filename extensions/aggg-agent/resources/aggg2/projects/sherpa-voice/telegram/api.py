#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""telegram.api — сеть: getaddrinfo-подмена, запросы, updates,
download, voice→wav, chat_action, реакции."""
import json
import os
import socket
import urllib.error
import urllib.request

# Настоящий оригинал getaddrinfo: сохраняем при импорте, когда подмены
# ещё нет (подмена происходит внутри _tg_request на время запроса).
# Кэшировать оригинал ВНУТРИ _ipv4_getaddrinfo нельзя: при первом вызове
# socket.getaddrinfo уже подменён на неё саму — получается рекурсия
# (RecursionError: maximum recursion depth exceeded, поймано на проде).
_ORIG_GETADDRINFO = socket.getaddrinfo

def _ipv4_getaddrinfo_ctx():
    """Контекстный менеджер: на время запроса подменяет getaddrinfo на
    IPv4-предпочитающий (см. _ipv4_getaddrinfo) и ВСЕГДА восстанавливает
    оригинал. Применять к КАЖДОМУ сетевому вызову Telegram (не только
    _tg_request): _tg_get_updates (слушатель), _tg_download и другие
    ходят напрямую — без подмены они продолжают дёргать IPv6 и падать
    с Errno 101."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        socket.getaddrinfo = _ipv4_getaddrinfo
        try:
            yield
        finally:
            socket.getaddrinfo = _ORIG_GETADDRINFO
    return _ctx()

def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """getaddrinfo, предпочитающий IPv4: отбрасывает AF_INET6, если есть
    хоть один IPv4-адрес. Зачем: api.telegram.org отдаёт в DNS и IPv4,
    и IPv6; urllib берёт ПЕРВЫЙ адрес из списка, а порядок плавает
    (round-robin). На машинах без IPv6-маршрута запрос к IPv6 падает
    с Errno 101 Network is unreachable — отсюда «связь то есть, то нет».
    Если IPv4 нет — фолбэк на оригинальный результат (не ломать
    IPv6-only сети)."""
    res = _ORIG_GETADDRINFO(host, port, family, type, proto, flags)
    ipv4 = [r for r in res if r[0] == socket.AF_INET]
    return ipv4 or res

def _tg_request(token, method, payload=None, files=None):
    """Запрос к Telegram Bot API. files: [(поле, имя_файла, байты)] —
    multipart для sendDocument. Возвращает (ok, ошибка_или_None).

    Во время запроса socket.getaddrinfo подменяется на IPv4-предпочитающий:
    без этого на машинах без IPv6 urllib случайно дёргает IPv6-адрес
    (порядок DNS плавает) и падает с Network is unreachable. См.
    _ipv4_getaddrinfo."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    headers = {}
    data = None
    if files:
        import uuid
        boundary = "----sherpa" + uuid.uuid4().hex
        parts = []
        for name, value in (payload or {}).items():
            if isinstance(value, (dict, list)):
                # JSON-поля (reply_markup и т.п.) в multipart обязаны идти
                # строкой JSON — иначе Telegram: "can't parse reply keyboard
                # markup JSON object" (проверено вживую: документ с кнопками)
                value = json.dumps(value, ensure_ascii=False)
            parts.append((f"--{boundary}\r\n"
                          f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                          f"{value}\r\n").encode())
        for field, filename, blob in files:
            parts.append((f"--{boundary}\r\n"
                          f"Content-Disposition: form-data; name=\"{field}\"; "
                          f"filename=\"{filename}\"\r\n"
                          f"Content-Type: application/octet-stream\r\n\r\n").encode())
            parts.append(blob)
            parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif payload:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with _ipv4_getaddrinfo_ctx():
        try:
            # req — URL константный (api.telegram.org + метод из кода),
            # ключ токена уходит в path, а не от пользователя
            with urllib.request.urlopen(req, timeout=30) as resp:  # nosemgrep
                result = json.load(resp)
            if result.get("ok"):
                return True, None
            return False, f"Telegram: {result.get('description', 'неизвестная ошибка')}"
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:200]
            e.close()
            return False, f"Telegram HTTP {e.code}: {body}"
        except Exception as e:
            return False, f"Telegram: {type(e).__name__}: {e}"

def _tg_get_chat_id(token):
    """Узнаёт chat_id по последнему сообщению боту (getUpdates c offset=-1 —
    заодно «подтверждает» старые updates, чтобы поллер не получил их снова).
    Возвращает (chat_id_или_None, ошибка_или_None)."""
    if not token:
        return None, "сначала задайте токен (пункт 1)"
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/getUpdates?offset=-1")
    try:
        with _ipv4_getaddrinfo_ctx():
            # URL константный (api.telegram.org + метод из кода)
            with urllib.request.urlopen(req, timeout=30) as resp:  # nosemgrep
                data = json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        e.close()
        return None, f"Telegram HTTP {e.code}: {body}"
    except Exception as e:
        return None, f"Telegram: {type(e).__name__}: {e}"
    if not data.get("ok"):
        return None, f"Telegram: {data.get('description', 'неизвестная ошибка')}"
    for upd in reversed(data.get("result", [])):
        msg = (upd.get("message") or upd.get("edited_message")
               or upd.get("channel_post"))
        if msg and msg.get("chat", {}).get("id") is not None:
            return str(msg["chat"]["id"]), None
    return None, "бот не видит сообщений — напишите ему /start в Telegram"

def _tg_skip_reason(enabled, token, chat_id):
    """Почему отправка в Telegram не выполняется (для честного сообщения).
    None — всё настроено, отправлять можно."""
    if not enabled:
        return "Telegram выключен — меню [6] → Вкл/выкл"
    if not token:
        return "не задан токен бота — меню [6] → Токен"
    if not chat_id:
        return "не задан chat_id — меню [6] → Chat ID (можно ввести '?')"
    return None

def _tg_get_updates(token, offset=None, timeout=25):
    """Long polling getUpdates. Возвращает (список_updates, ошибка_или_None)."""
    url = f"https://api.telegram.org/bot{token}/getUpdates?timeout={timeout}"
    if offset is not None:
        url += f"&offset={offset}"
    try:
        with _ipv4_getaddrinfo_ctx():
            # URL: api.telegram.org + token из .env + метод из кода
            with urllib.request.urlopen(url, timeout=timeout + 10) as resp:  # nosemgrep
                data = json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        e.close()
        return None, f"Telegram HTTP {e.code}: {body}"
    except Exception as e:
        return None, f"Telegram: {type(e).__name__}: {e}"
    if not data.get("ok"):
        return None, f"Telegram: {data.get('description', 'неизвестная ошибка')}"
    return data.get("result", []), None

def _tg_download(token, file_id, dest):
    """Скачивает файл по file_id (getFile + file/bot<token>/<path>).
    Возвращает (ok, ошибка_или_None)."""
    url = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
    try:
        with _ipv4_getaddrinfo_ctx():
            # URL: api.telegram.org + token из .env + file_id от Telegram API
            with urllib.request.urlopen(url, timeout=30) as resp:  # nosemgrep
                data = json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        e.close()
        return False, f"Telegram HTTP {e.code}: {body}"
    except Exception as e:
        return False, f"Telegram: {type(e).__name__}: {e}"
    if not data.get("ok"):
        return False, f"Telegram: {data.get('description', 'неизвестная ошибка')}"
    path = data.get("result", {}).get("file_path")
    if not path:
        return False, "Telegram: у файла нет пути — слишком большой для Bot API"
    # Защита в глубину: file_path приходит с сервера Telegram и попадает
    # в URL. Нормальный путь — относительный, без ".." и абсолютных
    # префиксов. Если сервер ответит чем-то странным — не подставляем.
    # (semgrep: dynamic-urllib-use-detected — схема всё равно фиксированный
    # https, но проверка делает подстановку безопасной и при сбое сервера.)
    if path.startswith("/") or ".." in path.split("/"):
        return False, (f"Telegram: сервер вернул подозрительный путь "
                       f"({path!r}) — файл не скачиваю")
    try:
        with _ipv4_getaddrinfo_ctx():
            # path уже проверен выше (относительный, без ".."); схема https
            urllib.request.urlretrieve(  # nosemgrep
                f"https://api.telegram.org/file/bot{token}/{path}", dest)
    except Exception as e:
        return False, f"Telegram: файл не скачан ({type(e).__name__}: {e})"
    return True, None

def _tg_voice_to_wav(src, dst):
    """Декодирует голосовое (ogg/opus) в wav через ffmpeg.
    Возвращает (ok, ошибка_или_None)."""
    import shutil
    import subprocess
    if shutil.which("ffmpeg") is None:
        return False, ("ffmpeg не найден — голосовые из Telegram не "
                       "декодируются. Установите: Linux — sudo dnf install "
                       "ffmpeg; Windows — winget install ffmpeg")
    try:
        subprocess.run(["ffmpeg", "-y", "-i", src, "-ac", "1",
                        "-f", "wav", dst], capture_output=True, timeout=60)
    except Exception as e:
        return False, f"ffmpeg: {type(e).__name__}: {e}"
    if not os.path.isfile(dst):
        return False, "ffmpeg не дал wav — возможно, файл повреждён"
    return True, None

def _tg_chat_action(token, chat_id, action="typing"):
    """Индикатор «печатает» (sendChatAction). Виден ~5 сек — для долгих
    операций повторять. Ошибки игнорируются: индикация — косметика, не
    должна ломать транскрипцию."""
    try:
        _tg_request(token, "sendChatAction",
                    {"chat_id": chat_id, "action": action})
    except Exception:
        pass

def _tg_set_reaction(token, chat_id, message_id, emoji):
    """Реакция на сообщение: 🤔 думаю → 👍 готово / 👎 не вышло.
    Официальные эмодзи-реакции Bot API (один на сообщение, ошибки — 400).
    Ошибки игнорируются: реакция — косметика."""
    try:
        _tg_request(token, "setMessageReaction", {
            "chat_id": chat_id,
            "message_id": message_id,
            "reaction": [{"type": "emoji", "emoji": emoji}],
        })
    except Exception:
        pass

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
