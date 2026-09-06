#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""chat.polish — полировка текста и эхо-защита (prompt/polish/echo).
Вынесено из chat.py механически (verbatim), 15.08.2026 — гейт god-файлов."""
import difflib
import os
import shlex
import tempfile

from publish import publish_result
from store import _session_add_and_compact, _vocab_text, get_session
from ui_utils import c_blue, c_info, c_warn


def _prompt_from_text():
    """Многострочный промпт вставкой (как /editor в OpenCode, минуя
    распознавание): вставь текст, Ctrl+D — конец, подтверди, Enter-отправка.
    Текст уходит в сессию как обычная диктовка (polish + результат)."""
    import subprocess
    editor = os.environ.get("EDITOR")
    if editor:
        # Как /editor в OpenCode: вставляешь текст в редактор (nano/vim),
        # сохраняешь и выходишь — текст возвращается.
        tmp = os.path.join(tempfile.gettempdir(), "sherpa_prompt.txt")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("")
        print(c_info(f"[~] Редактор: {editor} — вставьте текст, сохраните "
                     "и выйдите (Ctrl+O, Enter, Ctrl+X в nano)."))
        try:
            # shlex + список вместо shell=True: редактор берётся из конфига
            # пользователя — без шелла нет инъекций (semgrep 12.08.2026)
            subprocess.run([*shlex.split(editor), tmp], check=True)
            with open(tmp, encoding="utf-8") as f:
                raw = f.read().strip()
        except (subprocess.CalledProcessError, OSError) as e:
            print(c_warn(f"[i] Редактор не открылся ({e}) — использую "
                         "вставку строк."))
            raw = ""
        if not raw:
            print(c_warn("[i] Пусто — отменяю"))
            return
    else:
        print(c_info("[~] Вставьте текст (пустые строки разрешены, "
                     "Ctrl+D — закончить, Ctrl+C — отмена):"))
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        except KeyboardInterrupt:
            print(c_warn("\n[i] Отменено"))
            return
        raw = "\n".join(lines).strip()
    if not raw:
        print(c_warn("[i] Пусто — отменяю"))
        return
    preview = raw[:200].replace("\n", " ")
    print(f"  Вставлено: {len(lines)} строк, {len(raw)} символов\n  {preview}…")
    try:
        confirm = input(c_warn("Отправить? [y/N]: ")).strip().lower()
    except (EOFError, KeyboardInterrupt):
        confirm = ""
    if confirm not in ("y", "д", "yes", "да"):
        print(c_warn("[i] Отменено"))
        return
    print(c_blue("[ai] Улучшаю текст…"))
    import deepseek_ai
    usage = {}
    # Без диалога сессии — как в _polish_text (проверено вживую: с диалогом
    # polish-модель отвечает вместо правки). Вместо диалога — примеры
    # прошлых правок («было → стало») из сессии.
    req = _polish_request(raw)
    polished, err = deepseek_ai.ask(
        deepseek_ai.PROMPTS["polish"], req, temperature=0.0, usage=usage)
    if err:
        print(c_warn(f"[i] Улучшение не удалось ({err}) — отправляю как есть."))
        polished = raw
    else:
        polished = _sanitize_polish(raw, polished)
        if polished != raw:
            print(f"[text исправлено] {polished[:200]}…")
        else:
            print(c_blue("[text исправлено] без изменений"))
    _session_add_and_compact(raw, polished or raw, usage)
    publish_result(polished or raw, "📝 Промпт")


def _is_echo(out, prompt):
    """Эхо-детект: ответ почти дословно повторяет промпт (известная
    слабость DeepSeek-семейства — модель «продолжает» последнее сообщение
    вместо ответа). Ловим: точный повтор, вхождение промпта в ответ при
    близкой длине, близкий повтор коротких фраз. Содержательный ответ
    (вопрос в ответе, развитие темы) — НЕ эхо."""
    if not out or not prompt:
        return False
    def norm(s):
        return " ".join(s.strip().lower().split())
    out_n, prompt_n = norm(out), norm(prompt)
    if not out_n or not prompt_n:
        return False
    if out_n == prompt_n:
        return True
    # ответ = промпт + небольшой хвост («привет привет» → «привет привет
    # привет»): промпт целиком внутри ответа и ответ не сильно длиннее;
    # или ответ начинается с дословного повтора промпта (модель цитирует
    # отправленный текст и дописывает пару слов)
    if (prompt_n in out_n and len(out_n) <= len(prompt_n) * 1.8) or (
            out_n.startswith(prompt_n)
            and len(out_n) <= len(prompt_n) * 1.5):
        return True
    # почти-повтор коротких фраз («два» → «Два.», «25» → «25»)
    ratio = difflib.SequenceMatcher(None, out_n, prompt_n).ratio()
    return len(prompt_n) <= 30 and ratio >= 0.8


def _ask_no_echo(prompt_key, marked, usage=None, retries=1, temperature=0.3,
                 echo_ref=None):
    """Запрос к DeepSeek с эхо-защитой (известная слабость DeepSeek:
    «продолжает» последнее сообщение — возвращает дословный повтор
    промпта/исходного текста вместо ответа). echo_ref — исходный текст
    записи (без обёртки): модель иногда возвращает «полированный»
    исходник вместо пересказа/задач — это тоже эхо. При эхе — переспрос
    с требованием содержательного ответа; если снова эхо — возвращаем
    как есть (честно: модель упёрлась). Возвращает (out, err).

    ВАЖНО: без messages=_session_context() — история сессии НЕ передаётся
    (паттерн LangChain context engineering «Isolate Context Strategy»:
    одноразовые задачи extraction/summarization идут с изолированным
    контекстом). С историей при низкой температуре модель «продолжает»
    последнее сообщение ассистента в истории (то самое эхо, но сравнить
    не с чем) — проверено живьём: «Задачи»/«Саммари» возвращали
    приветствие ассистента из сессии вместо результата."""
    import deepseek_ai as _dai

    def is_echo(out, prompt):
        if _is_echo(out, prompt):
            return True
        # «полированный» повтор исходного текста (пересказ == исходник):
        # ratio ≥ 0.75 без лимита длины
        if echo_ref and out and len(out.strip()) > 0:
            n_out = " ".join(out.strip().lower().split())
            n_ref = " ".join(str(echo_ref).strip().lower().split())
            if n_out and n_ref:
                r = difflib.SequenceMatcher(None, n_out, n_ref).ratio()
                if r >= 0.75:
                    return True
        return False

    out, err = _dai.ask(_dai.PROMPTS[prompt_key], marked,
                        temperature=temperature, usage=usage)
    for _ in range(retries):
        if err or not is_echo(out, marked):
            break
        print(c_warn("[i] Эхо-ответ — переспрашиваю…"))
        demand = (marked + "\n\n(Предыдущий ответ был дословным повтором "
                  "промпта или исходного текста. Это не результат. Выполни "
                  "задачу по существу: верни ТОЛЬКО результат обработки, "
                  "без повтора исходного текста.)")
        out, err = _dai.ask(_dai.PROMPTS[prompt_key], demand,
                            temperature=temperature, usage=usage)
    if not err and is_echo(out, marked):
        print(c_warn("[i] Ответ снова повтор — отдаю как есть."))
    return out, err


def _sanitize_polish(raw, polished):
    """Пост-валидация полировки (паттерн из гайда DeepSeek: проверяй
    вывод модели). Если «исправление» в разы длиннее исходника — модель
    ушла в ответ/пересказ вместо правки («сколько тебе лет?» → целый
    абзац-ответ) — берём исходный текст, чтобы в сессию и в answer не
    ушёл ответ вместо вопроса."""
    if not polished or not polished.strip():
        return raw
    if len(polished) > len(raw) * 2.5 + 40:
        return raw
    return polished


def _polish_examples(sess, limit=3):
    """Пары «было → стало» из сессии — словарь прошлых правок для
    полировки. НЕ диалог: проверено вживую, диалоговый контекст сбивает
    модель-редактора в собеседника (отвечает вместо правки), а примеры
    правок — нет. Правки помечаются при записи (kind="polish" в
    _session_add_and_compact) — не гадаем по длине/сходству, а берём
    только настоящие пары (raw диктовка → исправленный текст)."""
    msgs = sess.messages if hasattr(sess, "messages") else []
    out = []
    for i in range(len(msgs) - 1, -1, -1):
        if len(out) >= limit:
            break
        m = msgs[i]
        if m.get("kind") != "polish" or i == 0:
            continue
        prev = msgs[i - 1]
        if prev.get("role") != "user":
            continue
        raw, pol = prev.get("content", ""), m.get("content", "")
        if not raw or not pol or pol == raw:
            continue
        if len(raw) > 200:
            raw = raw[:200] + "…"
        if len(pol) > 200:
            pol = pol[:200] + "…"
        out.append(f"Было: {raw}\nСтало: {pol}")
    return "\n\n".join(out)


def _polish_request(raw):
    """Запрос полировке: примеры прошлых правок (из сессии) + словарь
    терминов + текст для правки. Без диалога — он сбивает модель-редактора
    (проверено вживую)."""
    parts = []
    examples = _polish_examples(get_session())
    if examples:
        parts.append(f"Примеры прошлых правок (Было → Стало):\n{examples}")
    vocab = _vocab_text()
    if vocab:
        parts.append(f"Словарь терминов (говоришь так → пиши так): {vocab}")
    parts.append(f"Текст для правки:\n{raw}")
    return "\n\n".join(parts)


def _polish_text(text):
    """Автоулучшение текста через DeepSeek (знаки препинания, очевидные
    ошибки распознавания). Возвращает исправленный текст; при ошибке или
    отключении — исходный."""
    import deepseek_ai
    raw = text
    if deepseek_ai.auto_polish_enabled() and deepseek_ai.enabled():
        from termui import step as _step
        print(_step("ai", "Улучшаю текст (знаки препинания, смысл)…"))
        usage = {}
        # БЕЗ диалогового контекста — как в текстовом режиме (проверено
        # вживую: с диалогом polish нестабилен — то правит, то возвращает
        # как есть, то отвечает вместо правки). Вместо диалога — примеры
        # прошлых правок из сессии («было → стало»): словарь без срыва
        # роли редактора.
        req = _polish_request(text)
        polished, err = deepseek_ai.ask(
            deepseek_ai.PROMPTS["polish"], req, temperature=0.0, usage=usage)
        if err:
            print(f"[i] Улучшение не удалось ({err}) — использую исходный текст.")
        else:
            polished = _sanitize_polish(text, polished)
            if polished and polished != text:
                text = polished
                print(c_blue(f"[text исправлено] {text}"))
            else:
                print(c_blue("[text исправлено] без изменений"))
            # learning loop: пара raw → polished (для hotwords/vocab)
            try:
                import hotwords
                hotwords.record(raw, polished or raw)
                hotwords.learn()
            except Exception:
                pass
        _session_add_and_compact(raw, polished or raw, usage)
    return text


# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
