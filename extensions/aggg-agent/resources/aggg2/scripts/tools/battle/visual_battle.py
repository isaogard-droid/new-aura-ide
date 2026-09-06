#!/usr/bin/env python3
"""Визуальная регрессия: пиксельный дифф против baseline (PIL).

Конфиг — Python-модуль с CONFIG:
    CONFIG = {
        "shots": [
            {"name": "…", "capture": callable -> PIL.Image,
             "baseline": "shots/home.png",
             "threshold": 0.05,       # per-pixel допуск канала (0-1)
             "max_diff_ratio": 0.01}, # доля пикселей сверх допуска
        ],
    }

Пороги — паттерн индустрии (frontendcomponent): threshold гасит
anti-aliasing-шум (5% на канал), maxDiffPixelRatio отделяет регрессию
от субпиксельной пыли. `--update` перезаписывает baseline'ы (после
осознанного изменения UI), иначе только сравнение.
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import battle_core  # noqa: E402
from PIL import Image, ImageChops  # noqa: E402


def diff_ratio(img_a, img_b, threshold):
    if img_a.size != img_b.size:
        return 1.0
    diff = ImageChops.difference(img_a.convert("RGB"), img_b.convert("RGB"))
    import numpy
    arr = numpy.asarray(diff, dtype=numpy.int16)
    over = (arr > threshold * 255).any(axis=2)
    return float(over.mean())


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    spec = importlib.util.spec_from_file_location("visual_config", sys.argv[1])
    cfg_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg_mod)
    cfg = getattr(cfg_mod, "CONFIG", None)
    if not isinstance(cfg, dict):
        raise SystemExit(f"в {sys.argv[1]} нет CONFIG (dict)")

    update = "--update" in sys.argv
    results = []

    def drive(shot):
        if shot == "__last__":
            return results[-1] if results else None
        img = shot["capture"]()
        base_path = Path(shot["baseline"])
        if update or not base_path.exists():
            base_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(base_path)
            results.append("baseline обновлён")
            return results[-1]
        baseline = Image.open(base_path)
        ratio = diff_ratio(baseline, img, shot.get("threshold", 0.05))
        results.append(f"diff={ratio:.4f}")
        return results[-1]

    steps = []
    for s in cfg["shots"]:
        want_ratio = s.get("max_diff_ratio", 0.01)
        def ok(v, ratio=want_ratio):
            if not isinstance(v, str):
                return False
            if v == "baseline обновлён":  # baseline создан/перезаписан
                return True
            try:
                return float(v.split("=")[1]) <= ratio
            except (IndexError, ValueError):
                return False

        steps.append({"name": s["name"], "action": s, "wait": "__last__",
                      "want": ok, "timeout": 30})
    out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    sys.exit(battle_core.run(drive, steps, report_out=out, tag="visual"))


if __name__ == "__main__":
    main()
