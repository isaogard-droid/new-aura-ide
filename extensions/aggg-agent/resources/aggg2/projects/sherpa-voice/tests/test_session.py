import os

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
import tempfile
import unittest

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


os.environ.setdefault("SESSION_COMPACT_TOKENS", "10000")
os.environ.setdefault("SESSION_KEEP_TOKENS", "100")
os.environ.setdefault("SESSION_BUFFER", "50")
import session  # noqa: E402


class FakeAsk:
    """Мок deepseek_ai.ask: возвращает фиксированную сводку."""
    def __call__(self, system, user_text, key=None, model=None,
                 temperature=0.3, retries=3, retry_delay=2.0, messages=None):
        return "СВОДКА: о микрофоне и распознавании. Цель — чистая запись. Сделано: настроен npr. Дальше: тесты.", None


class TestSession(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old = session.CACHE_DIR
        session.CACHE_DIR = self._tmp.name

    def tearDown(self):
        session.CACHE_DIR = self._old
        self._tmp.cleanup()

    def test_add_save_load(self):
        s = session.Session("test-1")
        s.add("user", "привет")
        s.add("assistant", "и тебе")
        loaded = session.Session.load("test-1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.messages, [
            {"role": "user", "content": "привет"},
            {"role": "assistant", "content": "и тебе"},
        ])

    def test_load_today(self):
        # автоподхват последней сессии (по времени создания)
        session.Session("20260101-000000").save()
        session.Session("20260101-111111").save()
        latest = session.Session.load_latest()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.session_id, "20260101-111111")

    def test_estimate_tokens(self):
        self.assertGreaterEqual(session.estimate_tokens("abcd"), 1)
        self.assertEqual(session.estimate_tokens("x" * 40), 10)

    def test_build_context(self):
        s = session.Session("ctx")
        for i in range(8):
            s.add("user", f"диктовка {i}")
            s.add("assistant", f"ответ {i}")
        ctx = s.build_context(tail_count=3)
        self.assertEqual(len(ctx), 3)
        self.assertEqual(ctx[-1]["content"], "ответ 7")
        s.summary = "краткая сводка"
        ctx2 = s.build_context(tail_count=3)
        self.assertEqual(ctx2[0]["role"], "system")
        self.assertIn("краткая сводка", ctx2[0]["content"])

    def test_compact(self):
        s = session.Session("cmp")
        # много сообщений, чтобы превысить порог 1000 токенов (~4000 симв)
        for _ in range(200):
            s.add("user", "длинная диктовка " + "x" * 120)
            s.add("assistant", "длинный ответ " + "y" * 120)
        self.assertTrue(s.needs_compact())
        ok = s.compact(FakeAsk())
        self.assertTrue(ok)
        self.assertIsNotNone(s.summary)
        self.assertIn("СВОДКА", s.summary)
        # после компакта хвост сохранился дословно
        self.assertTrue(s.messages)
        self.assertEqual(s.messages[-1]["content"].startswith("длинный ответ"), True)
        # повторный компакт не нужен
        self.assertFalse(s.needs_compact())

    def test_compact_empty(self):
        s = session.Session("empty")
        self.assertFalse(s.compact(FakeAsk()))


    def test_load_latest_and_list(self):
        session.Session("20260101-000001").save()
        session.Session("20260101-000002").save()
        s = session.Session("20260101-000003")
        s.add("user", "первая диктовка")
        s.summary = "про микрофон"
        s.save()
        latest = session.Session.load_latest()
        self.assertEqual(latest.session_id, "20260101-000003")
        lst = session.Session.list_sessions(10)
        self.assertEqual(lst[0][0], "20260101-000003")
        self.assertEqual(lst[0][1:3], (s.created, 1))
        self.assertIn("микрофон", lst[0][3])

    def test_usage_and_cost(self):
        s = session.Session("usage")
        s.record_usage({"prompt_cache_miss_tokens": 100_000,
                        "prompt_cache_hit_tokens": 900_000,
                        "completion_tokens": 10_000})
        self.assertEqual(s.stats["tokens_in"], 100_000)
        self.assertEqual(s.stats["tokens_hit"], 900_000)
        # $ = 100k*0.14 + 900k*0.0028 + 10k*0.28 / 1M
        expected = (100_000 * 0.14 + 900_000 * 0.0028 + 10_000 * 0.28) / 1e6
        self.assertAlmostEqual(s.cost(), expected, places=6)
        ctx = s.context_str()
        self.assertIn("1M", ctx)
        self.assertIn("$", ctx)

    def test_title_auto(self):
        s = session.Session("title")
        s.add("user", "ну вот мы настраивали микрофон и пресет EasyEffects")
        self.assertTrue(s.title)
        self.assertFalse(s.title.startswith("ну "))
        loaded = session.Session.load("title")
        self.assertEqual(loaded.title, s.title)
        # длинная диктовка — обрезка по границе слова
        s2 = session.Session("title2")
        s2.add("user", "очень длинная диктовка " + "слово " * 30)
        self.assertLessEqual(len(s2.title), session.Session.TITLE_MAX + 1)
        self.assertTrue(s2.title.endswith("…") or " " not in s2.title[-2:])

    def test_undo(self):
        s = session.Session("undo-t")
        s.add("user", "первая диктовка")
        s.add("assistant", "ответ 1")
        s.add("user", "вторая диктовка")
        s.add("assistant", "ответ 2")
        self.assertTrue(s.undo())  # убирает «вторую диктовку» и всё после
        self.assertEqual([m["content"] for m in s.messages],
                         ["первая диктовка", "ответ 1"])
        self.assertTrue(s.undo())  # отменяет и первый ход
        self.assertEqual(s.messages, [])
        self.assertFalse(s.undo())  # пусто — отменять нечего

if __name__ == "__main__":
    unittest.main()

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
