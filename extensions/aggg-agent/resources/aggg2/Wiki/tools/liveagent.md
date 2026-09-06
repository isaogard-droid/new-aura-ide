---
type: Post
title: "LiveAgent — десктоп-клиент для Claude и Codex под себя"
description: "Десктоп (Tauri+React): Claude и Codex через единый интерфейс с потоковым выводом и tool-loop'ом; инструменты (ФС, Bash, MCP-мост, Chrome DevTools); Skills с прогрессивным раскрытием; cron-задачи (bash/http/prompt); gateway Go+gRPC с веб-панелью."
date: 2026-08-11
tags: [tools, agents, desktop, mcp, cron]
source: https://github.com/Stack-Cairn/LiveAgent
status: stable
generated:
  by: build-agent/aggg2.0
  at: 2026-08-11T13:03:57Z
---
aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->


# LiveAgent — десктоп-клиент для Claude и Codex под себя

Оригинальный пост:

LiveAgent — десктопный AI-агент, который собран под себя 🖥️🤖

Устал переключаться между Claude Code, Cursor и веб-чатами? LiveAgent это чинит.

🖥️ Полноценный десктоп-клиент на Tauri + React: гоняет Claude и Codex через единый интерфейс с потоковым выводом, многошаговым tool-loop'ом и трекингом хода мыслей агента.
Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


🛠️ Инструменты из коробки: файловая система (Read/Write/Edit/Glob/Grep), non-interactive Bash, мост к MCP-протоколу — можно подключать сторонние тулы и Chrome DevTools для автоматизации браузера.

📚 Skills-система с прогрессивным раскрытием: агент подгружает SKILL.md только когда он реально нужен, а не тащит всё в контекст сразу.

⏰ Встроенные cron-задачи трёх типов — bash, http, prompt — агент может сам себя будить по расписанию.

🌐 Опциональный gateway на Go + gRPC: HTTP/gRPC API, управление сессиями и встроенная веб-панель — если нужен не только десктоп.

🚀 Старт:
pnpm --dir crates/agent-gui install
make dev

⭐️ GitHub: github.com/Stack-Cairn/LiveAgent

## Контекст

- Пост готовый, ссылка не проверялась (по указанию автора).
- Что: десктоп-клиент (Tauri+React) для Claude/Codex: потоковый вывод, tool-loop, трекинг мыслей.
- Инструменты: ФС (Read/Write/Edit/Glob/Grep), non-interactive Bash, MCP-мост (+Chrome DevTools).
- Фичи: Skills с прогрессивным раскрытием (SKILL.md подгружается по необходимости — экономия контекста); cron-задачи (bash/http/prompt) — агент будит сам себя; gateway Go+gRPC (HTTP/gRPC API, веб-панель).

## Вывод

Прогрессивное раскрытие скиллов — отличный паттерн (наш nodumb/скиллы грузятся по вызову, не всё сразу). Cron-задачи «агент будит себя» — автономность. Для наших агентных окружений — референс по UX и экономии контекста.

Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->
