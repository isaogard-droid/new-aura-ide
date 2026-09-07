// AGGG2.0-прошивка: механическая инъекция ядра правил в системный промпт +
// сторож запретов + nudge-гейты «база первым / ресёрч первым».
// Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
// AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

// Хуки (доки opencode + типы @opencode-ai/plugin; v2: PluginModule =
// {server: Plugin}, хуки tool.execute.before {tool, sessionID, callID}):
// - experimental.chat.system.transform — ядро правил в каждый ход;
// - experimental.session.compacting — ядро переживает компакцию контекста;
// - tool.execute.before — сторож: блок опасных Bash (throw Error), QA/CHANGELOG-
//   напоминания на правках кода, nudge-гейты «база первым / ресёрч первым»
//   (log warn один раз за сессию; не deny — nudge сильнее промпта, мягче запрета).
// core.txt кладётся рядом install_proshivka.py (источник: AGGG2.0/harness/core.txt).
import { existsSync, readFileSync, readdirSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"
import * as Pkg from "@opencode-ai/plugin"

const HERE = dirname(fileURLToPath(import.meta.url))
const CORE_PATH = join(HERE, "core.txt")
const MARK = "AGGG2.0-прошивка"

// Блок-правила Bash — синхронизировать с harness/hooks/aggg2_prompt_hook.py
// (осознанный дубль: разные рантаймы, 5 правил, меняются редко).
const BLOCK_RULES = [
  [/pkill\s+(-[a-zA-Z]+\s+)*-f\s+"?[^\["]/, "pkill -f без скобочного трюка убьёт сам bash. Используй pkill -f \"[х]...\""],
  [/rm\s+-[a-z]*r[a-z]*f?\s+\/\*?(\s|$)/, "rm -rf корня — необратимо. Подтверди у пользователя, покажи цель."],
  [/rm\s+-[a-z]*r[a-z]*f?\s+~(\s|$)/, "rm -rf дома — необратимо. Подтверди у пользователя, покажи цель."],
  [/rm\s+-[a-z]*r[a-z]*f?\s+\.\.?\/?(\s|$)/, "rm -rf текущего каталога — необратимо. Подтверди у пользователя."],
  [/git\s+reset\s+--hard/, "git reset --hard уничтожает незакоммиченное. Используй git stash/rebase."],
]

// Nudge-гейты (паттерн индустрии: runtime policy enforcement, PreToolUse
// deny-gate; у нас — nudge: напоминание без блокировки, один раз за сессию).
// Состояние по сессиям — в памяти процесса (serve); после рестарта — заново.
const DB_TOOLS = /^db-?tools[_-]|^(repo_map|search_all|agent-lsp|agent_lsp)[_-]/  // MCP db-tools/repo_map/search_all/agent-lsp
const SKILL_BASH = /db\/skills\.db|skills\.db|search\.py.*-b|skills_search\.py/
const DEBUG_BASH = /journalctl|systemctl|dmesg|\.log|gdb|strace/
const SKILL_TOOLS = new Set(["Skill", "skill"])
const WEB_TOOLS = new Set(["web_search", "fetch_page", "batch_fetch",
                           "browser_navigate", "extract_links", "browser_type"])
const READ_TOOLS = new Set(["read", "grep", "glob"])
const EDIT_TOOLS = new Set(["write", "edit", "patch", "apply_patch"])
const DB_BASH = /(findings\.py|search\.py|build\.py|githist\.py|tasks\.py)/
const SMB_TOOLS = new Set(["semble", "semble.search", "semble_search",
                           "semble.find_related", "semble_find_related"])
const stateBySession = new Map()

function sessionState(sid) {
  const id = sid || "default"
  if (!stateBySession.has(id)) {
    stateBySession.set(id, { dbTouched: false, webTouched: false,
                             skillsTouched: false, warnedDb: false,
                             warnedWeb: false, warnedWebLow: false,
                             warnedSkills: false, warnedSkillsFallback: false,
                             webCount: 0, sembleTouched: false,
                             warnedSemble: false, pending: "" })
  }
  return stateBySession.get(id)
}

function core() {
  try {
    return readFileSync(CORE_PATH, "utf8").trim()
  } catch {
    return ""
  }
}

function alreadyIn(list) {
  return list.some((s) => typeof s === "string" && s.includes(MARK))
}

export const AgGG2Proshivka = async ({ client } = {}) => {
  const RESUME_NOTE = 'ПРОДОЛЖЕНИЕ ПОСЛЕ КОМПАКЦИИ: контекст был сжат — это НЕ конец задачи. Сверься с research.db (findings.py search checkpoint), продолжай по плану, не дублируй сделанное.'
  return {
    "experimental.chat.system.transform": async (_input, output) => {
      if (!output || !Array.isArray(output.system)) return
      const text = core()
      if (text && !alreadyIn(output.system)) output.system.push(text)
    },
    "experimental.session.compacting": async (_input, output) => {
      const text = core()
      if (text && output && Array.isArray(output.context) && !alreadyIn(output.context)) {
        output.context.push(text)
        output.context.push(RESUME_NOTE)
      }
    },
    "tool.execute.before": async (input, output) => {
      const DOC_PATTERNS = ["AGENTS.md", "CLAUDE.md", "CYCLE.md", "docs/canon/CAMOUFOX.md", "docs/canon/DB-FIRST.md", "docs/canon/AGENT-LSP.md", "docs/canon/CODE-GRAPH.md", "docs/canon/SETUP.md", "CHANGELOG/", "harness/", "db-tools/", "scripts/", "VERSION"]
      const tool = input?.tool || ""
      const st = sessionState(input?.sessionID)

      // Следы использования базы / веб-ресёрча — маркируем сессию.
      if (DB_TOOLS.test(tool)) {
        st.dbTouched = true
      }
      if (SMB_TOOLS.has(tool) || /semble/i.test(tool)) {
        st.sembleTouched = true
      }
      if (WEB_TOOLS.has(tool)) {
        st.webTouched = true
        st.webCount += 1
      }
      if (SKILL_TOOLS.has(tool) || SKILL_BASH.test(String(output?.args?.command || ""))) {
        st.skillsTouched = true
        // skills_search.py — быстрый ресёрч чужих скиллов: маркируем
        // и «ресёрч был» (гейт «ресёрч-первым» не ругается после него)
        if (SKILL_BASH.test(String(output?.args?.command || ""))) {
          st.webTouched = true
          st.webCount += 1
        }
      }
      // Дебаг/инцидент (журнал/логи) без поиска скиллов — nudge
      // «скиллы-первым» (грабля 17.08: инцидент чинился без скиллов)
      if (DEBUG_BASH.test(String(output?.args?.command || ""))
          && !st.skillsTouched && !st.warnedSkills) {
        st.warnedSkills = true
        client?.app?.log("warn", "AGGG2.0-nudge «скиллы-первым»: дебаг/инцидент — СНАЧАЛА чужие скиллы по симптому: python3 scripts/tools/skills/skills_search.py \"<симптом>\" (debugging/systemd/incident-скиллы, ~1с), потом факты/лог (qa-debugging: Search The Validated Corpus First)")
        return { monologue: "AGGG2.0-nudge «скиллы-первым»: дебаг/инцидент — СНАЧАЛА чужие скиллы по симптому: python3 scripts/tools/skills/skills_search.py \"<симптом>\" (debugging/systemd/incident-скиллы, ~1с), потом факты/лог (qa-debugging: Search The Validated Corpus First)" }
      }

      if (tool === "bash") {
        const cmd = output?.args?.command
        if (typeof cmd !== "string" || !cmd) return
        for (const [re, reason] of BLOCK_RULES) {
          if (re.test(cmd)) {
            throw new Error(`AGGG2.0-сторож: БЛОК — ${reason}`)
          }
        }
        if (DB_BASH.test(cmd)) {
          st.dbTouched = true
        }
        if (/rm\s+-[a-z]*r/.test(cmd) || cmd.includes("git push --force")) {
          client?.app?.log("warn", `AGGG2.0-сторож: ${cmd.slice(0, 60)} — необратимая команда, покажи цель пользователю`)
          return { monologue: "AGGG2.0-сторож: необратимая команда — убедись, что цель показана пользователю." }
        } else if (/pkill/.test(cmd) && !/-f\s+"?\[/.test(cmd)) {
          client?.app?.log("warn", 'AGGG2.0-сторож: pkill — всегда скобочный трюк pkill -f "[х]..."')
          return { monologue: 'AGGG2.0-сторож: pkill — всегда скобочный трюк pkill -f "[х]..."' }
        } else if (/^(grep|find|cat|ls)\s/.test(cmd) && !st.dbTouched && !st.warnedDb) {
          st.warnedDb = true
          // Nudge в КОНТЕКСТ модели (monologue), не только в лог сервера —
          // иначе агент его не видит (аудит 17.08.2026, research.db id=792).
          return { monologue: "AGGG2.0-гейт: вопрос про содержимое воркспейса — СНАЧАЛА база (search.py --symbol/поиск / MCP db-tools / findings.py), потом греп/чтение (DB-FIRST). База не проиндексирована? python3 db-tools/build.py" }
        }
        return
      }
      if (READ_TOOLS.has(tool) && !st.dbTouched && !st.warnedDb) {
        st.warnedDb = true
        // Nudge в КОНТЕКСТ модели (monologue) — лог сервера модель не видит
        // (аудит 17.08.2026, research.db id=792: гейт был невидим агенту).
        return { monologue: "AGGG2.0-гейт: чтение файлов ДО базы — СНАЧАЛА индекс: search.py / MCP db-tools (search, symbol, calls) / findings.py; карта первой: repomap.py project (или MCP repo_map); «мы это уже разбирали» дешевле через базу (DB-FIRST)." }
      }
      // Nudge «лестница поиска»: греп/чтение после базы, но ДО semble —
      // смысловой вопрос про код должен идти через semble.search.
      if (READ_TOOLS.has(tool) && st.dbTouched && !st.sembleTouched && !st.warnedSemble) {
        st.warnedSemble = true
        return { monologue: "AGGG2.0-гейт «лестница поиска»: смысловой вопрос про код — СНАЧАЛА MCP semble.search (запрос ТЕРМИНАМИ дока, не бытовым пересказом; батл 19.08: термины 23/23, перефразы 0-1/10), потом db-tools (структура) → agent-lsp (символы). Точное имя символа — сразу agent-lsp; keyword — db-tools FTS, не semble (docs/canon/SEMBLE.md, скилл code-search-ladder)." }
      }
      // Nudge «скиллы-первым»: веб-ресёрч ДО поиска локального скилла
      // (db/skills.db). Мягкое напоминание, веб-вызов не блокируем.
      if (WEB_TOOLS.has(tool) && !st.skillsTouched && !st.warnedSkills) {
        st.warnedSkills = true
        client?.app?.log("warn", "AGGG2.0-nudge «скиллы-первым»: идёшь в веб/дебаг — СНАЧАЛА локальный скилл: python3 db-tools/search.py -b db/skills.db <тема> (или MCP search db=skills). Локальных нет — внешние через skills_search.py (100+ скиллов skills.sh за ~1с, --top по установкам, --read OWNER/REPO/SKILL читает SKILL.md как контекст). ДАЖЕ ДЛЯ ДЕБАГА/ИНЦИДЕНТА: сначала чужие скиллы (skills_search.py \"<симптом>\" — debugging/systemd-скиллы), потом факты/лог (qa-debugging: Search The Validated Corpus First). Верни НЕСКОЛЬКО подходящих (3-5+, лучше больше). Нашёл — ЗАГРУЗИ И СЛЕДУЙ; пусто — зафиксируй и иди в веб (docs/canon/SKILLS-LOCAL.md, docs/canon/skills.sh.md)")
        return { monologue: "AGGG2.0-nudge «скиллы-первым»: идёшь в веб/дебаг — СНАЧАЛА локальный скилл: python3 db-tools/search.py -b db/skills.db <тема> (или MCP search db=skills). Локальных нет — внешние через skills_search.py (100+ скиллов skills.sh за ~1с, --top по установкам, --read OWNER/REPO/SKILL читает SKILL.md как контекст). ДАЖЕ ДЛЯ ДЕБАГА/ИНЦИДЕНТА: сначала чужие скиллы (skills_search.py \"<симптом>\" — debugging/systemd-скиллы), потом факты/лог (qa-debugging: Search The Validated Corpus First). Верни НЕСКОЛЬКО подходящих (3-5+, лучше больше). Нашёл — ЗАГРУЗИ И СЛЕДУЙ; пусто — зафиксируй и иди в веб (docs/canon/SKILLS-LOCAL.md, docs/canon/skills.sh.md)" }
      }
      // Гейт «ресёрч-первым»: 0 источников — жёсткое напоминание с
      // нормативом; < 10 — вторая волна «мало источников» (без спама).
      if (EDIT_TOOLS.has(tool)) {
        if (!st.webTouched && !st.warnedWeb) {
          st.warnedWeb = true
          client?.app?.log("warn", "AGGG2.0-гейт: правка кода ДО веб-ресёрча — для задач с выбором/неизвестностью СНАЧАЛА Camoufox (web_search): МИНИМУМ 10 источников на любую задачу (справка/факт — 10, решения/выборы — 30-50, docs/canon/CAMOUFOX.md). «Подумал» без поиска = догадка")
          return { monologue: "AGGG2.0-гейт: правка кода ДО веб-ресёрча — для задач с выбором/неизвестностью СНАЧАЛА Camoufox (web_search): МИНИМУМ 10 источников на любую задачу (справка/факт — 10, решения/выборы — 30-50, docs/canon/CAMOUFOX.md). «Подумал» без поиска = догадка" }
        }
        if (st.webTouched && st.webCount < 10 && !st.warnedWebLow) {
          st.warnedWebLow = true
          client?.app?.log("warn", `AGGG2.0-гейт: маловато источников (${st.webCount} < 10) для правки — добери до норматива: web_search/fetch_page/batch_fetch (docs/canon/CAMOUFOX.md)`)
          return { monologue: `AGGG2.0-гейт: маловато источников (${st.webCount} < 10) для правки — добери до норматива: web_search/fetch_page/batch_fetch (docs/canon/CAMOUFOX.md)` }
        }
        const target = String(input?.filePath || input?.path || "")
        if (target && /\.(md|py|js|ts|sh|go|rs|java|c|cpp|css|html|toml)$/i.test(target)) {
          // Гейт god-файлов (зеркало scripts/tools/audit/check_file_sizes.py LIMITS):
          // файл выше hard — только в сторону резки, не расти (docs/canon/FILE-SIZE.md).
          try {
            if (existsSync(target)) {
              const lines = readFileSync(target, "utf8").split("\n").length
              const hard = /\.md$/i.test(target) ? 500 : 1000
              if (lines >= hard) {
                client?.app?.log("warn", `AGGG2.0-сторож: god-файл (${target.slice(-40)}: ${lines} строк, hard ${hard}) — правь в сторону резки, не расти (docs/canon/FILE-SIZE.md)`)
              }
            }
          } catch {}
          // Гейт лимита каталога (docs/canon/ARCHITECTURE.md): ≤ 15 файлов-братьев.
          try {
            const dir = dirname(target)
            const sibs = readdirSync(dir).filter((f) => f.endsWith(".py")
              || f.endsWith(".js") || f.endsWith(".md") || f.endsWith(".sh")
              || f.endsWith(".ts") || f.endsWith(".toml"))
            if (sibs.length > 15) {
              client?.app?.log("warn", `AGGG2.0-сторож: каталог-переросток (${dir.slice(-40)}: ${sibs.length} файлов > 15) — дели по доменам, не добавляй в кучу (docs/canon/ARCHITECTURE.md)`)
            }
          } catch {}
        }
        if (target && DOC_PATTERNS.some((p) => target.replace(/\\/g, "/").includes(p))) {
          client?.app?.log("warn", `AGGG2.0-сторож: правишь канон/скрипт (${target.slice(0, 50)}) — правило в каноне универсальное, БЕЗ имён проектов (проект-специфика → файлы проекта); проверь связанные: python3 scripts/tools/audit/doc_deps.py check <файл> (кто ссылается, зеркала, разнос)`)
        } else if (target && /\.(py|js|ts|sh|toml|json)$/.test(target)) {
          client?.app?.log("warn", `AGGG2.0-сторож: правишь код (${target.slice(0, 50)}) — QA: get_diagnostics → ruff → semgrep → тесты; изменение кода → CHANGELOG`)
        }
      }
    },
    "tool.execute.after": async (input, output) => {
      // Nudge «фоллбэк скиллов»: skills_search.py завершился НЕ результатом
      // (exit 2 «НЕ СМОГ» / «ничего не найдено» / трейсбек) → камуфокс-ресёрч
      // скиллов ОБЯЗАТЕЛЕН (core.txt п.3, docs/canon/skills.sh.md «Порядок поиска»;
      // паттерн: AWS AGENTOPS04-BP03 fallback chain, PostToolUse-фидбек).
      const tool = input?.tool || ""
      if (tool !== "bash" || !output) return
      const st = sessionState(input?.sessionID)
      const cmd = String(input?.args?.command || "")
      if (!/skills_search\.py/.test(cmd)) return
      const text = typeof output?.output === "string"
        ? output.output : JSON.stringify(output ?? "")
      if (/не смог|ничего не найдено|Traceback|No such file|exit code 2/i.test(text)
          && !st.warnedSkillsFallback) {
        st.warnedSkillsFallback = true
        const msg = "AGGG2.0-nudge «фоллбэк скиллов»: skills_search.py НЕ дал результата (не смог/пусто) — ОБЯЗАТЕЛЕН камуфокс-ресёрч скиллов: web_search 3-5 запросов с разных сторон («<тема> agent skill», site:skills.sh, GitHub API) + fetch_page первоисточников (SKILL.md через raw GitHub). «Скрипт не работает» без фоллбэка = НЕ ответ (docs/canon/skills.sh.md «Порядок поиска», core.txt п.3)"
        client?.app?.log("warn", msg)
        return { monologue: msg }
      }
    },
  }
}

// opencode v2: реальные хуки (ctx.tool.hook/ctx.session.hook — beta API,
// проверено пробником 19.08.2026: ctx.tool/session.hook живые в next-17292).
// Динамический импорт + фоллбэк-noop: v1-рантайм (у которого нет Plugin.define
// в @opencode-ai/plugin) или отсутствие пакета не ломает загрузку модуля.
// opencode v1: named export AgGG2Proshivka (совместимость — эвал, старые версии).

// Тексты гейтов v2 (текст ядра — core.txt рядом).
const V2_DB_HINT = "AGGG2.0-гейт: чтение файлов ДО базы — СНАЧАЛА индекс: search.py / MCP db-tools (search, symbol, calls) / findings.py; карта первой: repomap.py project (или MCP repo_map); «мы это уже разбирали» дешевле через базу (DB-FIRST). База не проиндексирована? python3 db-tools/build.py -r <корень> -o db/<имя>.db"
const V2_SEMBLE_HINT = "AGGG2.0-гейт «лестница поиска»: читаешь/грепаешь код после базы ДО semble — смысловые вопросы по коду («где реализовано X», аудит/«что улучшить») идут СНАЧАЛА через MCP semble.search (запрос ТЕРМИНАМИ дока, не бытовым пересказом), потом db-tools (структура) → agent-lsp (символы). Точное имя символа — сразу agent-lsp; keyword — db-tools FTS, не semble (docs/canon/SEMBLE.md, скилл code-search-ladder)."
const V2_WEB_HINT = "AGGG2.0-гейт: правка кода ДО веб-ресёрча — для задач с выбором/неизвестностью СНАЧАЛА быстрые пути: локальная база → скиллы (db/skills.db → skills_search.py) → потом Camoufox (web_search): МИНИМУМ 10 источников на любую задачу (справка/факт — 10, решения/выборы — 30-50, docs/canon/CAMOUFOX.md). «Подумал» без поиска = догадка"
const V2_SKILLS_HINT = "AGGG2.0-nudge «скиллы-первым»: идёшь в веб/дебаг — СНАЧАЛА локальный скилл: python3 db-tools/search.py -b db/skills.db <тема> (или MCP search db=skills). Локальных нет — внешние через skills_search.py (100+ скиллов skills.sh за ~1с, --top по установкам, --read/--tree читают ЛЮБОЙ файл скилла). ДАЖЕ ДЛЯ ДЕБАГА/ИНЦИДЕНТА: сначала чужие скиллы (skills_search.py \"<симптом>\" — debugging/systemd-скиллы), потом факты/лог (qa-debugging: Search The Validated Corpus First). Нашёл подходящий — ЗАГРУЗИ И СЛЕДУЙ; пусто — зафиксируй и иди в веб (docs/canon/SKILLS-LOCAL.md)"

const V2_READ_BASH = /^(grep|cat|head|tail|find|ls|rg)\s/
const V2_SEMBLE_BASH = /semble\.search|semble\.find_related|semble_mcp|tools\.semble/
const V2_DB_BASH = /(findings\.py|search\.py|build\.py|githist\.py|tasks\.py|repomap\.py)/
const V2_WEB_BASH = /camoufox|web_search|fetch_page|browser_navigate|skills_search\.py/
const V2_SHELL_TOOLS = new Set(["bash", "shell"])

async function v2NudgeWrite(sid, event, extra) {
  try {
    const { writeFileSync, mkdirSync } = await import("node:fs")
    const { join } = await import("node:path")
    const { homedir } = await import("node:os")
    const dir = join(homedir(), ".cache", "aggg2-hook")
    mkdirSync(dir, { recursive: true })
    writeFileSync(join(dir, "events.jsonl"),
      JSON.stringify({ ts: new Date().toISOString(), session: sid || "-",
                       event, ...extra }) + "\n", { flag: "a" })
  } catch {}
}

export default (() => {
  const Plugin = Pkg.Plugin
  if (!Plugin?.define) {
    return { id: "aggg2-proshivka", setup: async () => {} }
  }
  return Plugin.define({
    id: "aggg2-proshivka",
    setup: async (ctx) => {
      // 1) Ядро правил + pending-nudge в system ПЕРЕД каждым dispatch модели.
      await ctx.session.hook("context", (ev) => {
        const text = core()
        if (text && !alreadyIn(ev.system)) {
          ev.system.push({ type: "text", text })
        }
        const s = sessionState(ev.sessionID)
        if (s.pending) {
          ev.system.push({ type: "text", text: s.pending })
          s.pending = ""
        }
      })
      // 2) Сторож запретов + nudge-гейты ДО исполнения тула.
      await ctx.tool.hook("execute.before", (ev) => {
        const tool = ev?.tool || ""
        const input = ev?.input
        const s = sessionState(ev?.sessionID)
        // Маркеры сессии.
        if (DB_TOOLS.test(tool)) s.dbTouched = true
        if (SMB_TOOLS.has(tool) || /semble/i.test(tool)) {
          if (!s.sembleTouched) v2NudgeWrite(ev?.sessionID, "semble_used", { tool })
          s.sembleTouched = true
        }
        if (WEB_TOOLS.has(tool)) { s.webTouched = true; s.webCount += 1 }
        if (SKILL_TOOLS.has(tool)) {
          s.skillsTouched = true
          v2NudgeWrite(ev?.sessionID, "skill_loaded",
            { skill: String(input?.name || input?.id || tool) })
        }
        // Shell/bash: блоки запретов + баш-чтение.
        if (V2_SHELL_TOOLS.has(tool)) {
          const cmd = String(input?.command || input?.cmd || "")
          if (!cmd) return
          for (const [re, reason] of BLOCK_RULES) {
            if (re.test(cmd)) {
              throw new Error(`AGGG2.0-сторож: БЛОК — ${reason}`)
            }
          }
          if (/^\s*(grep|rg|ack|ag)\b.*\bWiki\//i.test(cmd)) {
            throw new Error("AGGG2.0-сторож: БЛОК — grep/rg по Wiki/ запрещён: только база (search.py -b db/wiki.db или MCP search db: wiki).")
          }
          if (V2_DB_BASH.test(cmd)) s.dbTouched = true
          if (V2_SEMBLE_BASH.test(cmd) || /semble/i.test(cmd)) {
            if (!s.sembleTouched) v2NudgeWrite(ev?.sessionID, "semble_used", { bash: true })
            s.sembleTouched = true
          }
          if (SKILL_BASH.test(cmd)) { s.skillsTouched = true; s.webTouched = true; s.webCount += 1 }
          if (V2_WEB_BASH.test(cmd)) { s.webTouched = true; s.webCount += 1 }
          if (V2_READ_BASH.test(cmd)) {
            if (!s.dbTouched && !s.warnedDb) { s.warnedDb = true; s.pending = V2_DB_HINT }
            else if (s.dbTouched && !s.sembleTouched && !s.warnedSemble) { s.warnedSemble = true; s.pending = V2_SEMBLE_HINT }
          }
          return
        }
        // Read/grep/glob: база-первым → лестница-semble.
        if (READ_TOOLS.has(tool)) {
          if (!s.dbTouched && !s.warnedDb) { s.warnedDb = true; s.pending = V2_DB_HINT }
          else if (s.dbTouched && !s.sembleTouched && !s.warnedSemble) { s.warnedSemble = true; s.pending = V2_SEMBLE_HINT }
        }
        // Edit/write: ресёрч-первым.
        if (EDIT_TOOLS.has(tool)) {
          if (!s.webTouched && !s.warnedWeb) { s.warnedWeb = true; s.pending = V2_WEB_HINT }
          else if (s.webTouched && s.webCount < 10 && !s.warnedWebLow) {
            s.warnedWebLow = true
            s.pending = `AGGG2.0-гейт: маловато источников (${s.webCount} < 10) для правки — добери до норматива: web_search/fetch_page/batch_fetch (docs/canon/CAMOUFOX.md)`
          }
        }
        // Веб-вызов без локального скилла.
        if (WEB_TOOLS.has(tool) && !s.skillsTouched && !s.warnedSkills) {
          s.warnedSkills = true
          s.pending = V2_SKILLS_HINT
        }
      })
    },
  })
})()

// Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
// AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
