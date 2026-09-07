---
name: architecture-simplicity
description: "Спроектировать/перепроектировать модули и слои, выбор библиотеки vs свой код, god-file, схема БД без потери данных, ревью архитектуры. Не для денег (money-path-safety), харденинга (hardening-observability), рефакторинга (agent-refactor-safety)."
compatibility: любой язык и стек, этап проектирования/ревью архитектуры
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# Architecture & simplicity: проектные принципы

Дистилляция из боевых сессий. Первоисточник: `docs/patterns/GLAV-PATTERNS.md`, блоки C (21-30), K (71-90).

## 1. Простота и зависимость

- **YAGNI UNTIL SECOND NEED** — абстракция с одним потребителем = долг; inline до второго потребителя; слой удаляется — поведение то же, кода меньше
- **STD LIB FIRST** — новая зависимость дороже 30 строк своего кода; stdlib/native сначала, dep при измеримой боли (не moment.js ради одного format)
- **SEPARATE BY CHANGE REASON** — payments/access/generators/bot — разные оси изменений; фича PDF не трогает billing; НЕ god-file на 3000 строк
- **SHARED CORE, THIN ADAPTERS** — бизнес-логика одна; Telegram/CLI/desktop — оболочка (I/O + auth + UX); баг чинится в одном месте
- **ABSTRACTION PAYS RENT** — окупается сейчас, не «когда-нибудь»

## 2. Конфиг и эволюция

- **CONFIG OUTSIDE REPO** — секреты/ops-тюнинг не в git; безопасные default'ы в коде (FREE_MINUTES=30); override env; clone не утекает
- **SCHEMA WITHOUT DROP** — CREATE IF NOT EXISTS + ALTER ADD COLUMN ignore-if-exists; старый файл БД открывается новым кодом
- **FLAG > REWRITE** — ops-тюнинг через флаг/env
- **DETERMINISTIC REBUILD > STALE CACHE** — документы/артефакты пересобрать лучше, чем жить со старым кэшем
- **CACHE BY STABLE KEY** — дорогое (LLM) кэшировать по PK; дешёвое пересобирать; второй клик = 0 external calls

## 3. Паттерны кода

- **EXPLICIT SPEND ORDER** — списание (free→bonus→paid) — один алгоритм в одном месте; тест на каждую границу bucket'а
- **FALLBACK CHAIN** — ordered list провайдеров, next on timeout/5xx, fail когда все мертвы; mock: first down → second ok
- **MINI-PROTOCOL** — короткие префиксы + версионируемые поля > свободный JSON: `hl:page`, `ho:id:back`; regex router; back_context всегда с собой
- **PURE AT CORE** — сборка/экспорт — чистые функции; I/O на границах
- **ILLEGAL STATES UNREPRESENTABLE** — отдельные поля > boolean soup: `status: active|finished`
- **COMMENTS: WHY + CEILING** — почему и потолок (лимит/предположение), не «что делает»
- **DELETE DEAD CODE** — удалять, не комментировать навсегда
- **VERB NAMES** — charge_seconds, apply_referral, can_afford
- **YYYY-MM EXPLICIT** — ключи периодов — строки YYYY-MM
- **FLOAT MONEY IS EVIL** — деньги не float; минуты можно, если консистентно + тесты

## 4. Остальное из мета-принципов

- **FAIL CLOSED ON AUTH** — auth-отказ закрыт; fail open только для optional UX, с уведомлением
- **OBSERVABILITY IS A FEATURE** — лог/метрика с фичей в том же PR
- **TESTABLE OFFLINE** — доменная логика обязана тестироваться офлайн
- **PARTIAL FAILURE IS NORMAL** — рассылка: sent/failed счётчики, отчёт — не «всё или ничего»
- **BACK NAV STATE IS A FEATURE** — состояние возврата проектируется сразу
- **LAZIEST CORRECT FIX** — общий корень, не копипаст guard'ов
- **COPY IS PART OF QA** — копия проверяется
- **MONEY PATH TESTED** — зелёные тесты без денежного пути = ложная безопасность
- **PROD IS THE INTEGRATION** — smoke после деплоя/рестарта

## Workflow (порядок применения)

1) Границы модулей по причине изменений → 2) YAGNI-проверка абстракций → 3) зависимости (stdlib сначала) → 4) ядро/тонкие адаптеры → 5) секреты вне git, дефолты в коде → 6) схема эволюционирует без DROP (YYYY-MM) → 7) ключевые паттерны (списание в одном месте, fallback chain, невалидные состояния нерепрезентабельны, чистые функции) → 8) мёртвое удалено, комментарии WHY, имена-глаголы.

## Чеклист ревью архитектуры

- [ ] YAGNI: нет абстракций с одним потребителем
- [ ] зависимость оправдана (stdlib сначала)
- [ ] модули по причине изменений; бизнес-ядро одно, адаптеры тонкие
- [ ] секреты вне репо; дефолты в коде; схема без DROP
- [ ] списание в одной функции; fallback chain; состояния нерепрезентабельны
- [ ] мёртвый код удалён; комментарии WHY

## Этапы (handoff)

- **Вход из:** `nodumb` (дорогая развилка), `task-cycle` (фаза 3 — план)
- **Дальше:** `hardening-observability`, `agent-refactor-safety`, `code-review`

## References

- Первоисточник: `docs/patterns/GLAV-PATTERNS.md` — блоки C (21-30), K (71-90), ТОП-20
- Смежные: `money-path-safety`, `hardening-observability`, `agent-refactor-safety`

Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
