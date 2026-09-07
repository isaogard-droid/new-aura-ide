#!/usr/bin/env python3
"""design_teardown — инструменты разбора дизайна (только stdlib).

  css <файл.css>            извлечь дизайн-токены из CSS в таблицу
  histogram <файл.png>      палитра скриншота (нужен ImageMagick convert)

Вывод — в stdout, диагностика — в stderr. Exit: 0 ok, 1 ошибка ввода,
2 отсутствует ImageMagick.
"""
import re
import subprocess
import sys
from collections import Counter

HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})\b")
RGB_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)")


def _hex_to_rgb(value):
    value = value.lstrip("#")
    if len(value) in (3, 4):
        value = "".join(c * 2 for c in value)
    r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    return (r, g, b)


def css_tokens(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            css = fh.read()
    except OSError as exc:
        print(f"не удалось прочитать {path}: {exc}", file=sys.stderr)
        return 1

    colors = Counter()
    for match in HEX_RE.finditer(css):
        if len(match.group(1)) in (3, 6):
            colors[_hex_to_rgb(match.group(1))] += 1
    for match in RGB_RE.finditer(css):
        colors[(int(match.group(1)), int(match.group(2)), int(match.group(3)))] += 1

    props = {}
    for prop, pattern in (
        ("шрифты", r"font-family\s*:\s*([^;}]+)"),
        ("радиусы", r"border-radius\s*:\s*([^;}]+)"),
        ("тени", r"box-shadow\s*:\s*([^;}]+)"),
        ("высоты", r"(?:height|line-height)\s*:\s*(\d+px)"),
    ):
        values = Counter(m.strip() for m in re.findall(pattern, css, re.IGNORECASE))
        props[prop] = values.most_common(12)

    print("== ПАЛИТРА (rgb : вхождений) ==")
    for (r, g, b), count in colors.most_common(20):
        print(f"  #{r:02X}{g:02X}{b:02X}  {count}")
    for title, values in props.items():
        print(f"== {title} (топ значений) ==")
        for value, count in values:
            print(f"  {value}  x{count}")
    return 0


def histogram(path, n_colors):
    cmd = ["convert", path, "-resize", "50%", "-colors", str(n_colors),
           "-unique-colors", "txt:"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("нужен ImageMagick (convert). dnf install ImageMagick", file=sys.stderr)
        return 2
    print("== ПАЛИТРА СКРИНШОТА ==")
    for line in proc.stdout.splitlines()[1:]:
        print("  " + line)
    return 0


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 1
    if sys.argv[1] == "css":
        return css_tokens(sys.argv[2])
    if sys.argv[1] == "histogram":
        n = 14
        if len(sys.argv) > 3:
            n = int(sys.argv[3])
        return histogram(sys.argv[2], n)
    print(__doc__, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
