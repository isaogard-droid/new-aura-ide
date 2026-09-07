# skills.sh по максимуму: fallback-лестница, форматы, экосистема

Первоисточник: `../../docs/canon/skills.sh.md` (проверено живьём 17.08.2026).
Читать, когда CLI-скрипт недоступен, результат пуст, или нужны детали
каталога (URL-форматы, аудиты, экосистема).

## Порядок поиска (быстрый, без фейлов)

```text
1. python3 scripts/tools/skills/skills_search.py "<тема>" --top      # PRIMARY (~1с; retry ≤1)
2. python3 scripts/tools/skills/skills_search.py --read OWNER/REPO/SKILL  # SKILL.md как контекст
3. python3 scripts/tools/skills/skills_search.py --tree OWNER/REPO/SKILL  # состав (references/scripts)
4. SECONDARY — ОБЯЗАТЕЛЕН при exit 2 («⚠ НЕ СМОГ») ИЛИ «ничего не найдено»:
   КАМУФОКС-РЕСЁРЧ СКИЛЛОВ — web_search 3-5 запросов с разных сторон
   ("<тема> agent skill github", "site:skills.sh <тема>", "<тема> skills directory")
   → fetch_page первоисточников (raw GitHub SKILL.md, страницы skills.sh)
5. поле ввода browser_type(input, q)  # нестабильно, последний сетевой шаг
6. если всё пусто → экосистема: GitHub API search repositories
   ("<тема> skills agent"), SkillsMP, bibendi/agent-skills,
   JonesPitkin/sing-box-skills
7. DEGRADED: честное «не нашёл» + фиксация (HALT); ESCALATION: вопрос владельцу
```

## Сравнение способов (проверено живьём)

| Способ | Надёжность | Скорость | Примечание |
|---|---|---|---|
| API `/api/search?q=` | СТАБИЛЕН, 25+ рез. | ~2с | JSON, парсить `"id":"owner/repo/skill"` |
| поле ввода `browser_type("input")` | НЕСТАБИЛЕН: то 6, то 20 рез. | ~4-5с | лидерборд фильтруется с задержкой |
| `/search?q=` страница | пусто | — | не рендерит результаты |
| web_search site:skills.sh | почти пусто | ~3с | каталог не индексируется DDG |

## Форматы URL

| URL | Что даёт | Статус |
|---|---|---|
| `skills.sh/<owner>/<repo>` | страница репо: скиллы, установки, команда `npx skills add` | работает |
| `skills.sh/<owner>/<repo>/<skill>` | страница скилла: описание, установка, Security Audits, First Seen | работает, иногда таймаутит (45с) |
| `skills.sh/<owner>/<repo>/skills/<skill>` | то же | 404 — не использовать |
| `raw.githubusercontent.com/<owner>/<repo>/<branch>/<путь>` | ПОЛНЫЙ файл без JS (SKILL.md и любой reference/script) | лучший способ читать содержимое (уточнить ветку/путь через GitHub API tree) |

## Как читать содержимое скилла (по убыванию надёжности)

1. `python3 scripts/tools/skills/skills_search.py --tree OWNER/REPO/SKILL` —
   состав скилла (SKILL.md, references/, scripts/, assets/) через GitHub
   tree API (кэш 6ч, защита rate limit). У скилла-в-корне-репо
   (qwwiwi/skill-finder) — тоже работает.
2. `--read OWNER/REPO/SKILL` — SKILL.md; `--read OWNER/REPO/SKILL/<подпуть>`
   (например `references/proxy_conflict_reference.md`, `scripts/x.py`) —
   любой файл. raw GitHub (main, затем master), мгновенно, без JS.
3. Страница скилла на skills.sh — описание + метаданные (установки,
   аудиты), но текст SKILL.md может обрезаться («Show more»).
4. Страница таймаутит — повторный вызов часто проходит; не виснуть,
   сразу брать raw-вариант.

**Публичный skills.sh НЕ отдаёт состав файлов** (`/api/skills/.../files`
из mastra-ai/skills-api на www.skills.sh — 404, проверено 17.08.2026);
единственный надёжный путь к внутренностям — GitHub tree + raw.

## Security Audits на странице скилла

Каждый скилл имеет 3 аудита: **Gen Agent Trust Hub / Socket / Snyk**
(Pass / Warn / Fail). Скилл с Snyk Fail (пример: singbox-config
обрабатывает чужие подписки с кредами) — следовать осторожно, креды
не выводить.

## Экосистема (когда на skills.sh пусто)

- **bibendi/agent-skills** — sing-box-ubuntu-setup (split-routing через TUN);
- **JonesPitkin/sing-box-skills** — 10 скиллов sing-box (core/dns/routing/
  tun/outbounds/inbounds/rulesets/security/openwrt/troubleshooting),
  production, baseline v1.13.13;
- **SkillsMP** (skillsmp.com) — зеркало-каталог скиллов (vpn-deploy и др.);
- **GitHub API** — `api.github.com/search/repositories?q=<тема>+skills` —
  быстрый (~1.5с), JSON; НЕ github.com/search (SPA, таймаутит/пусто);
- raw GitHub — универсальный способ читать SKILL.md любого репо.

## Грабли (не наступать)

- поле ввода нестабильно: 1-й вызов может вернуть 6 из 20 результатов —
  повтор или API;
- `/search?q=` страница — пустой вывод, не тратить время;
- `/api/...` НЕ таймаутит (проверено 17.08: работает!) — основной способ;
- `/skills/` в URL скилла — 404;
- web_search по site:skills.sh — почти пусто (DDG не индексирует);
- github.com/search — SPA, пустой текст; использовать GitHub API;
- страницы скиллов иногда таймаутят 45с — повтор или raw GitHub;
- установка скиллов — только `npx skills add <owner/repo> --skill <имя>`
  с явного согласия владельца (чужой код = supply-chain риск: Snyk
  ToxicSkills — 13.4% скиллов из каталогов с проблемами).
