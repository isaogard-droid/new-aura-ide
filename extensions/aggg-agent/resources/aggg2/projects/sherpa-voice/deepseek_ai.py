#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""DeepSeek API — лёгкий вызов через стандартную библиотеку (без requests).

Ключ берётся из:
  1) переменной окружения DEEPSEEK_API_KEY,
  2) файла .env рядом со скриптом (DEEPSEEK_API_KEY=sk-...).
Модель — из DEEPSEEK_MODEL (.env/окружение), по умолчанию "deepseek-v4-flash"
(по актуальной документации DeepSeek; старое имя deepseek-chat убрали).

API совместим с OpenAI: POST https://api.deepseek.com/chat/completions
"""

import json
import os
import time
import urllib.error
import urllib.request

API_URL = "https://api.deepseek.com/chat/completions"
BALANCE_URL = "https://api.deepseek.com/user/balance"
DEFAULT_MODEL = "deepseek-v4-flash"
TIMEOUT = 120

# Кэш проверки баланса: не дёргать /user/balance на каждый вызов.
# После нулевого баланса блокируем генерацию на TTL — API не долбится
# бесполезными попытками (money-path: hard gate до дорогого вызова).
BALANCE_TTL = 300
_balance_cache = {"ts": 0.0, "available": None}

_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

PROVIDER = "DeepSeek"
MODEL_DISPLAY = {
    "deepseek-v4-flash": "DeepSeek V4 Flash",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
}


def model_display_name(model=None):
    """Человекочитаемое имя модели для статуса сессии."""
    return MODEL_DISPLAY.get(model or load_model(), (model or load_model()))


# Системные промпты для кнопок-действий
PROMPTS = {
    "summary": ("Ты помощник для саммари голосовой записи. Сначала ПЕРЕСКАЖИ "
                "запись своими словами: 2–5 предложений, о чём говорилось. "
                "Потом выдели КЛЮЧЕВЫЕ МЫСЛИ: краткий список буллетов "
                "(по 1 строке на пункт). Без воды, только суть записи."),
    "answer": ("Ты — собеседник в голосовом дневнике. Сообщения выше — "
               "история сессии (диктовки и ответы). Последнее сообщение "
               "пользователя — ТЕКУЩАЯ диктовка или вопрос, на который "
               "нужно ответить. Ответь на него: если это вопрос — "
               "развёрнутый ответ по существу; если реплика — естественное "
               "продолжение диалога. Используй контекст сессии для точности. "
               "НЕ повторяй сообщение пользователя дословно или почти "
               "дословно — даже приветствие («привет» → «привет!» — это "
               "эхо, а не ответ): начни с содержательной фразы, которая "
               "развивает тему, комментирует или спрашивает в ответ. "
               "НЕ отвечай одиночным числом, если вопрос не про количество; "
               "не выдумывай факты и числа, которых нет в сессии."),
    "polish": ("Ты редактор русского текста, распознанного с микрофона. "
               "Твоя задача — аккуратная правка, а не пересказ и НЕ ответ: "
               "1) расставь знаки препинания и заглавные буквы; "
               "2) исправь только очевидные ошибки распознавания — искажённые "
               "слова, чьё значение однозначно ясно из контекста; "
               "3) восстанови явно усечённые слова («смер» → «смерть»), если "
               "значение однозначно; "
               "4) убери слова-паразиты («ну», «вот», «да», «то есть», «как бы») и "
               "только механические повторы-запинки («ну ну», «вот вот»); "
               "смысловые повторы («привет привет», «да да») НЕ убирай — "
               "это живая речь; "
               "5) если русскими буквами произнесено иностранное слово или число "
               "и его значение однозначно ясно — запиши правильно: иностранные "
               "слова латиницей («эппл» → Apple, «линукс» → Linux), а числа — "
               "цифрами («сикси севен эйт» → «6 7 8», «твенти файв» → «25», "
               "«ван ту сри» → «1 2 3», «офис фор» → «4»); английские "
               "числительные 1-20, десятки и сотни, произнесённые русскими "
               "буквами в потоке речи, заменяй цифрами уверенно — это "
               "однозначный паттерн; не угадывай только при настоящей "
               "неоднозначности (например, «ван» в середине осмысленной "
               "русской фразы); "
               "6) если в истории сессии (сообщения выше) слово уже записано "
               "правильно — исправляй диктовку по этому образцу: "
               "«езифектс» → EasyEffects, «гигаам» → GigaAM, даже если без "
               "контекста ты бы не был уверен; "
               "7) если русскими буквами произнесена ЦЕЛАЯ английская фраза "
               "(ошибка кода, системное сообщение) и её можно однозначно "
               "восстановить — запиши её на английском: "
               "«скейн нот эксес локал верибл» → cannot access local variable, "
               "«фаил нот фаунд» → file not found, "
                "«коннекшн таймаут» → connection timeout; "
                "это нормально для русской речи — технические фразы пишут "
                "латиницей; работает и в середине предложения: "
                "«у меня скейн нот эксес локал верибл» → «у меня cannot "
                "access local variable» (без кавычек вокруг фразы). "
                "8) пользователь говорит по-русски, но английский знает "
                "слабо и произносит технические/кодинг-термины с сильным "
                "русским акцентом, часто искажая их. Это НОРМАЛЬНО: "
                "восстанавливай правильный термин по звучанию, даже если "
                "произношение сильно кривое. Думай как редактор, который "
                "понимает, что «бэкенд» → backend, «фронтенд» → frontend, "
                "«пул реквест» → pull request, «дебаг» → debug, «коммит» → "
                "commit, «бренч»/«бранч» → branch, «мердж» → merge, "
                "«репозитори» → repository, «директори» → directory, "
                "«пэйл»/«фейл» → fail, «эксепшн» → exception, «аутпут» → "
                "output, «инпут» → input, «вербл» → variable, «стринг» → "
                "string, «фанкшн»/«фанкшен» → function, «конфиг» → config, "
                "«скрипт» → script, «деплой» → deploy, «билд» → build, "
                "«раннер» → runner, «хост» → host, «порт» → port, "
                "«токен» → token, «апи» → API, «эс эс эль» → SSL. Не "
                "требуй точного произношения: «гарнес» и «харнес» — оба "
                "могут означать harness; «энжин» и «инжин» — engine; "
                "«верибл», «верибле» и «варбл» — variable. Восстанавливай "
                "по контексту и звучанию; если уверен — пиши латиницей "
                "правильно, если сомневаешься — оставь как есть. "
                "ЗАПРЕЩЕНО: выдумывать или добавлять слова, числа и детали, "
               "которых нет в исходном тексте; переписывать фразы своими словами; "
               "домысливать неразборчивые фрагменты. Каждое изменение должно быть "
               "оправдано исходным текстом. Если правка неочевидна или ты не "
               "уверен — оставь фрагмент дословно. Если текст уже корректен — "
               "верни его без изменений. "
               "Верни ТОЛЬКО исправленный текст, без пояснений. "
               "ВАЖНО: если текст — вопрос («сколько тебе лет?»), НЕ отвечай "
               "на него — исправь сам вопрос (пунктуация, заглавные) и верни "
               "вопрос, а не ответ. Ты редактор, а не собеседник: длина и "
               "смысл результата должны совпадать с исходным текстом."),
    "day_summary": ("Ты — аналитик голосового дневника. Ниже — записи за один "
                    "день (каждая с отметкой времени). Собери сжатый итог "
                    "дня: какие темы поднимались, какие мысли повторялись, "
                    "что было важным. 3–8 предложений, без маркированных "
                    "списков, связным текстом. ЗАПРЕЩЕНО: выдумывать темы, "
                    "которых нет в записях; додумывать выводы. Если записей "
                    "мало или они бессвязны — честно скажи об этом, а не "
                    "придумывай содержание. Верни ТОЛЬКО текст итога."),
    "tags": ("Ты — классификатор записей голосового дневника. Ниже — одна "
             "запись. Придумай 2–3 коротких тега, отражающих тему (например: "
             "кодинг, тесты, идея, задача, покупки, план). Требования: одно "
             "слово или словосочетание без пробелов (используй дефис), "
             "нижний регистр, конкретика без воды. Верни ТОЛЬКО теги через "
             "запятую, без #, без пояснений."),
    "action_items": ("Ты извлекаешь задачи (action items) из голосовой "
                     "записи. Ниже — одна запись. Найди только то, что "
                     "звучит как действие, которое надо сделать: «сделать», "
                     "«починить», «написать», «позвонить», «проверить», "
                     "«добавить», «заказать», «купить», «отправить», "
                     "«напомнить», «разобраться», «настроить» и похожие "
                     "глаголы. Требования: каждый пункт — ОДНА задача, "
                     "начинается с глагола в начальной форме, коротко "
                     "(1 строка, без пояснений и пересказа); только "
                     "реальные задачи из текста, не каждое предложение. "
                     "Если в записи упомянут срок («до пятницы», «завтра», "
                     "«на этой неделе») или исполнитель («я», «нам», имя) — "
                     "добавь его к пункту через запятую, но НЕ выдумывай, "
                     "если не назван. ЗАПРЕЩЕНО: выдумывать задачи, которых "
                     "нет в записи; пересказывать запись; добавлять пункты "
                     "«просто так». Если задач нет — верни «Задач нет», "
                     "без пояснений. Верни ТОЛЬКО список задач, каждая "
                     "с новой строки, без нумерации."),
    "prompt_review": ("Ты — инженер, который превращает озвученную человеком "
                      "задачу в профессиональный кодинг-промпт (ТЗ с "
                      "чек-листом). Задача ниже — то, что человек сказал; "
                      "это единственный источник конкретики. "
                      "ЗАПРЕЩЕНО: выдумывать сценарии, примеры и темы из "
                      "быта, которых нет в задаче; аналогии «для "
                      "наглядности»; привязывать задачу к конкретным "
                      "библиотекам, технологиям или репозиториям, если их "
                      "нет в самой задаче. Только сухая конкретика по теме "
                      "задачи. "
                      "Ты не выполняешь задачу сам — ты формулируешь "
                      "задания агенту: "
                      "1) РЕСЁРЧ ПЕРВЫМ ДЕЛОМ — агент начинает с полного "
                      "веб-поиска ПО ТЕМЕ ЗАДАЧИ: как её решают другие "
                      "(паттерны, форумы, репозитории GitHub, статьи, "
                      "исследования, стандарты индустрии), проверяет "
                      "первоисточники, ссылку рядом с утверждением, "
                      "непроверенное — «проверить». Список источников агент "
                      "составляет сам по теме задачи — не подсказывай "
                      "готовые имена; "
                      "2) КОНКРЕТИКА — что именно в задаче проверить, "
                      "уточнить и решить; "
                      "3) ТЕСТЫ — какие тесты и проверки нужны для этой "
                      "задачи, только по её сути, без выдуманных сценариев; "
                      "4) ФАКТОРЫ — на что посмотреть внимательнее "
                      "(латентность, стоимость, качество, риски) и как "
                      "проверить; "
                      "5) КРИТЕРИЙ ГОТОВНОСТИ — как понять, что результат "
                      "правильный. "
                      "Формат: кодинг-промпт (обращение к агенту) с "
                      "чек-листом, без воды, без аналогий."),
}




# Каналы-владельцы: https://t.me/aidvizhenie · https://t.me/hilartem. Версия неповторима, новая — ещё лучше.
def _env_or_file(name, default=None):
    val = os.environ.get(name)
    if val:
        return val.strip()
    if os.path.exists(_ENV_FILE):
        try:
            with open(_ENV_FILE, encoding="utf-8") as _f:
                for line in _f:
                    line = line.strip()
                    if line.startswith(name + "="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass
    return default


def load_key():
    """Ключ из окружения/.env ИЛИ введённый при онбординге (firstrun).
    None, если ключа нет нигде."""
    key = _env_or_file("DEEPSEEK_API_KEY")
    if key:
        return key
    try:
        import firstrun
        return firstrun._load_cfg().get("deepseek_key") or None
    except Exception:
        return None


def enabled():
    """Глобальный выключатель DeepSeek (паттерн Zed 'disable_ai: true',
    OpenCode offline mode): один флаг — отключено ВСЁ AI-поведение.

    Флаг: DEEPSEEK_OFF=1 в env/.env ИЛИ deepseek_off=1 в конфиге firstrun.
    При выключенном — load_key() и auto_* игнорируются: программа работает
    чисто как транскрайбер. Возвращает False также без ключа."""
    if _env_or_file("DEEPSEEK_OFF", "0").lower() in ("1", "true", "yes", "on"):
        return False
    try:
        import firstrun
        if firstrun._load_cfg().get("deepseek_off") == "1":
            return False
    except Exception:
        pass
    return bool(load_key())


def load_model():
    """Модель из окружения/.env или DEFAULT_MODEL."""
    return _env_or_file("DEEPSEEK_MODEL", DEFAULT_MODEL)


def env_config(name, default=None):
    """Значение настройки из окружения или .env (например MIC_DEVICE)."""
    return _env_or_file(name, default)


def auto_polish_enabled():
    """Автоулучшение текста после распознавания (DEEPSEEK_AUTO_POLISH,
    по умолчанию вкл., если есть ключ)."""
    return _env_or_file("DEEPSEEK_AUTO_POLISH", "1").lower() in ("1", "true", "yes", "on")


def auto_tags_enabled():
    """Автотеги записей в истории (DEEPSEEK_AUTO_TAGS, по умолчанию вкл.,
    если есть ключ)."""
    return _env_or_file("DEEPSEEK_AUTO_TAGS", "1").lower() in ("1", "true", "yes", "on")


def _is_retryable(e):
    """Сетевые сбои и 5xx — ретраим; 4xx (неверный ключ, лимиты запроса)
    бессмысленно повторять — это не временное состояние."""
    if isinstance(e, urllib.error.HTTPError):
        return e.code >= 500 or e.code == 429
    return isinstance(e, (urllib.error.URLError, TimeoutError, ConnectionError))


def balance_available(key=None, ttl=BALANCE_TTL, _cache=None):
    """Проверка баланса DeepSeek ДО генерации (hard gate money-path).

    GET https://api.deepseek.com/user/balance → {"is_available": bool}.
    Возвращает (ok, err):
      ok=True            — баланс есть, можно генерировать
      ok=False           — баланс исчерпан, НЕ пускать в API (кэш на ttl)
      ok=None, err       — проверить не удалось (сеть/5xx): НЕ блокируем,
                           API сам вернёт 402 при нулевом балансе.
    _cache — внутренний (тесты передают свой), по умолчанию модульный."""
    if _cache is None:
        _cache = _balance_cache
    key = key or load_key()
    if not key:
        return None, "нет ключа DeepSeek"
    now = time.monotonic()
    if _cache["available"] is not None and now - _cache["ts"] < ttl:
        return _cache["available"], None
    req = urllib.request.Request(
        BALANCE_URL,
        headers={"Accept": "application/json",
                 "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # nosemgrep
            data = json.load(resp)
        available = bool(data.get("is_available"))
        _cache.update({"ts": now, "available": available})
        if not available:
            return False, "баланс DeepSeek исчерпан — пополните аккаунт"
        return True, None
    except urllib.error.HTTPError as e:
        # 401 (плохой ключ) — это не про баланс; пускаем — ask() сам вернёт
        # понятную ошибку. Сетевые/5xx тоже не блокируем (fail-open).
        e.close()
        return None, f"проверка баланса: HTTP {e.code}"
    except Exception as e:
        return None, f"проверка баланса недоступна: {type(e).__name__}: {e}"


def ask(system, user_text, key=None, model=None, temperature=0.3,
        retries=3, retry_delay=2.0, messages=None, usage=None):
    """usage (dict) — если передан, заполняется фактическими токенами из
    ответа API: prompt_cache_miss_tokens/prompt_cache_hit_tokens/
    completion_tokens (для статистики сессии)."""
    if usage is not None:
        usage.clear()
        usage.update({"prompt_cache_miss_tokens": 0,
                      "prompt_cache_hit_tokens": 0, "completion_tokens": 0})
    """Запрос к DeepSeek с ретраями на сетевые сбои/5xx/429.
    Возвращает (текст_ответа, ошибка_или_None).

    temperature — креативность ответа; для правки текста (polish) используйте
    0.0, чтобы модель не додумывала слова и числа.

    messages — опциональная история сессии (список {"role","content"},
    user/assistant/system). Если передана, она идёт после system-промпта,
    а user_text доклеивается последним сообщением."""
    key = key or load_key()
    if not key:
        return None, "нет ключа DeepSeek — положите DEEPSEEK_API_KEY в .env"
    if not user_text or not user_text.strip():
        return None, "пустой текст"
    # HARD GATE: нулевой баланс не пускаем в API (money-path, до дорогого
    # вызова). Проверка кэшируется; при недоступности проверки — fail-open,
    # API сам вернёт 402.
    ok, balance_err = balance_available(key)
    if ok is False:
        return None, balance_err
    model = model or load_model()
    msgs = [{"role": "system", "content": system}]
    if messages:
        msgs += messages
    msgs.append({"role": "user", "content": user_text})
    body = json.dumps({
        "model": model,
        "messages": msgs,
        "temperature": temperature,
        "stream": False,
        "thinking": {"type": "disabled"},  # не тратим токены на reasoning
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        })
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            # URL константный (API_URL), ключ — в Authorization, не в URL
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # nosemgrep
                data = json.load(resp)
            if usage is not None:
                u = data.get("usage", {})
                usage.clear()
                usage.update({k: u.get(k, 0) for k in (
                    "prompt_cache_miss_tokens", "prompt_cache_hit_tokens",
                    "completion_tokens")})
            return data["choices"][0]["message"]["content"].strip(), None
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            e.close()
            last_err = f"DeepSeek HTTP {e.code}: {detail}"
            if not _is_retryable(e):
                return None, last_err
        except Exception as e:
            last_err = f"DeepSeek: {type(e).__name__}: {e}"
            if not _is_retryable(e):
                return None, last_err
        if attempt < retries:
            time.sleep(retry_delay)
    return None, f"{last_err} (после {retries} попыток)"


if __name__ == "__main__":
    # smoke-test: python deepseek_ai.py "Привет, ответь одним словом"
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "Привет, ответь одним словом"
    out, err = ask(PROMPTS["answer"], text)
    print(out if out is not None else f"[ошибка] {err}")

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
