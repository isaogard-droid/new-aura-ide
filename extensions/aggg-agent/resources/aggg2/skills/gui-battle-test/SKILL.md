---
name: gui-battle-test
description: "Батл-тест GUI кликами: «батл тест кнопок/состояний», «протестируй UI», «прогони панель как юзер». pywebview/evaluate_js, condition-based waiting, снимок/откат системы, отчёт «было X% → стало Y%». Не для юнит-тестов (testing-discipline) и веб-страниц."
compatibility: AGGG2.0; паттерны применимы к любому GUI (pywebview/GTK/Qt/Tk/нативные)
metadata:
  version: "1.0"
  author: AGGG2.0 (t.me/aidvizhenie, t.me/hilartem)
license: Proprietary
---

# GUI battle test: кнопки и состояния реальными действиями

Батл-тест UI = прогнать ВСЕ интерактивные элементы и состояния реальными действиями (клики/ввод через мост или accessibility), собрать цифры (X/Y, %), реверснуть отказы, починить, перезамерить. Обобщение боевого крещения 19.08 (vpn-gui: 145 шагов, 3 продуктовых бага).

## When to use / NOT use

**Use:** «батл тест кнопок», «протестируй интерфейс», «прогони как юзер», «стресс-тест UI», «все состояния панели», после правок UI — «докажи, что работает».

**NOT use:** юнит-тесты (testing-discipline), веб-страницы в браузере (Playwright MCP/browser-interaction), аудит UX (ask-nodumb), дебаг (debug-incident-protocol).

## Workflow (7 шагов)

1. **Инвентаризация UI.** Все элементы (кнопки, тумблеры, сегменты, диалоги, инпуты) и состояния (алерты, пусто, busy, ошибка, недоступно). Источник: HTML/JS, вьюхи, a11y-дерево.
2. **Гарнесс по типу:** webview → `scripts/tools/battle/gui_battle.py` (мост evaluate_js/exec_js; эталон vpn-gui tests/battle_ui.py); нативные → accessibility (Linux AT-SPI/pyautogui, macOS accessibility-API, Windows pywinauto/Windows-MCP); нет моста → скриншот-подход (GUISpector/Codex Computer Use): скриншот → клик по координатам → сверка.
3. **Привилегии ДО прогона** (рецепты ниже): `sudo -n true` (scoped NOPASSWD) и/или сухой pkexec.
4. **Снимок состояния ДО** (конфиги, сервисы, настройки, данные) → откат в finally (обязательно: гоняется даже при падении теста).
5. **Шаги = действие + условие (condition-based waiting).** Клик/ввод → поллинг УСЛОВИЯ (0.5-1с; deadline: 5с UI, 15-30с системные, 45с тяжёлые) — НЕ фиксированный sleep. Внешний цикл не блокирует: фоновый запуск + ожидание процесса, прогресс по хвосту лога.
6. **Реверс отказов.** С уликами: трассировка первых значений поллинга, тосты/ошибки СРАЗУ (тосты истекают), логи сервиса, состояние чекбоксов. Баг теста vs баг продукта — репро в изоляции-зонде.
7. **Перезамер до 100% + отчёт.** «Было X% → стало Y%», прогоны подряд, баги с причинами, состояние после = снимку. Вывод: CHANGELOG + research.db.

## Привилегии без пароля (автономность, scoped!)

ПРИНЦИП: никогда blanket NOPASSWD:ALL — только ТОЧНЫЙ список команд (ArchWiki polkit, linuxvox/ServerFault sudoers, Claude-breach least privilege).

**Linux — sudoers.d (scoped NOPASSWD):**
```
# /etc/sudoers.d/aggg2-autonomy — ТОЛЬКО нужные команды, БЕЗ ALL
<user> ALL=(ALL) NOPASSWD: /usr/bin/systemctl * sing-box, /usr/local/libexec/vpn-gui-config *, /usr/bin/journalctl -u sing-box *, /usr/bin/tee /usr/local/libexec/vpn-gui-config
```
Проверка: `visudo -c`, `sudo -n true`, целевая команда `sudo -n ...`. Откат: удалить файл. ГРАБЛЯ: пробелы в Command_Spec — экранировать; `*` в пути не работает — только в аргументах.

**Linux — polkit (для systemd-юнитов, тоньше sudo):**
```
// /etc/polkit-1/rules.d/50-aggg2.rules
polkit.addRule(function (action, subject) {
    if (!subject.isInGroup("wheel")) return polkit.Result.NOT_HANDLED;
    if (action.id === "org.freedesktop.systemd1.manage-units" &&
        action.lookup("unit") === "sing-box.service") return polkit.Result.YES;
    if (action.id === "org.freedesktop.policykit.exec" &&
        action.lookup("program") === "/usr/local/libexec/vpn-gui-config")
        return polkit.Result.YES;
    return polkit.Result.NOT_HANDLED;
});
```
Проверка: `pkexec <программа> <команда> </dev/null` (payload — в STDIN, не аргументом! argv проверяется полкитом). ГРАБЛЯ: правила перечитываются сразу (inotify), битый файл ломает polkitd — писать атомарно (mktemp+mv).

**macOS:** sudoers.d + tccutil для Accessibility (иначе клики молчат). **Windows:** UAC off не нужен — admin-сессия агента; скилл `cross-platform` (пути/кодировки/subprocess).

## Адаптивные ожидания (никаких слепых sleep)

- **Condition-based waiting (паттерн obra/superpowers, канон):** жди УСЛОВИЕ, не время; deadline = предел поллинга, шаг завершается как только условие истинно.
- **Поллинг с прогрессией:** 0.5-1с на UI; условие false 5+ итераций → интервал ×2 (до 5с); появился прогресс (тост/спиннер/лог) → сброс к 0.5с.
- **Внешние прогоны не блокируют:** фоновый запуск + ожидание завершения, прогресс по `tail -f`. Никаких `sleep 400` в оркестраторе.
- **Трассировка на отказе:** первые 3 РАЗНЫХ значения поллинга и ранние тосты (живут ~3с).

## Кроссплатформенные гарнессы

| Система | Дисплей | Драйвер кликов | Привилегии |
|---|---|---|---|
| Linux X11 | DISPLAY + Xvfb (`xvfb-run -a`) | evaluate_js / AT-SPI / pyautogui | sudoers.d scoped / polkit |
| Linux Wayland | XWayland: `GDK_BACKEND=x11` | то же | то же |
| macOS | реальная сессия (нет Xvfb) | accessibility / pyautogui / Computer Use | sudoers + tccutil |
| Windows | реальная сессия | pywinauto / Windows-MCP / PowerShell | admin-сессия |

Кодировки/пути/CRLF — `cross-platform` (обязателен при коде под Windows).

## Инструменты AGGG2.0

- `scripts/tools/battle/battle_core.py` — ядро gui/cli/api: поллинг с прогрессией, трассировка, откат в finally, отчёт X/Y.
- `scripts/tools/battle/gui_battle.py` — GUI-раннер: конфиг (launch, snapshot/restore, шаги «действие+условие+deadline»).
- Братья: `cli_battle.py` (exit/stdout/stderr, wait_retry, таймаут-убийца), `api_battle.py` (статус-коды, schema, POST) — карта в скилле `battle-test`.
- `mcp/gui_battle_mcp.py` — stdio MCP: `battle_run(surface=gui|cli|api)` (фон, сразу путь лога), `battle_status` (прогресс по логу). Паттерн: MCP = доступ, скилл = как пользоваться.

## Известные грабли (предупреди заранее — из боевого крещения 19.08)

1. **Кириллица в evaluate_js искажается (WebKitGTK)** — JS только ВОЗВРАЩАЕТ значения, сравнения на стороне Python.
2. **JS-инъекции до загрузки страницы мешают** — стартовая пауза 3-5с до первого evaluate_js.
3. **systemd start-rate-limit** после серии действий — `systemctl reset-failed <юнит>` перед start/restart.
4. **Чекбоксы рассинхронизируются** (10с-поллинги перезаписывают DOM) — не `.click()`, а `el.checked = target; el.dispatchEvent(new Event('change'))`.
5. **pkexec: payload в stdin, не в argv** — argv проверяет polkit-правило.
6. **Тосты истекают за ~3с** — трассируй рано, не в конце шага.
7. **Кнопки в display:none**: .click() в WebKitGTK может не сработать — клик по табу, показывающему панель, сначала.
8. **Скрытые panes ≠ мёртвые** — visible-состояние проверять в инвентаризации.
9. **Restore обязан отключать и юниты**, не только правила (иначе состояние утекает до перезагрузки).
10. **Раннер-отладка дешевле полного прогона**: зонд-репро (~1 мин) вместо полного батла (~4 мин) на гипотезу.
11. **Python 3.14 late-binds лямбды в компрехеншнах** — не строить `want`/каллбеки в list-comprehension, только явный цикл.
12. **Falsy в трассировке**: None/0/'' — легитимные значения поллинга, не «нет значения» (sentinel для исключений).

## Success criteria

- Пройдены ВСЕ шаги инвентаризации (или отказ объяснён: мусор источника ≠ наш баг); каждый отказ разобран: баг продукта (починен+CHANGELOG) или баг теста (починен+урок в скилл).
- 100% достижимых; прогоны подряд; состояние после == снимку ДО; цифры «было X% → стало Y%».

## Failure modes

- **Слепые sleep** — флаки; против: адаптивные ожидания.
- **Blanket NOPASSWD:ALL** — вектор атаки (Claude breach); против: scoped-список.
- **Ресторе без юнитов** — утечка опасного состояния (kill switch); против: полный откат.
- **Ретраи маскируют баг** («уже есть» от повторного клика); против: одна попытка на шаг + трассировка.
- **Тест чинит сам продукт**; против: реверс с уликами, зонд-изоляция.

## Этапы (handoff)

- **Вход из:** «батл тест», после правок UI, после battle-test фичи (CYCLE фаза 5а).
- **Дальше:** testing-discipline (юнит-покрытие багов), changelog-discipline, hardening-observability (дыры привилегий).

## References

- Ресёрч 19.08 (20+ источников): obra/superpowers condition-based-waiting, pywebview Test Execution, ArchWiki polkit, linuxvox/ServerFault sudoers, Functionize Adaptive Timing, Selenide, TestGuild 2026, GUISpector, Codex Computer Use QA, Windows-MCP, skills-mcp, Claude blog skills+MCP, Xvfb/XWayland, Claude-breach least privilege.
- Эталон: projects/vpn-gui/tests/battle_ui.py (145 шагов, 100%×4, 19.08).

Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
<!-- wm: aidvizhenie t.me · h-i-l-artem · t,me/aidvizh_hub -->
