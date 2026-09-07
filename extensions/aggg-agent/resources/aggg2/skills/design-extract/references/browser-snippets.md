# Сниппеты браузера: computed styles и скриншот

Для извлечения дизайна с живого сайта. Два варианта: Camoufox
(есть в воркспейсе, антидетект — проходит бот-щиты) и playwright.

## Camoufox: computed styles ключевых селекторов

```python
# запускать через venv с camoufox (в воркспейсе — ~/.venvs/aggg2)
from camoufox.sync_api import Camoufox

with Camoufox(headless=True) as browser:
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto("https://example.com", wait_until="domcontentloaded",
              timeout=45000)
    page.wait_for_timeout(3000)  # дать JS достроить DOM
    info = page.evaluate("""() => {
      const gs = (sel) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const s = getComputedStyle(el);
        return { bg: s.backgroundColor, color: s.color,
                 font: s.fontFamily.slice(0, 40), fs: s.fontSize,
                 br: s.borderRadius, border: s.borderColor,
                 pad: s.padding, weight: s.fontWeight,
                 tt: s.textTransform, shadow: s.boxShadow.slice(0, 60) };
      };
      return {
        header: gs('.header-in'), nav: gs('.nav-menu a'),
        card: gs('.cols'), button: gs('button'),
        h1: gs('h1'), footer: gs('.footer'),
      };
    }""")
    print(info)
```

Селекторы брать из HTML референса: хедер, навигация, карточки,
кнопки, инпуты, заголовки, футер, бейджи.

## Camoufox: скриншот

```python
from camoufox.sync_api import Camoufox

with Camoufox(headless=True) as browser:
    page = browser.new_page(viewport={"width": 1280, "height": 1600})
    page.goto("https://example.com", wait_until="networkidle",
              timeout=45000)
    page.screenshot(path="/tmp/opencode/reference.png")
```

Дальше — `design_teardown.py histogram /tmp/opencode/reference.png`.

## Playwright (альтернатива без Camoufox)

```bash
cd <папка скилла> && npm install playwright   # зависимость в папку скилла
```

```js
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  await p.goto('https://example.com', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(3000);
  const info = await p.evaluate(() => {
    const s = getComputedStyle(document.querySelector('.header-in'));
    return { bg: s.backgroundColor, color: s.color, fs: s.fontSize };
  });
  console.log(info);
  await p.screenshot({ path: '/tmp/opencode/reference.png' });
  await b.close();
})();
```

## Грабли

- `waitUntil: 'networkidle'` на рекламных сайтах может не сработать
  никогда — фолбэк на `domcontentloaded` + `wait_for_timeout`.
- Снимать computed styles ПОСЛЕ задержки: JS-виджеты достраивают DOM.
- Для бот-щитов: Camoufox > curl; если и он в капче — пробовать
  мобильный viewport и `domcontentloaded` вместо networkidle.
- Если селектор не найден — `gs` вернёт null: смотреть реальный HTML
  (`page.content()`), а не угадывать имена классов.
