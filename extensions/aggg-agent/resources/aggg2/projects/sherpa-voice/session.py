"""Сессия диалога для DeepSeek — контекст как в харнессах (OpenCode/Claude Code).

Каждый вызов API stateless: память держим сами в файле сессии:
массив сообщений (user/assistant) + чекпоинт-сводка (summary).

Автокомпакт по паттерну OpenCode V2:
- перед ростом истории оцениваем токены (4 символа ~ 1 токен);
- при превышении прагматичного лимита старые ходы сжимаем в сводку
  (цель/факты/сделано/активное/блокеры/дальше), хвост keep_tokens
  сохраняется дословно;
- сводка вставляется в контекст как «исторический контекст», не как
  инструкция.

DeepSeek V4: контекст 1M токенов, кэш префиксов включён по умолчанию
(cache-hit входные токены дешевле ~в 10 раз) — повторный префикс истории
почти бесплатен, поэтому сессия экономически оправдана.
"""
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

import json
import os
import time

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "sherpa-voice",
                         "sessions")

# Лимиты (по OpenCode-паттерну, подогнаны под DeepSeek V4)
CONTEXT_LIMIT = 1_000_000      # реальный контекст deepseek-v4 (токены)
COMPACT_THRESHOLD = int(os.environ.get("SESSION_COMPACT_TOKENS", "250000"))
OUTPUT_BUDGET = 4096           # резерв под ответ модели
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

BUFFER = int(os.environ.get("SESSION_BUFFER", "20000"))  # страховка ниже лимита
KEEP_TOKENS = int(os.environ.get("SESSION_KEEP_TOKENS", "15000"))  # дословный хвост рядом со сводкой
TAIL_FOR_POLISH = 5            # последних диктовок в контекст полировки

# Цены deepseek-v4-flash (USD за 1M токенов, август 2026; сверять с
# официальной страницей pricing). Вход разбит на cache-hit и cache-miss.
PRICING = {"in_miss": 0.14, "in_hit": 0.0028, "out": 0.28}

COMPACT_PROMPT = (
    "Ты сжимаешь историю голосовой диктовки/диалога в компактную сводку "
    "на русском (150–300 слов). Сохрани: о чём говорили, цель, важные "
    "факты и детали, имена и термины (как есть, включая англ. названия), "
    "числа, что уже сделано, что сейчас активно, блокеры, следующие шаги. "
    "Не добавляй нового и не пересказывай дословно. Верни ТОЛЬКО сводку."
)


def estimate_tokens(text):
    """Грубая оценка токенов: ~4 символа на токен (OpenCode-эвристика)."""
    return max(1, len(text) // 4)


class Session:
    """Сессия дня: messages + summary, персистентна в CACHE_DIR."""

    TITLE_MAX = 60  # символов в автоназвании сессии

    def __init__(self, session_id=None):
        self.session_id = session_id or time.strftime("%Y%m%d-%H%M%S")
        self.created = time.strftime("%Y-%m-%d %H:%M")
        self.title = None       # автоназвание из первой диктовки
        self.messages = []      # [{"role": "user"|"assistant", "content"}]
        self.summary = None
        self.stats = {"tokens_in": 0, "tokens_hit": 0, "tokens_out": 0}
        self._path = os.path.join(CACHE_DIR, f"{self.session_id}.json")

    # --- persist / resume ---
    def save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = {"id": self.session_id, "created": self.created,
                "title": self.title, "summary": self.summary,
                "messages": self.messages, "stats": self.stats}
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self._path)

    @classmethod
    def load(cls, session_id):
        path = os.path.join(CACHE_DIR, f"{session_id}.json")
        if not os.path.isfile(path):
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        s = cls(data.get("id", session_id))
        s.created = data.get("created", "?")
        s.title = data.get("title")
        s.summary = data.get("summary")
        s.messages = data.get("messages", [])
        s.stats = data.get("stats", {"tokens_in": 0, "tokens_hit": 0,
                                     "tokens_out": 0})
        return s

    @classmethod
    def _ids(cls):
        """Все id сессий (имя файла без .json), новые первыми."""
        if not os.path.isdir(CACHE_DIR):
            return []
        return sorted(
            (f[:-5] for f in os.listdir(CACHE_DIR) if f.endswith(".json")),
            reverse=True)

    @classmethod
    def load_latest(cls):
        """Последняя (по времени создания) сессия — автопродолжение."""
        ids = cls._ids()
        return cls.load(ids[0]) if ids else None

    @classmethod
    def list_sessions(cls, limit=10):
        """Список сессий: (id, created, сообщений, сводка) — новые первыми."""
        out = []
        for sid in cls._ids()[:limit]:
            s = cls.load(sid)
            if s is None:
                continue
            out.append((s.session_id, s.created, len(s.messages),
                        (s.summary or "")[:70], s.title))
        return out

    # --- рост истории ---
    @staticmethod
    def _title_from(content):
        """Название из первой диктовки (как OpenCode — из первого
        сообщения): первые ~60 символов, без мусорных слов в начале,
        обрезка по границе слова."""
        text = content.strip()
        for junk in ("ну ", "вот ", "так ", "это ", "короче "):
            if text.lower().startswith(junk):
                text = text[len(junk):]
                break
        if len(text) <= Session.TITLE_MAX:
            return text
        cut = text[:Session.TITLE_MAX]
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        return cut + "…"

    def add(self, role, content, kind=None):
        """kind — пометка сообщения: "polish" для результата полировки
        (правка распознанного текста), None — обычный ход (ответ модели).
        Пометка не обязательна и не ломает старые сессии."""
        if role == "user" and not self.title:
            self.title = self._title_from(content)
        msg = {"role": role, "content": content}
        if kind:
            msg["kind"] = kind
        self.messages.append(msg)
        self.save()

    def total_tokens(self):
        return estimate_tokens(
            (self.summary or "") + "".join(
                m["content"] for m in self.messages))

    # --- автокомпакт (паттерн OpenCode V2) ---
    def needs_compact(self):
        limit = min(CONTEXT_LIMIT, COMPACT_THRESHOLD)
        return self.total_tokens() > limit - max(OUTPUT_BUDGET, BUFFER)

    def compact(self, deepseek_ask):
        """Сжимает старые ходы в summary, хвост keep_tokens дословно.

        deepseek_ask — функция ask из deepseek_ai (передаётся, чтобы не
        импортировать по кругу: session -> deepseek_ai)."""
        if not self.messages:
            return False
        budget = KEEP_TOKENS * 4  # в символах
        tail, head, used = [], [], 0
        for m in reversed(self.messages):
            cost = len(m["content"]) + 4
            if tail and used + cost > budget:
                head.insert(0, m)
            else:
                tail.insert(0, m)
                used += cost
        transcript = "\n\n".join(f"{m['role'].upper()}: {m['content']}"
                                 for m in head)
        summary, err = deepseek_ask("", transcript, temperature=0.2,
                                    messages=None)
        if err or not summary:
            return False
        self.summary = summary.strip()
        self.messages = tail
        self.save()
        return True

    def undo(self):
        """Отменяет последний ход: удаляет последнее user-сообщение и всё,
        что после него (как /undo в OpenCode — без Git, для дневника)."""
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i]["role"] == "user":
                del self.messages[i:]
                self.save()
                return True
        return False

    # --- статистика использования (usage из ответа DeepSeek) ---
    def record_usage(self, usage):
        """Копит фактические токены из usage ответа API:
        prompt_cache_miss_tokens / prompt_cache_hit_tokens /
        completion_tokens."""
        if not usage:
            return
        self.stats["tokens_in"] += int(usage.get("prompt_cache_miss_tokens", 0))
        self.stats["tokens_hit"] += int(usage.get("prompt_cache_hit_tokens", 0))
        self.stats["tokens_out"] += int(usage.get("completion_tokens", 0))
        self.save()

    def cost(self):
        """Оценка стоимости сессии в USD по ценам deepseek-v4-flash."""
        s = self.stats
        return (s["tokens_in"] * PRICING["in_miss"]
                + s["tokens_hit"] * PRICING["in_hit"]
                + s["tokens_out"] * PRICING["out"]) / 1_000_000

    def _fmt_cost(self):
        """Стоимость с умным округлением: крупные $, мелкие — в центах."""
        c = self.cost()
        if c >= 0.01:
            return f"${c:.2f}"
        if c >= 0.0001:
            return f"${c:.4f}"
        return f"${c:.6f}"

    def context_str(self):
        """Как в OpenCode TUI: 'Tokens: 19.9K/1M (98% свободно)' + $."""
        used = self.total_tokens()
        pct = used * 100.0 / CONTEXT_LIMIT
        return (f"{used/1000:.1f}K/{CONTEXT_LIMIT/1_000_000:.0f}M "
                f"({100-pct:.1f}% свободно), в сессии: "
                f"{len(self.messages)} сообщ., ~{self._fmt_cost()} "
                f"(вход {self.stats['tokens_in']/1000:.1f}K + кэш "
                f"{self.stats['tokens_hit']/1000:.1f}K + выход "
                f"{self.stats['tokens_out']/1000:.1f}K)")

    # --- сборка контекста для запроса ---
    def build_context(self, tail_count=None):
        """messages для передачи в ask: сводка (system) + хвост истории.
        tail_count — ограничить число последних сообщений (для полировки)."""
        msgs = []
        if self.summary:
            msgs.append({"role": "system",
                         "content": f"[Сводка предыдущего контекста сессии]\n{self.summary}"})
        hist = self.messages
        if tail_count is not None and len(hist) > tail_count:
            hist = hist[-tail_count:]
        msgs += hist
        return msgs

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
