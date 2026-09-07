#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""chat.commands — slash-команды диалога (COMMANDS/SLASH/HELP_TEXT).
Вынесено из chat.py механически (verbatim), 15.08.2026 — гейт god-файлов.
Первоисточник правил: docs/canon/FILE-SIZE.md (механическая резка)."""


# Команды меню: как OpenCode/Claude Code — строго именованные slash-команды,
# список виден через ввод "/" (Tab-дополнение) и /help. Словесных алиасов
# нет (не индустриальный паттерн — подтверждено ресёрчем).
COMMANDS = {
    "/tasks":    ("0", "Извлечь задачи/дела из записи"),
    "/summary":  ("1", "Пересказ и ключевые мысли записи"),
    "/answer":   ("2", "Ответить с учётом контекста сессии"),
    "/export":   ("3", "Экспорт в MD/PDF (транскрипт + результаты)"),
    "/prompt":   ("4", "Кодинг-промпт: запись → ТЗ для агента"),
    "/mix":      ("5", "Подмешка — подпись, уходит отдельно в TG"),
    "/telegram": ("6", "Настройки Telegram"),
    "/history":  ("7", "Поиск по истории записей"),
    "/day":      ("8", "Сводка дня (рекап) — итоги за день"),
    "/tags":     ("9", "Теги записей"),
    "/session":  ("s", "Сессии: список / новая / компакт"),
    "/compact":  ("c", "Сжать контекст сессии (суммаризация старых ходов)"),
    "/clear":    ("n", "Очистить контекст — новая сессия (старая остаётся в /session)"),
    "/new":      ("n", "Новая сессия с чистым контекстом"),
    "/editor":   ("t", "Продвинутый ввод: пустые строки, подтверждение, $EDITOR"),
    "/vocab":    ("v", "Словарь терминов (как говоришь → как писать)"),
    "/reconfigure": ("e", "Заново пройти онбординг DeepSeek (ключ / пропустить)"),
    "/ai":       ("a", "DeepSeek: глобально вкл/выкл (выкл — без ИИ (только запись))"),
}
SLASH = {cmd: meta[0] for cmd, meta in COMMANDS.items()}
# Алиасы команд как в OpenCode/Claude Code (внутри slash-системы)
SLASH.update({
    "/help": "h",
    "/undo": "u", "/paste": "t", "/editor": "t", "/text": "t",
    "/new": "n", "/clear": "n",
    "/compact": "c",
    "/sessions": "s", "/resume": "s", "/continue": "s",
    "/exit": "q", "/quit": "q", "/q": "q",
    "/setup": "e", "/onboard": "e", "/reset": "e", "/reconfigure": "e",
    "/deepseek": "a", "/off": "a", "/llm": "a",
})


def _help_text():
    """Список команд с описаниями — как палитра OpenCode/Claude Code."""
    lines = ["  Команды (набери / и Tab — автодополнение; /help — список):"]
    for cmd, (_code, purpose) in COMMANDS.items():
        lines.append(f"    {cmd:<12} {purpose}")
    lines.append("    /help       показать этот список")
    lines.append("  Алиасы: /sessions=/resume=/continue · /exit=/quit=/q · "
                 "/undo=/paste=/text=/editor")
    return "\n".join(lines)


HELP_TEXT = _help_text()


# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
