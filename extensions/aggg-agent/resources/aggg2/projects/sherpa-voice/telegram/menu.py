#!/usr/bin/env python3
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""telegram.menu — меню и callback-диспетчер."""
import os
import time

from export import save_text_export

from . import ratelimit
from .api import _tg_get_chat_id
from .send import tg_send_document
from .state import _tg_state_load, save_telegram

_TG_BUSY = set()            # чаты, где действие уже выполняется
_TG_LAST = {}               # чат → (действие, время) — защита от двойного нажатия
_TG_DEBOUNCE_SEC = 30       # повторное нажатие той же кнопки в этот срок — игнор

def _telegram_menu(text=None):
    """Подменю Telegram: токен / chat_id (или узнать самому через '?') /
    вкл-выкл / отправить текущий текст / тест / очистить. Файл перечитывается
    на каждом шаге — ручные правки подхватываются сразу."""
    while True:
        enabled, token, chat_id = load_telegram()
        status = "вкл" if enabled else "выкл"
        token_masked = "…" + token[-4:] if token else "(не задан)"
        chat_str = chat_id if chat_id else "(не задан)"
        try:
            sub = input(f"\n[ai] Telegram ({status}): токен {token_masked}, "
                        f"chat_id {chat_str}\n"
                        f"[ai] [1] 🪙 Токен  [2] 🆔 Chat ID  [3] 🔄 Вкл/выкл  "
                        f"[4] 📤 Отправить текст  [5] 🧪 Тест  [6] 🗑 Очистить  "
                        f"[7] 🔑 DeepSeek  [Enter] назад\n    > ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not sub:
            return
        if sub == "1":
            print("[i] Токен бота из @BotFather (вид 123456:ABC…). Введите:")
            try:
                new_token = input("    > ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if not new_token:
                print("[i] Оставил как было.")
                continue
            token = new_token
            if save_telegram(enabled, token, chat_id):
                print("[✓] Токен сохранён.")
        elif sub == "2":
            print("[i] Chat ID — число (группы — с минусом). Если не знаете, "
                  "введите '?' — я")
            print("[i] узнаю его сам (бот должен получить от вас хоть одно "
                  "сообщение).")
            try:
                val = input("    > ").strip()
            except (EOFError, KeyboardInterrupt):
                continue
            if not val:
                print("[i] Оставил как было.")
                continue
            if val == "?":
                chat_id, err = _tg_get_chat_id(token)
                if err:
                    print(f"[✗] {err}")
                    continue
                print(f"[✓] Нашёл chat_id: {chat_id}")
                if save_telegram(enabled, token, chat_id):
                    print("[✓] Chat ID сохранён.")
                continue
            if not val.lstrip("-").isdigit():
                print("[i] Chat ID — число (можно с минусом).")
                continue
            chat_id = val
            if save_telegram(enabled, token, chat_id):
                print("[✓] Chat ID сохранён.")
        elif sub == "3":
            if not (token and chat_id):
                print("[i] Сначала задайте токен и chat_id (пункты 1–2) — "
                      "включать нечего.")
                continue
            enabled = not enabled
            if save_telegram(enabled, token, chat_id):
                print(f"[✓] Отправка в Telegram "
                      f"{'включена' if enabled else 'выключена'}.")
        elif sub == "4":
            if not (enabled and token and chat_id):
                print("[i] Режим выключен или не настроен — включите и "
                      "проверьте (пункты 1–3, 5).")
                continue
            if not text:
                print("[i] Нет текста для отправки — текст появляется после "
                      "распознавания.")
                continue
            ok, err = _tg_send_result(text)
            if ok:
                print("[✓] Отправлено в Telegram.")
            else:
                print(f"[✗] {err}")
        elif sub == "5":
            if not (token and chat_id):
                print("[i] Сначала задайте токен и chat_id (пункты 1–2).")
                continue
            ok, err = _tg_request(token, "sendMessage", {
                "chat_id": chat_id, "text": "Проверка связи от sherpa-voice ✓"})
            if ok:
                print("[✓] Тестовое сообщение отправлено — проверьте Telegram.")
            else:
                print(f"[✗] {err}")
        elif sub == "6":
            if save_telegram(False, "", ""):
                print("[✓] Настройки Telegram очищены, режим выключен.")
        elif sub == "7":
            # DeepSeek: ввести ключ или вернуть «спросить при старте»
            import deepseek_ai
            import firstrun
            cfg = firstrun._load_cfg()
            has = bool(deepseek_ai.enabled())
            print(f"[i] DeepSeek: {'активен (вкл.)' if has else 'выключен (без ИИ)'}.")
            if not has:
                try:
                    key = input("    Ключ (sk-…, Enter — пропустить): ").strip()
                except (EOFError, KeyboardInterrupt):
                    key = ""
                if key.startswith("sk-"):
                    cfg["deepseek_key"] = key
                    cfg.pop("deepseek_off", None)  # ввод ключа = включить ИИ
                    firstrun._save_cfg(cfg)
                    print("[✓] DeepSeek-ключ сохранён — улучшение и действия вкл.")
                else:
                    firstrun.unskip()
                    print("[i] Оставил без ключа — при следующем старте спрошу "
                          "снова (или положите DEEPSEEK_API_KEY в .env).")
            else:
                try:
                    ans = input("    [1] Убрать ключ  [Enter] назад: ").strip()
                except (EOFError, KeyboardInterrupt):
                    ans = ""
                if ans == "1":
                    cfg.pop("deepseek_key", None)
                    firstrun._save_cfg(cfg)
                    print("[i] Ключ убран — режим без ИИ (только запись).")
        else:
            print("[i] Не понял выбор — Enter = назад.")

def _impl_tg_handle_callback(cq, token):
    """Нажатие inline-кнопки: снять спиннер (answerCallbackQuery), показать
    «⏳ Готовлю…» (DeepSeek думает секунды — юзер должен видеть отклик, а
    не «ничего не происходит»), выполнить действие и прислать результат в
    тот же чат новой sendMessage с теми же кнопками — цепочка действий не
    обрывается. Повторное нажатие (занятость/30с) не дублирует запрос."""
    data = (cq.get("data") or "").strip().lower().lstrip("/")
    data = {"саммари": "summary", "ответить": "answer", "кодинг": "coding",
            "кодинг-промт": "coding", "экспорт": "export",
            "документация": "docs", "помощь": "docs", "help": "docs"}.get(data, data)
    cq_id = cq.get("id")
    chat_id = (cq.get("message") or {}).get("chat", {}).get("id")
    if not chat_id:
        return
    state = _tg_state_load(chat_id)
    text = state.get("text")
    if data == "docs":
        # документация — мгновенно, без контекста и без статуса «Готовлю»
        if cq_id:
            _tg_request(token, "answerCallbackQuery",
                        {"callback_query_id": cq_id})
        _tg_send_docs(token, chat_id)
        return
    # Входной antiflood на платные DeepSeek-действия (кнопки Саммари/
    # Ответить/Кодинг — каждый клик = платный вызов; «фарм» кнопок = деньги
    # владельца). Экспорт/документация — бесплатные, не лимитируются.
    # Отказ — понятным сообщением, без молчания (RATE LIMIT ALERT TEXT).
    user_id = (cq.get("from") or {}).get("id")
    if user_id is not None and data in ("summary", "answer", "coding"):
        ok, retry_after = ratelimit.action_allowed(user_id)
        if not ok:
            if cq_id:
                _tg_request(token, "answerCallbackQuery",
                            {"callback_query_id": cq_id,
                             "text": f"⏳ Слишком часто — подождите {retry_after} сек"})
            _tg_request(token, "sendMessage", {
                "chat_id": chat_id,
                "text": (f"⏳ Слишком часто — подождите {retry_after} сек "
                         f"и попробуйте ещё раз.")})
            print(f"[i] rate-limit: юзер {user_id} превысил лимит действий")
            return
    if not text:
        if cq_id:
            _tg_request(token, "answerCallbackQuery",
                        {"callback_query_id": cq_id})
        _tg_request(token, "sendMessage", {
            "chat_id": chat_id,
            "text": "Нет контекста для действий — пришлите голосовое."})
        return
    _tg_chat_action(token, chat_id)   # «печатает…» — кнопки работают
    now = time.time()
    if chat_id in _TG_BUSY:
        if cq_id:
            _tg_request(token, "answerCallbackQuery",
                        {"callback_query_id": cq_id,
                         "text": "⏳ Уже готовлю — секунду"})
        return
    last = _TG_LAST.get(chat_id)
    if last and last[0] == data and now - last[1] < _TG_DEBOUNCE_SEC:
        if cq_id:
            _tg_request(token, "answerCallbackQuery",
                        {"callback_query_id": cq_id,
                         "text": "✅ Уже сделано — смотри выше"})
        return
    if cq_id:
        _tg_request(token, "answerCallbackQuery",
                    {"callback_query_id": cq_id})
    label = {"summary": "Саммари", "answer": "Ответ",
             "coding": "Кодинг-промт", "export": "Экспорт"}.get(data, data)
    _tg_request(token, "sendMessage",
                {"chat_id": chat_id, "text": f"<b>Готовлю {label}…</b>",
                 "parse_mode": "HTML"})
    _TG_BUSY.add(chat_id)
    try:
        if data == "export":
            _tg_do_export(token, chat_id, text, state)
            _TG_LAST[chat_id] = (data, now)
            return
        prompt_key = {"summary": "summary", "answer": "answer",
                      "coding": "prompt_review"}.get(data)
        if not prompt_key:
            return
        import deepseek_ai
        if not deepseek_ai.enabled():
            _tg_request(token, "sendMessage", {
                "chat_id": chat_id,
                "text": "DeepSeek не подключен — положите DEEPSEEK_API_KEY в .env "
                        "проекта (те же действия, что меню [1]/[2]/[4] в консоли)."})
            return
        if data == "coding":
            marked = (f"Озвученная человеком задача (после распознавания "
                      f"и очистки речи):\n{text}")
        else:
            marked = f"Транскрипт голосовой записи: «{text}»"
        # эхо-защита (как в CLI-меню): DeepSeek иногда возвращает дословный
        # повтор промпта или исходного текста вместо результата — переспрашиваем
        from transcribe import _ask_no_echo
        temp = 0 if prompt_key == "action_items" else 0.3
        out, err = _ask_no_echo(prompt_key, marked, temperature=temp,
                                echo_ref=text)
        if err:
            _tg_request(token, "sendMessage",
                        {"chat_id": chat_id, "text": f"[✗] {err}"})
            return
        state[data] = out
        prefix = {"summary": "Саммари", "answer": "Ответ",
                  "coding": "Кодинг-промт"}[data]
        # результат — файлом .txt; кнопки-меню и подмешка НЕ нужны на
        # результатах кнопок — только на транскрипте (чтобы не зацикливать
        # меню само на себе)
        ok, err = _tg_send_result(out, prefix, chat_id=chat_id)
        if not ok:
            print(f"[✗] {err}")
        _TG_LAST[chat_id] = (data, now)
    finally:
        _TG_BUSY.discard(chat_id)

def _tg_do_export(token, chat_id, text, state):
    """Кнопка Экспорт: MD (+PDF, если есть шрифты) уходит файлом в тот же
    чат; результаты саммари/ответа/кодинг-промта включаются в экспорт."""
    md_path, pdf_path, err = save_text_export(
        text, summary=state.get("summary"), answer=state.get("answer"),
        review=state.get("coding"))
    if err:
        print(f"[i] {err}")
    for p in (md_path, pdf_path):
        if not p:
            continue
        ok, err_tg = tg_send_document(p, chat_id=chat_id)
        if ok:
            print(f"[✓] {os.path.basename(p)} отправлен в Telegram")
        elif err_tg:
            print(f"[✗] {err_tg}")

def _tg_send_docs(token, chat_id):
    """Отправляет актуальный README в чат (кнопка «Документация», /docs)."""
    readme = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
    if not os.path.isfile(readme):
        _tg_request(token, "sendMessage", {
            "chat_id": chat_id,
            "text": "README.md не найден рядом со скриптом."})
        return
    _tg_request(token, "sendMessage", {
        "chat_id": chat_id, "text": "📖 Документация (актуальный README):"})
    ok, err = tg_send_document(readme, chat_id=chat_id)
    if ok:
        print("[✓] Документация отправлена в Telegram")
    elif err:
        print(f"[✗] {err}")

def _tg_handle_ping(token, chat_id):
    """Healthcheck бота: /ping → «pong 🏓». Индустриальный паттерн
    минимальных ботов (/start, /ping, /count — pongbot и аналоги);
    пользователь проверяет, что бот жив и отвечает."""
    _tg_request(token, "sendMessage", {
        "chat_id": chat_id, "text": "pong 🏓"})

def _impl_tg_handle_text_command(msg, token):
    """Текстовые команды-фолбэк, если кнопки недоступны: «саммари»,
    «/answer», «экспорт» и т.п. — ведут себя как нажатие кнопки."""
    text = (msg.get("text") or "").strip().lower()
    if not text:
        return
    chat_id = msg.get("chat", {}).get("id")
    cmd = text.lstrip("/")
    if cmd == "ping":
        # healthcheck «бот жив» — отвечаем напрямую, не через кнопки
        _tg_handle_ping(token, chat_id)
        return
    if cmd not in ("summary", "answer", "coding", "export", "docs",
                   "саммари", "ответить", "кодинг", "кодинг-промт", "экспорт",
                   "документация", "помощь", "help"):
        return
    _tg_handle_callback({"id": None, "data": cmd, "from": msg.get("from"),
                         "message": {"chat": {"id": chat_id}}}, token)
import telegram as _telegram  # noqa: E402 — форвардеры (патчи-совместимость)


def _fwd_route(name):
    def _forward(*args, **kwargs):
        return getattr(_telegram, name)(*args, **kwargs)
    _forward.__name__ = name
    return _forward

_tg_handle_callback = _fwd_route('_tg_handle_callback')
_tg_handle_text_command = _fwd_route('_tg_handle_text_command')
load_telegram = _fwd_route('load_telegram')
_tg_request = _fwd_route('_tg_request')
_tg_send_result = _fwd_route('_tg_send_result')
_tg_chat_action = _fwd_route('_tg_chat_action')

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
