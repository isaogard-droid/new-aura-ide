#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Юнит-тесты меню «Действия» (chat.py после разбиения deepseek_menu).

Запуск (из корня проекта):
    ./venv/bin/python -m unittest discover -s tests -t .
"""
import unittest

from chat import _build_menu


class BuildMenuTest(unittest.TestCase):
    def test_full_menu_structure(self):
        menu = _build_menu("вкл", no_ai=False)
        text = "\n".join(menu)
        self.assertIn("Действия", text)
        self.assertIn("[0] Задачи", text)
        self.assertIn("[3] Экспорт", text)
        self.assertIn("[8] Сводка дня", text)
        self.assertIn("[9] Теги", text)
        self.assertIn("Подмешка(вкл)", text)
        self.assertIn("Сессии", text)
        # панель «без ИИ» не должна попасть в полный режим
        self.assertNotIn("Режим без ИИ", text)

    def test_no_ai_menu(self):
        menu = _build_menu("выкл", no_ai=True)
        text = "\n".join(menu)
        self.assertIn("Режим без ИИ (только запись)", text)
        # анализ/теги скрыты (они требуют DeepSeek)
        self.assertNotIn("[0] Задачи", text)
        self.assertNotIn("[8] Сводка дня", text)
        self.assertNotIn("[9] Теги", text)
        # публикация и сессии остаются
        self.assertIn("[3] Экспорт", text)
        self.assertIn("[s] Сессия", text)


if __name__ == "__main__":
    unittest.main()

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
