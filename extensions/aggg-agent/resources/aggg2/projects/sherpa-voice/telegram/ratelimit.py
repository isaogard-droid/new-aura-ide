#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""telegram.ratelimit — входной antiflood по юзеру (from.id).

Защищает сервер от «фарма»: юзер шлёт голосовые пачками (каждый →
транскрипция + полировка DeepSeek) или жмёт кнопки подряд (каждая →
платный DeepSeek-вызов). Паттерн индустрии — grammY ratelimiter
(timeFrame/limit, MEMORY_STORE, keyGenerator=from.id, dismiss on arrival,
next() не вызывается), подтверждено ресёрчем 14-16.08.2026
(findings 531/536/617/647 в research.db).

Правила:
- in-memory sliding window (одного процесса достаточно — Redis не тащим);
- ключ — (bucket, user_id); bucket: "voice" / "action";
- интервалы — time.monotonic() (time.time() может пойти назад);
- лимиты env-конфигурируемые, 0 = unlimited (явная семантика);
- отказ не молчаливый: вызывающий получает retry_after и шлёт юзеру
  понятное сообщение «Слишком часто — подождите N сек».
"""
import os
import threading
import time
from collections import defaultdict, deque

# Голосовых от одного юзера в минуту (0 = unlimited).
TG_RATE_VOICE_PER_MIN = int(os.environ.get("TG_RATE_VOICE_PER_MIN", "10"))
# DeepSeek-действий (кнопки Саммари/Ответить/Кодинг) от одного юзера в минуту.
TG_RATE_ACTION_PER_MIN = int(os.environ.get("TG_RATE_ACTION_PER_MIN", "5"))

_WINDOW_SEC = 60.0

_lock = threading.Lock()
_hits = defaultdict(deque)  # (bucket, user_id) -> deque[monotonic ts]


def _allowed(bucket, user_id, limit):
    """Проверяет и учитывает входящий вызов. Возвращает (ok, retry_after_sec).
    ok=True — можно; ok=False — превышен лимит, retry_after — сколько ждать."""
    if limit <= 0:
        return True, 0
    now = time.monotonic()
    key = (bucket, user_id)
    with _lock:
        q = _hits[key]
        # выкинуть записи старше окна
        while q and q[0] <= now - _WINDOW_SEC:
            q.popleft()
        if len(q) >= limit:
            retry_after = int(q[0] + _WINDOW_SEC - now) + 1
            return False, retry_after
        q.append(now)
        return True, 0


def voice_allowed(user_id):
    """Можно ли юзеру прислать ещё одно голосовое сейчас."""
    return _allowed("voice", user_id, TG_RATE_VOICE_PER_MIN)


def action_allowed(user_id):
    """Можно ли юзеру запустить ещё одно DeepSeek-действие сейчас."""
    return _allowed("action", user_id, TG_RATE_ACTION_PER_MIN)


def reset_for_tests():
    """Сбрасывает окна (для юнит-тестов)."""
    with _lock:
        _hits.clear()


# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
