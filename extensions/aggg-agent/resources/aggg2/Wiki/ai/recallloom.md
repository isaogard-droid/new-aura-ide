---
type: Post
title: "RecallLoom — файловая память проекта для агентов (.recallloom/)"
description: "Память проекта в markdown/json рядом с кодом — без БД и векторного поиска: контекст, решения, следующий шаг; работает поверх Codex, Claude Code, Gemini CLI, Copilot; сверяет сохранённое с git/деревом/тестами; local-first, запись только с подтверждением."
date: 2026-08-11
tags: [ai, agents, memory, files, context]
source: https://github.com/Frappucc1no/recall-loom
status: stable
generated:
  by: build-agent/aggg2.0
  at: 2026-08-11T13:03:57Z
---
Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: t,me/aidvizhenie · hilartem · aidvizh_hub -->


# RecallLoom — файловая память проекта для агентов (.recallloom/)

Оригинальный пост:

RecallLoom — файловая память проекта для агентов между сессиями 🧠📁

📂 Хранит контекст, ключевые решения и следующий шаг в обычных markdown/json-файлах рядом с кодом (.recallloom/) — без БД, векторного поиска или фонового сервиса.

🔄 Работает поверх Codex, Claude Code, Gemini CLI, GitHub Copilot и любого агента, читающего файлы проекта — модель или тул можно сменить, память остаётся с проектом.

✅ Перед возобновлением сверяет сохранённое состояние с реальностью: git-статусом, рабочим деревом и тестами — устаревшая сводка не важнее актуального кода.

🔒 Local-first: файлы остаются в воркспейсе, ничего не грузится в облако; запись происходит только с явным подтверждением, а не автоматически.

🚀 Установка:

npx skills add https://github.com/Frappucc1no/recall-loom --skill recallloom

🔓 Open source, Python 3.10+

🔗 GitHub: github.com
🌐 Сайт: recallloom.error9pm.com/en

## Контекст

- Пост готовый, ссылки не проверялись (по указанию автора).
- Что: память проекта в обычных markdown/json рядом с кодом (.recallloom/) — без БД/векторного поиска/фонового сервиса; агент-агностик (Codex, Claude Code, Gemini CLI, Copilot).
- Ключевое: сверка сохранённого состояния с реальностью (git, дерево, тесты) — «устаревшая сводка не важнее актуального кода»; local-first; запись только с явным подтверждением.
- Установка: npx skills add; Python 3.10+.

## Вывод

Девятое решение «памяти проекта» (Memora, Continuum, TencentDB, Flowix, Obelisk, Greplica, Cognee, RecallLoom + наш research.db). Отличия: файлы как память (как PROJECT_STATUS.md — привычка из нашей библиотеки), сверка с реальностью перед возобновлением, подтверждение записи. KISS-подход: без БД и сервисов.

Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: h-i-l-artem · t,me/aidvizh_hub · aidvizhenie -->
