# docs/ — документация воркспейса

Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

Карта каталога (per-directory README — SSOT слоя, паттерн индустрии
docs-as-code). Правило: новый док кладётся в свою секцию; не в свою —
переместить прежде коммита.

| Каталог | Что внутри | Правила |
|---|---|---|
| `canon/` | доки обязательных скиллов: NODUMB, ASK-NODUMB, CHANGELOG-DISCIPLINE, SYSTEM-FEEDBACK, FABLE-METHOD/LOOP/JUDGE/DOMAIN, MULTIMODEL-JUDGE, ORCHESTRATION | канон-доки скиллов; ссылаются из AGENTS.md/core.txt; правки → doc-eval (пороги recall ≥0.8) |
| `research/` | отчёты глубокого ресёрча `<дата>-<тема>.md` + README-шаблон | шаблон и правила — `research/README.md`; вывод — в research.db с `--source` |
| `patterns/` | библиотека паттернов (GLAV-PATTERNS, UNIVERSAL-PATTERNS, `glav/`) | см. `patterns/README.md` |
| `eval/` | выхлоп eval-прогонов (JSONL) | генерится скриптами `scripts/eval/*`; в git не входит |

Корневые канон-доки (AGENTS.md, CLAUDE.md, CYCLE.md, docs/canon/CAMOUFOX.md,
docs/canon/DB-FIRST.md, docs/canon/AGENT-LSP.md, docs/canon/CODE-GRAPH.md, docs/canon/SETUP.md, docs/canon/FILE-SIZE.md) —
в корне, читаются агентами с корня (Tier A/B).
