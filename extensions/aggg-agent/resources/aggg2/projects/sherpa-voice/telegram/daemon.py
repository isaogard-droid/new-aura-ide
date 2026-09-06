#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""telegram.daemon — цикл приёма обновлений."""
import os
import time

from audio import read_wav, transcribe_offline, transcribe_streaming
from transcribe import (
    _polish_text,
    append_mix,
    notify,
    publish_result,
)

from . import ratelimit
from .api import _tg_get_updates, _tg_voice_to_wav
from .state import _tg_keyboard, _tg_state_save


def _tg_handle_update(upd, token, recognizer, is_streaming, copy_to_buf,
                      notify_new=False):
    """Обрабатывает один update: голосовое → скачивание → распознавание →
    полировка → подмешка → ответ в тот же чат + консоль + история.
    Возвращает новый offset (update_id + 1)."""
    uid = upd.get("update_id")
    cq = upd.get("callback_query")
    if cq:
        # нажатие inline-кнопки (Саммари/Ответить/Кодинг-промт/Экспорт)
        _tg_handle_callback(cq, token)
        return (uid + 1) if uid is not None else None
    msg = upd.get("message") or upd.get("edited_message")
    if not msg:
        return (uid + 1) if uid is not None else None
    chat_id = msg.get("chat", {}).get("id")
    voice = msg.get("voice")
    if not voice or chat_id is None:
        # текстовое сообщение: команды-фолбэк (если кнопки недоступны)
        _tg_handle_text_command(msg, token)
        return (uid + 1) if uid is not None else None
    sender = msg.get("from") or {}
    from_name = sender.get("first_name") or sender.get("username") or "?"
    file_id = voice.get("file_id")
    msg_id = msg.get("message_id")
    # Входной antiflood по юзеру (from.id): голосовые пачками = каждый
    # распознаётся и полируется через DeepSeek (деньги владельца). Отказ —
    # понятным сообщением, без молчания (RATE LIMIT ALERT TEXT).
    user_id = sender.get("id")
    if user_id is not None:
        ok, retry_after = ratelimit.voice_allowed(user_id)
        if not ok:
            _tg_request(token, "sendMessage", {
                "chat_id": chat_id,
                "text": (f"⏳ Слишком часто — подождите {retry_after} сек "
                         f"и пришлите голосовое ещё раз.")})
            print(f"[i] rate-limit: юзер {user_id} превысил лимит голосовых")
            return (uid + 1) if uid is not None else None
    print(f"[telegram] Голосовое от {from_name} — скачиваю и распознаю…")
    _tg_chat_action(token, chat_id)                    # «печатает…»
    _tg_set_reaction(token, chat_id, msg_id, "🤔")      # «думаю…»
    if notify_new:
        notify("Sherpa Voice", f"Голосовое от {from_name} — распознаю…")
    import tempfile
    src = tempfile.mktemp(suffix=".ogg")
    wav = tempfile.mktemp(suffix=".wav")
    try:
        ok, err = _tg_download(token, file_id, src)
        if not ok:
            print(f"[✗] {err}")
            return (uid + 1) if uid is not None else None
        ok, err = _tg_voice_to_wav(src, wav)
        if not ok:
            print(f"[✗] {err}")
            return (uid + 1) if uid is not None else None
        audio = read_wav(wav)
        text = (transcribe_streaming if is_streaming else transcribe_offline)(
            recognizer, audio)
        print(f"[text] {text}")
        if text.strip():
            _tg_chat_action(token, chat_id)   # индикатор гаснет через ~5с — повтор
            text = _polish_text(text)
            text, added, mix = append_mix(text)
            publish_result(text, to_tg=False, to_clipboard=copy_to_buf)
            _tg_state_save(chat_id, text)
            ok_tg, err_tg = _tg_send_result(text, "📝 Транскрипт",
                                            chat_id=chat_id,
                                            reply_markup=_tg_keyboard(),
                                            footer=mix if added else None)
            if ok_tg:
                _tg_set_reaction(token, chat_id, msg_id, "👍")  # готово
                print("[✓] Ответ отправлен в Telegram")
                if notify_new:
                    notify("Sherpa Voice", "Транскрипт отправлен в Telegram")
            elif err_tg:
                print(f"[✗] {err_tg}")
        else:
            print("[i] Пустое распознавание — не отправляю.")
            _tg_set_reaction(token, chat_id, msg_id, "👎")
    except Exception as e:
        print(f"[✗] Ошибка обработки голосового: {e}")
        _tg_set_reaction(token, chat_id, msg_id, "👎")
    finally:
        for p in (src, wav):
            try:
                os.remove(p)
            except OSError:
                pass
    return (uid + 1) if uid is not None else None

def _tg_listen_loop(recognizer, is_streaming, copy_to_buf=True, notify_new=False):
    """Слушает голосовые боту (long polling). Работает в фоновом потоке
    основного режима и как --telegram-daemon. НЕ умирает, если Telegram
    выключен или не настроен: конфиг перечитывается на каждом цикле, и
    настройка через меню [6] подхватывается без перезапуска (раньше поток
    проверял конфиг один раз при старте и молча завершался — «голосовые
    не переводятся»)."""
    offset = None
    err_since = None   # время первой ошибки подряд — для тихого ретрая
    while True:
        enabled, token, chat_id = load_telegram()
        if not (enabled and token and chat_id):
            time.sleep(5)
            continue
        updates, err = _tg_get_updates(token, offset)
        if err:
            # 409 Conflict — бота уже слушает другой экземпляр (вторая
            # программа или --telegram-daemon): Telegram разрешает только
            # одного слушателя на бота. Ретраить бессмысленно — конфликт
            # останется, пока жив другой слушатель. Скажем понятно и
            # остановимся (не спамим ошибкой каждые 10 секунд).
            if "409" in err or "Conflict" in err:
                print("[✗] Telegram 409: этого бота уже слушает другая "
                      "программа (второй экземпляр или --telegram-daemon). "
                      "Telegram разрешает только одного слушателя на бота — "
                      "этот слушатель останавливается. Закройте лишний "
                      "экземпляр и перезапустите программу.")
                return
            # Сетевые ошибки (нет интернета, DNS, таймаут) ретраятся каждые
            # 10 сек, но печатаются один раз, а не на каждый цикл — иначе
            # при обрыве сети консоль заваливается одинаковыми строками.
            if err_since is None:
                print(f"[✗] Telegram: {err}\n"
                      f"[i] Сеть до Telegram недоступна — повторяю каждые "
                      f"10 секунд (без спама); о восстановлении сообщу.")
                err_since = time.time()
            time.sleep(10)
            continue
        if err_since is not None:
            print(f"[✓] Связь с Telegram восстановлена "
                  f"(не было {int(time.time() - err_since)} сек).")
            err_since = None
        for upd in updates:
            next_offset = _tg_handle_update(
                upd, token, recognizer, is_streaming, copy_to_buf, notify_new)
            if next_offset is not None:
                offset = next_offset
import telegram as _telegram  # noqa: E402 — форвардеры (патчи-совместимость)


def _fwd_route(name):
    def _forward(*args, **kwargs):
        return getattr(_telegram, name)(*args, **kwargs)
    _forward.__name__ = name
    return _forward

load_telegram = _fwd_route('load_telegram')
_tg_chat_action = _fwd_route('_tg_chat_action')
_tg_download = _fwd_route('_tg_download')
_tg_set_reaction = _fwd_route('_tg_set_reaction')
_tg_handle_callback = _fwd_route('_tg_handle_callback')
_tg_handle_text_command = _fwd_route('_tg_handle_text_command')
_tg_send_result = _fwd_route('_tg_send_result')

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
