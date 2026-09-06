#!/usr/bin/env python3
"""Web-батл: браузерный E2E на Playwright (auto-waiting — паттерн
Playwright: клики ждут элемент сами, sleep не нужен).

Конфиг — Python-модуль с CONFIG:
    CONFIG = {
        "base": "http://127.0.0.1:8000",     # None — адреса в шагах
        "headless": True,
        "snapshot"/"restore": как обычно,
        "steps": [
            {"name": "…", "action": "page.goto(base + '/')",
             "wait": "page.locator('#out').text_content()",
             "want": lambda v: v == "ok", "timeout": 15},
        ],
    }

drive(code) исполняет Python-выражение над {page, base, expect}:
- page — playwright sync Page (goto/click/fill/locator…);
- expect(page.locator(...)) — авто-ожидание видимости/текста;
- base — адрес из конфига.
Прогресс сразу; --json <файл> — отчёт; --headed — видимый браузер.
"""
import importlib.util
import sys
from contextlib import suppress

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import battle_core  # noqa: E402


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    spec = importlib.util.spec_from_file_location("web_config", sys.argv[1])
    cfg_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg_mod)
    cfg = getattr(cfg_mod, "CONFIG", None)
    if not isinstance(cfg, dict):
        raise SystemExit(f"в {sys.argv[1]} нет CONFIG (dict)")

    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    launch = {"headless": cfg.get("headless", True)
              and "--headed" not in sys.argv}
    if cfg.get("channel"):
        launch["channel"] = cfg["channel"]  # напр. "chrome" — системный браузер
    browser = pw.chromium.launch(**launch)
    page = browser.new_page()
    base = cfg.get("base", "")
    ns = {"page": page, "base": base}
    from playwright.sync_api import expect as _expect
    ns["expect"] = _expect

    def drive(code):
        return eval(  # noqa: S307  # nosemgrep: python.lang.security.audit.eval-detected.eval-detected — battle config is an explicitly local trusted test input; builtins are removed
            code, {"__builtins__": {}}, ns)

    try:
        out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
        code = battle_core.run(drive, cfg["steps"],
                               snapshot=cfg.get("snapshot"),
                               restore=cfg.get("restore"),
                               report_out=out, tag="web")
        sys.exit(code)
    finally:
        with suppress(Exception):
            browser.close()
        pw.stop()


if __name__ == "__main__":
    main()
