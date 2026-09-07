#!/usr/bin/env python3
"""Общее ядро батл-раннеров (gui/cli/api): поллинг условий, трассировка,
отчёт. Единый контракт шага:

    {"name", "action" (callable|str), "wait" (callable|str), "want",
     "timeout", "retries"}

Условия (condition-based waiting, паттерн obra/superpowers): wait
возвращает значение, want — предикат Python (None = truthy). Поллинг с
прогрессией: интервал растёт ×2 после 5 стабильных false (до 4с),
сбрасывается при смене значения. Никаких фиксированных sleep.
"""
import json
import time
import traceback

_MISSING = object()
RESULTS = []
START = time.time()


def poll(drive, wait, want, timeout):
    """drive(code) — выполнить действие/взять значение. Возвращает
    (ok, первые_3_различных_значения)."""
    deadline = time.time() + timeout
    interval = 0.6
    stable_false = 0
    firsts = []
    last = _MISSING
    prev = object()
    while time.time() < deadline:
        try:
            last = wait(drive) if callable(wait) else drive(wait)
        except Exception:
            last = _MISSING
        ok = want(last) if want is not None else bool(last)
        if ok:
            return True, None
        if last is not _MISSING and last != prev:
            prev = last
            stable_false = 0
            interval = 0.6
            if len(firsts) < 3:
                firsts.append(last)
        else:
            stable_false += 1
            if stable_false >= 5 and interval < 4.0:
                interval *= 2
        time.sleep(interval)
    return False, firsts


def run(drive, steps, snapshot=None, restore=None, boot_wait=0.0,
        report_out=None, tag=""):
    """Прогон шагов. drive = eval_js/subprocess/HTTP-адаптер.
    Снимок ДО → шаги → откат в finally → отчёт (печать + JSON)."""
    RESULTS.clear()
    snap = None
    try:
        if snapshot is not None:
            snap = snapshot()
            if snap is not None:
                print(f"Снимок: {snap}", flush=True)
        time.sleep(boot_wait)
        for step in steps:
            name = f"[{tag}] {step['name']}" if tag else step["name"]
            t0 = time.time()
            action = step.get("action")
            wait = step.get("wait", "true")
            want = step.get("want")
            timeout = step.get("timeout", 15)
            retries = step.get("retries", 0)
            for _attempt in range(retries + 1):
                try:
                    if action is not None:
                        if callable(action):
                            action()
                        else:
                            drive(action)
                except Exception as exc:
                    print(f"✗ {name} — исключение на действии: {exc}", flush=True)
                    RESULTS.append((name, False))
                    break
                ok, firsts = poll(drive, wait, want, timeout)
                if ok:
                    print(f"✓ {name} ({time.time() - t0:.1f}s)", flush=True)
                    RESULTS.append((name, True))
                    break
            else:
                print(f"✗ {name} — условие не наступило за "
                      f"{timeout * (retries + 1)}s · первых значений: {firsts}",
                      flush=True)
                RESULTS.append((name, False))
    except Exception:
        print("РАННЕР УПАЛ:\n" + traceback.format_exc(), flush=True)
    finally:
        try:
            if snap is not None and restore is not None:
                restore(snap)
        except Exception as exc:
            print(f"ВОССТАНОВЛЕНИЕ НЕ УДАЛОСЬ: {exc}", flush=True)
        ok = sum(1 for _, good in RESULTS if good)
        total = len(RESULTS)
        pct = 100 * ok / max(total, 1)
        print(f"\nИТОГ: {ok}/{total} ({pct:.0f}%) за {time.time() - START:.0f}s",
              flush=True)
        if ok < total:
            print("Отказы:", flush=True)
            for name, good in RESULTS:
                if not good:
                    print(f"  ✗ {name}", flush=True)
        if report_out:
            report = {"ok": ok, "total": total,
                      "seconds": round(time.time() - START, 1),
                      "failures": [n for n, g in RESULTS if not g]}
            with open(report_out, "w", encoding="utf-8") as fh:
                json.dump(report, fh, ensure_ascii=False, indent=2)
    return 0 if ok == total else 1
