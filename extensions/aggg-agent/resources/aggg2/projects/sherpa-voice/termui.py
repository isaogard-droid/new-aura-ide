#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Единый визуальный стиль терминала (паттерны индустрии).

OpenCode TUI: блоки-секции, статус-строка (модель · токены · сессия),
тонкие разделители. PatternFly CLI Handbook (Red Hat): смысл НЕ только
цветом — рядом текст-метка (OK/WARN/ERR); структура через заголовки,
буллеты, разделители; без стен текста.

Функции:
    rule(title)      — разделитель с подписью: ─── Транскрипт ───
    panel(title, body) — секция-блок: заголовок + отступ тела
    status(...)      — статус-строка: [модель · токены · $]
    ok/warn/err/info — метки с цветом И текстом: [✓ OK] / [! WARN] / [✗ ERR]
"""
# ANSI-цвета (темы как в OpenCode TUI)
C_OK, C_WARN, C_ERR, C_INFO, C_BLUE, C_DIM, C_RST = (
    "\033[32m", "\033[33m", "\033[31m", "\033[36m", "\033[34m",
    "\033[2m", "\033[0m")

# Ширина разделителя — по ширине терминала, но не бесконечная
_MAX_RULE = 72


def _term_width():
    try:
        import shutil
        return shutil.get_terminal_size().columns or 80
    except Exception:
        return 80


def rule(title="", ch="─"):
    """Разделитель с подписью по центру: ─── Заголовок ───────────.
    Возвращает строку (для join); печатать — print(rule(...))."""
    width = min(_term_width() - 2, _MAX_RULE)
    if not title:
        return C_DIM + ch * width + C_RST
    title = f" {title} "
    side = (width - len(title)) // 2
    return (C_DIM + ch * max(side, 1) + title
            + ch * max(width - side - len(title), 1) + C_RST)

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


def panel(title, body="", dim=False):
    """Секция-блок: заголовок + тело с отступом.
    dim=True — служебный заголовок приглушённым цветом (паттерн OpenCode:
    служебное не орёт, акцент на контенте). Эмодзи в меню-заголовках не
    используются (clutter audit: иконки = шум; см. CHANGELOG).
    Возвращает строку (для join); печатать — print(panel(...))."""
    head = C_DIM + f"▌ {title}" + C_RST if dim else C_BLUE + f"▌ {title}" + C_RST
    lines = [head]
    if body:
        for line in str(body).splitlines():
            lines.append(f"  {line}")
    return "\n".join(lines)


def ok(text):
    """Успех: цвет + текстовая метка (доступно без цвета)."""
    return f"{C_OK}[✓ OK] {text}{C_RST}"


def warn(text):
    """Предупреждение: цвет + метка."""
    return f"{C_WARN}[! WARN] {text}{C_RST}"


def err(text):
    """Ошибка: цвет + метка."""
    return f"{C_ERR}[✗ ERR] {text}{C_RST}"


def info(text):
    """Информация: цвет + метка."""
    return f"{C_INFO}[i INFO] {text}{C_RST}"


def step(prefix, text):
    """Шаг прогресса: [ai] Улучшаю текст… — единый стиль."""
    return f"{C_BLUE}[{prefix}]{C_RST} {text}"


def status(model, provider, context, cost=""):
    """Статус-строка как в OpenCode TUI: модель · провайдер · контекст · $."""
    parts = [p for p in (model, provider, context, cost) if p]
    return C_DIM + " · ".join(parts) + C_RST


def fmt_result(kind, text):
    """Готовый результат в блок: разделитель + панель + разделитель."""
    lines = ["\n"]
    lines.append(C_DIM + "─" * min(_term_width() - 2, _MAX_RULE) + C_RST)
    lines.append(f"{C_BLUE}▌ {kind}{C_RST}")
    for line in str(text).rstrip().splitlines():
        lines.append(f"  {line}")
    lines.append(C_DIM + "─" * min(_term_width() - 2, _MAX_RULE) + C_RST)
    return "\n".join(lines)

# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
