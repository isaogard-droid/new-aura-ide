"""Self-learning loop: исправления → hotwords для ASR + словарь для полировки.

Паттерн capslearn (github Deepmindlearning/capslearn): пара
«raw (как распознал ASR) → polished (как исправил DeepSeek/пользователь)»,
миннинг повторяющихся коррекций (>=2) → термины в hotwords и vocab.

Файлы (в ~/.cache/sherpa-voice/):
  corrections.jsonl   — пары «raw | polished», одна на строку
  hotwords.txt        — токенизированные hotwords для sherpa (text2token)
  denylist.txt        — коррекции, которые НЕ учить (пользователь отверг)
"""
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcribe  # noqa: E402  (нужны константы путей, vocab)

CACHE = os.path.expanduser("~/.cache/sherpa-voice")
CORRECTIONS = os.path.join(CACHE, "corrections.jsonl")
DENYLIST = os.path.join(CACHE, "denylist.txt")
HOTWORDS_RAW = os.path.join(CACHE, "hotwords_input.txt")
HOTWORDS_TOK = os.path.join(CACHE, "hotwords.txt")

# Сколько раз коррекция должна повториться, чтобы стать термином
MIN_REPEAT = 2
# Минимальная длина фразы-коррекции (короче — шум)
MIN_LEN = 3


def record(raw, polished):
    """Сохранить пару raw → polished (вызывается после полировки)."""
    raw = (raw or "").strip()
    polished = (polished or "").strip()
    if not raw or not polished or raw == polished:
        return
    if len(raw) < 2 or len(polished) < 2:
        return
    os.makedirs(CACHE, exist_ok=True)
    with open(CORRECTIONS, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{raw}\t{polished}\n")


def _load_corrections():
    if not os.path.isfile(CORRECTIONS):
        return []
    out = []
    with open(CORRECTIONS, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if "\t" in line:
                raw, polished = line.split("\t", 1)
                out.append((raw.strip(), polished.strip()))
    return out


def _load_denylist():
    if not os.path.isfile(DENYLIST):
        return set()
    with open(DENYLIST, encoding="utf-8") as f:
        return {ln.strip().lower() for ln in f if ln.strip()}


_PUNCT_STRIP = ".,!?;:…()«»\"'"

# Служебные слова, которые не бывают терминами: предлоги, союзы,
# местоимения, частицы. Learning-loop не должен учить их как hotwords
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# (они появляются в polished из-за перестановки/регистра полировки).
_STOP_WORDS = {
    "по", "это", "то", "на", "в", "во", "с", "со", "и", "для", "что",
    "как", "но", "не", "он", "она", "они", "мы", "вы", "ты", "я", "у",
    "о", "об", "от", "до", "из", "за", "к", "ко", "а", "же", "бы", "ли",
    "если", "тот", "так", "вот", "уже", "ещё", "еще", "все", "всё", "нет",
    "да", "там", "тут", "здесь", "когда", "потому", "поэтому", "очень",
    # слова-паразиты и связки живой речи (не термины)
    "есть", "что-то", "какой-то", "как-то", "по-моему", "кстати",
    "например", "вообще", "допустим", "скажем", "наверное", "конечно",
    "просто", "именно", "самое", "главный", "который", "интересует",
    "сейчас", "один", "целом", "говоря", "верно", "полностью",
    "везде", "правильно", "годное", "базе", "шумный", "полуавтоматически",
    "распознавание", "паттерны", "транскрибирует", "ссылается", "покрыл",
}


def _norm_word(w):
    """Слово без пунктуации по краям — только для сравнения, не для записи."""
    return w.strip(_PUNCT_STRIP)


def _diff_terms(raw, polished):
    """Вытащить пары «ошибочно → исправлено» из raw/polished.

    Простая версия: если raw встречается в polished как подстрока после
    замены — пропускаем; ищем слова, которых нет в raw, но есть в
    polished (добавленные/исправленные термины). Регистр сохраняется —
    для hotwords (bpe чувствителен) и vocab.

    Слова, отличающиеся от raw только пунктуацией на концах («базе.»
    при raw «базе») — НЕ термины: это следы полировки пунктуации, а не
    исправления распознавания (иначе learning-loop копит мусор в vocab).
    """
    raw_words = set(re.findall(r"[A-Za-zА-Яа-яЁё0-9_+.-]+", raw.lower()))
    raw_norm = {_norm_word(w) for w in raw_words}
    polished_words = re.findall(r"[A-Za-zА-Яа-яЁё0-9_+.-]+", polished)
    added = []
    for w in polished_words:
        wl = w.lower()
        if wl in raw_words:
            continue
        clean = _norm_word(w)
        if clean.lower() in raw_norm:
            continue  # то же слово с пунктуацией по краям — не термин
        if clean.lower() in _STOP_WORDS:
            continue  # служебное слово — не термин
        if len(clean) >= MIN_LEN:
            # сохраняем без пунктуации по краям: «CRG.» → «CRG»,
            # иначе пунктуация полировки снова копит мусор
            added.append(clean)
    return added


def _count_terms():
    """Считает, какие слова появлялись в исправлениях чаще всего."""
    counts = {}
    for raw, polished in _load_corrections():
        for term in _diff_terms(raw, polished):
            counts[term] = counts.get(term, 0) + 1
    return counts


def learn(force=False):
    """Миннинг коррекций: повторяющиеся (>=MIN_REPEAT) → hotwords.

    Возвращает список выученных терминов. Термины пишутся в нижнем
    регистре (bpe-модель русского чувствительна к регистру — хранит
    токены в нижнем; символьная GigaAM — регистронезависима).
    """
    denylist = _load_denylist()
    counts = _count_terms()
    learned = []
    for term, n in sorted(counts.items(), key=lambda x: -x[1]):
        if n < MIN_REPEAT:
            continue
        if term.lower() in denylist:
            continue
        learned.append(term)
    if learned:
        _append_hotwords(learned)
        _append_vocab(learned)
    return learned


def _append_hotwords(terms):
    """Добавить термины в hotwords_input.txt (сырой).

    Регистр — нижний: русские bpe-модели хранят токены в нижнем регистре,
    text2token требует точного совпадения (проверено на zipformer-ru)."""
    os.makedirs(CACHE, exist_ok=True)
    existing = set()
    if os.path.isfile(HOTWORDS_RAW):
        with open(HOTWORDS_RAW, encoding="utf-8") as f:
            existing = {ln.strip().lower() for ln in f if ln.strip()}
    new = []
    for t in terms:
        low = t.lower()
        if low in existing:
            continue
        # латиницу не добавляем: в русских bpe-моделях нет латинских токенов
        # (проверено: 0 латинских токенов в zipformer-ru/gigaam) — их берёт
        # полировка DeepSeek через vocab.txt
        if re.search(r"[a-z]", low) and not re.search(r"[а-яё]", low):
            continue
        new.append(low)
    if not new:
        return
    with open(HOTWORDS_RAW, "a", encoding="utf-8", newline="\n") as f:
        for t in new:
            f.write(t + "\n")
    print(f"[learn] hotwords: +{len(new)} ({', '.join(new[:5])}{'…' if len(new) > 5 else ''})")


def _append_vocab(terms):
    """Термины → словарь полировки (vocab.txt): «говоришь так → пиши так».

    НЕ добавляет пары «слово → слово»: vocab — ручной словарь произношений
    («церг → CRG»), а не список допустимых слов. Пара (t, t) — мусор:
    полировка и так знает слово, а learning-loop копил «CRG → CRG»,
    «env → env» (проверено 08.2026). Для распознавания редких слов
    термины уходят в hotwords (см. _append_hotwords).
    """
    return 0


def sync_from_vocab():
    """Ключи vocab-словаря («как говоришь») → hotwords.

    vocab хранит пары «говоришь так → пиши так»: ключ — как слово
    произносится («опен код», «камфифокс»). Это идеальные hotwords —
    модель подтянет произношение, а полировка превратит в правильное
    написание. Вызывать при старте, до load_model."""
    try:
        pairs = transcribe._vocab_load()
    except Exception:
        return
    keys = [k for k, _ in pairs if re.search(r"[а-яё]", k.lower())]
    if keys:
        _append_hotwords(keys)


def from_session(sess, limit=15):
    """Контекст-подкормка: термины из последних сообщений сессии.

    Русские термины → hotwords (влияют на ASR); латинские/смешанные
    (opencode, AGENTS.md) → vocab-словарь полировки (их берёт DeepSeek)."""
    rus_terms, lat_terms = [], []
    for msg in sess.messages[-6:]:
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        for m in re.finditer(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_.+/-]{1,}", content):
            w = m.group(0)
            if w.lower() in ("the", "and", "for", "with", "you", "this",
                             "или", "что", "как", "для", "при"):
                continue
            if w.islower() and not re.search(r"[а-яёА-ЯЁ]", w):
                continue
            if re.search(r"[а-яёА-ЯЁ]", w):
                rus_terms.append(w)
            else:
                lat_terms.append(w)
    if rus_terms:
        _append_hotwords(rus_terms[:limit])
    if lat_terms:
        _append_vocab(lat_terms[:limit])
    return rus_terms[:limit] + lat_terms[:limit]

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
