#!/usr/bin/env python3
"""API-батл: каждый эндпоинт и статус-код, контракт по схеме.

Конфиг — Python-модуль с CONFIG:
    CONFIG = {
        "base": "http://127.0.0.1:9090",  # или callable() -> str
        "timeout": 10,                    # таймаут запроса
        "headers": None | dict,
        "snapshot": callable() -> dict | None,
        "restore": callable(snap) | None,
        "steps": [
            {"name": "...", "method": "GET", "path": "/version",
             "want": lambda r: r.status_code == 200,
             "schema": {"version": str} | None,   # типы полей JSON
             "body": None | dict, "json": True,
             "timeout": 10},
        ],
    }

Паттерны (ресёрч 19.08): каждый статус-код — не только 200; схема —
типы полей, а не наличие; 401/403/404 отдельными шагами; идемпотентность
— повторный запрос. Progress печатается сразу; --json <файл> — отчёт.
"""
import importlib.util
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import battle_core  # noqa: E402


def _do(base, step):
    url = (base if callable(base) else base) + step["path"]
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {"status": None, "text": "недопустимый HTTP URL", "json": None}
    headers = step.get("headers") or {}
    data = None
    if step.get("body") is not None:
        import json as _json
        data = _json.dumps(step["body"]).encode()
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=step.get("method", "GET"))
    try:
        with urllib.request.urlopen(req, timeout=step.get("timeout", 10)) as resp:  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected — scheme and netloc are validated above
            body = resp.read().decode("utf-8", "replace")
            return {"status": resp.status, "text": body,
                    "json": _parse(body), "headers": dict(resp.headers)}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return {"status": exc.code, "text": body, "json": _parse(body)}
    except Exception as exc:
        return {"status": None, "text": str(exc), "json": None}


def _parse(text):
    import json as _json
    try:
        return _json.loads(text)
    except Exception:
        return None


def _schema_ok(data, schema):
    if not isinstance(data, dict) or not isinstance(schema, dict):
        return False
    return all(k in data and isinstance(data[k], t) for k, t in schema.items())


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    spec = importlib.util.spec_from_file_location("api_config", sys.argv[1])
    cfg_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg_mod)
    cfg = getattr(cfg_mod, "CONFIG", None)
    if not isinstance(cfg, dict):
        raise SystemExit(f"в {sys.argv[1]} нет CONFIG (dict)")

    base = cfg.get("base", "")
    _last = [None]

    def drive(path):
        if path == "__last__":
            return _last[0]
        r = _do(base, path if isinstance(path, dict) else {"path": path})
        _last[0] = r
        return r

    steps = []
    for s in cfg["steps"]:
        want = s.get("want")
        schema = s.get("schema")

        def check(r, w=want, sc=schema):
            if not isinstance(r, dict):
                return False
            if w is not None and not w(r):
                return False
            if sc is not None:
                return _schema_ok(r.get("json"), sc)
            return True

        steps.append({"name": s["name"], "action": s,
                      "wait": "__last__", "want": check,
                      "timeout": s.get("timeout", 10)})
    out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    code = battle_core.run(drive, steps,
                           snapshot=cfg.get("snapshot"),
                           restore=cfg.get("restore"),
                           report_out=out, tag="api")
    sys.exit(code)


if __name__ == "__main__":
    main()
