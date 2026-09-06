#!/usr/bin/env python3
"""Сжатие вывода команд — сырой вывод не в контекст.

Паттерн context-mode: 315 KB → 5.4 KB (98% reduction).
Агент НЕ читает 1000+ строк — скрипт выводит только нужное.

Использование:
    long_command | python3 sandbox_output.py                     # auto: head-tail 20 + stats
    long_command | python3 sandbox_output.py --errors            # только error/fail/exception
    long_command | python3 sandbox_output.py --grep PATTERN      # фильтр по паттерну
    long_command | python3 sandbox_output.py --unique            # уникальные строки
    long_command | python3 sandbox_output.py --top 10            # первые 10
    long_command | python3 sandbox_output.py --head-tail 15      # 15 сверху + 15 снизу + stats
    long_command | python3 sandbox_output.py --stats             # только статистика
    long_command | python3 sandbox_output.py --max-lines 50      # порог авто-сжатия (default 100)
    long_command | python3 sandbox_output.py --command pytest    # спец-обработчик
    long_command | python3 sandbox_output.py --budget 500        # token budget (~4 chars/token)
    long_command | python3 sandbox_output.py --strip-ansi        # убрать ANSI escape
    long_command | python3 sandbox_output.py --no-progress       # убрать progress bars

Комбо:
    long_command | python3 sandbox_output.py --no-empty --dedup --errors --top 20
    pytest tests/ | python3 sandbox_output.py --strip-ansi --no-progress --budget 800
"""
import argparse
import re
import sys
from collections import Counter

ERROR_PATTERN = re.compile(
    r"(error|fail|exception|traceback|critical|fatal|denied|refused|"
    r"timeout|killed|assert|panic|undefined|cannot|unable|missing|"
    r"violation|overflow|segfault|sigsegv|sigabrt)",
    re.IGNORECASE,
)

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

PROGRESS_PATTERNS = re.compile(
    r'(?:'
    r'\r.*\d+%'
    r'|\[.*\]\s*\d+/\d+'
    r'|Downloading.*\d+%'
    r'|Resolving\s'
    r'|Linking\s'
    r'|Compiling.*\(\d+/\d+\)'
    r'|\d+\.\d+s\s*-\s*\w+'
    r'|^\s*\.{10,}\s*\d+\s*%'
    r')',
    re.IGNORECASE,
)


def read_input(args):
    if args.file:
        with open(args.file, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    if not sys.stdin.isatty():
        return sys.stdin.readlines()
    print("Ошибка: нет ввода. Передайте через pipe или --file.", file=sys.stderr)
    sys.exit(1)


def filter_no_empty(lines):
    return [line for line in lines if line.strip()]


def filter_grep(lines, pattern):
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error:
        rx = re.compile(re.escape(pattern), re.IGNORECASE)
    return [line for line in lines if rx.search(line)]


def filter_errors(lines):
    return [line for line in lines if ERROR_PATTERN.search(line)]


def filter_unique(lines):
    seen = set()
    result = []
    for line in lines:
        key = line.strip()
        if key not in seen:
            seen.add(key)
            result.append(line)
    return result


def filter_dedup(lines):
    counts = Counter(line.strip() for line in lines)
    result = []
    seen = set()
    for line in lines:
        key = line.strip()
        if key not in seen:
            seen.add(key)
            count = counts[key]
            if count > 1:
                result.append(f"{line.rstrip()}  (×{count})\n")
            else:
                result.append(line)
    return result


def strip_ansi(lines):
    return [ANSI_ESCAPE.sub('', line) for line in lines]


def remove_progress(lines):
    return [line for line in lines
            if not PROGRESS_PATTERNS.search(line) and '\r' not in line]


def estimate_tokens(text):
    return len(text) // 4


def enforce_budget(lines, max_tokens):
    text = "".join(lines)
    tokens = estimate_tokens(text)
    if tokens <= max_tokens:
        return lines, False
    target_chars = max_tokens * 4
    truncated_text = text[:target_chars]
    result_lines = [truncated_text]
    result_lines.append(
        f"\n[TRUNCATED: {tokens} tokens → {max_tokens} token budget. "
        f"Use --file or pagination to retrieve more.]\n"
    )
    return result_lines, True


def detect_command(lines):
    if not lines:
        return None
    first = lines[0].lower()
    if 'on branch' in first:
        return 'git status'
    if 'passed' in first or 'failed' in first or '=====' in first:
        return 'pytest'
    if first.startswith('total ') or (len(lines) > 1 and lines[1].strip().startswith('total')):
        return 'ls'
    if any('compiling' in line.lower() for line in lines[:5]):
        return 'cargo'
    if any('npm warn' in line.lower() or 'npm err' in line.lower()
           for line in lines[:5]):
        return 'npm'
    return None


def compress_git_status(lines):
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('On branch') or stripped.startswith('HEAD detached') or stripped.startswith('Your branch'):
            result.append(line)
        elif stripped in ('Changes not staged for commit:',
                          'Changes to be committed:',
                          'Untracked files:',
                          'modified:', 'new file:', 'deleted:',
                          'renamed:', 'typechange:', 'copied:') or any(stripped.startswith(p) for p in ('modified:', 'new file:', 'deleted:',
                                                    'renamed:', 'typechange:', 'copied:')) or stripped and not stripped.startswith(('(', '\t', 'no changes')):
            result.append(f"  {stripped}\n")
    return result or lines


def compress_pytest(lines):
    result = []
    for line in lines:
        if 'FAILED' in line or 'ERROR' in line or '===' in line and ('passed' in line or 'failed' in line or 'error' in line) or 'short test summary' in line.lower():
            result.append(line)
    return result or lines


def compress_ls(lines):
    result = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 9:
            filename = parts[-1]
            if filename not in ('.', '..'):
                result.append(filename + '\n')
        elif parts and not parts[0].startswith('total'):
            result.append(line)
    return result or lines


def compress_cat(lines, max_lines=50):
    if len(lines) <= max_lines:
        return [f"{i+1}: {line}" for i, line in enumerate(lines)]
    half = max_lines // 2
    result = [f"{i+1}: {line}" for i, line in enumerate(lines[:half])]
    result.append(f"\n... {len(lines) - max_lines} lines omitted ...\n")
    start = len(lines) - half
    result.extend([f"{start+i+1}: {line}" for i, line in enumerate(lines[-half:])])
    return result


def compress_cargo(lines):
    result = []
    for line in lines:
        if 'error' in line.lower() or 'warning' in line.lower() or 'test result' in line.lower() or 'FAILED' in line or 'failures:' in line.lower():
            result.append(line)
    return result or lines


def compress_npm(lines):
    result = []
    for line in lines:
        if 'ERR!' in line or 'error' in line.lower() or 'added' in line.lower() or 'removed' in line.lower() or 'up to date' in line.lower() or 'warn' in line.lower() and 'npm warn' in line.lower():
            result.append(line)
    return result or lines


COMMAND_HANDLERS = {
    'git status': compress_git_status,
    'pytest': compress_pytest,
    'ls': compress_ls,
    'cargo': compress_cargo,
    'npm': compress_npm,
}


def auto_compress(lines):
    cmd = detect_command(lines)
    if cmd and cmd in COMMAND_HANDLERS:
        return COMMAND_HANDLERS[cmd](lines)
    return lines


def compute_stats(lines, original_count):
    total = len(lines)
    bytes_total = sum(len(line.encode("utf-8")) for line in lines)
    unique = len(set(line.strip() for line in lines))
    empty = sum(1 for line in lines if not line.strip())
    errors = sum(1 for line in lines if ERROR_PATTERN.search(line))
    tokens = estimate_tokens("".join(lines))

    if bytes_total > 1024 * 1024:
        size = f"{bytes_total / 1024 / 1024:.1f} MB"
    elif bytes_total > 1024:
        size = f"{bytes_total / 1024:.1f} KB"
    else:
        size = f"{bytes_total} B"

    return (
        f"\n--- stats: {total} строк"
        + (f" (из {original_count}, сжато {100 - total * 100 // max(original_count, 1)}%)"
           if total < original_count else "")
        + f" | {size} | ~{tokens} tok | {unique} уникальных | {errors} ошибок"
        + (f" | {empty} пустых" if empty else "")
        + " ---\n"
    )


def head_tail(lines, n):
    if len(lines) <= n * 2 + 1:
        return lines, 0
    skipped = len(lines) - n * 2
    return lines[:n] + [f"\n... пропущено {skipped} строк ...\n"] + lines[-n:], skipped


def main():
    parser = argparse.ArgumentParser(description="Сжатие вывода команд")
    parser.add_argument("--file", "-f", help="Файл вместо stdin")
    parser.add_argument("--grep", "-g", help="Фильтр по паттерну (regex)")
    parser.add_argument("--errors", "-e", action="store_true",
                        help="Только строки с error/fail/exception/traceback")
    parser.add_argument("--unique", "-u", action="store_true",
                        help="Уникальные строки (первое вхождение)")
    parser.add_argument("--dedup", action="store_true",
                        help="Убрать дубликаты с счётчиком (×N)")
    parser.add_argument("--no-empty", action="store_true",
                        help="Убрать пустые строки")
    parser.add_argument("--top", type=int, help="Первые N строк")
    parser.add_argument("--tail", type=int, help="Последние N строк")
    parser.add_argument("--head-tail", type=int, dest="head_tail",
                        help="N сверху + N снизу + статистика пропущенных")
    parser.add_argument("--stats", action="store_true",
                        help="Только статистика (без строк)")
    parser.add_argument("--max-lines", type=int, default=100, dest="max_lines",
                        help="Порог авто-сжатия (default: 100)")
    parser.add_argument("--context", "-c", type=int, default=20,
                        help="Контекст для auto/head-tail (default: 20)")
    parser.add_argument("--command", help="Спец-обработчик: git status|pytest|ls|cargo|npm")
    parser.add_argument("--budget", type=int,
                        help="Token budget (~4 chars/token, default: без лимита)")
    parser.add_argument("--strip-ansi", action="store_true", dest="strip_ansi",
                        help="Удалить ANSI escape sequences")
    parser.add_argument("--no-progress", action="store_true", dest="no_progress",
                        help="Удалить progress bars / spinners")
    parser.add_argument("--auto-detect", action="store_true", dest="auto_detect",
                        help="Авто-детект команды для спец-обработки")
    args = parser.parse_args()

    lines = read_input(args)
    original_count = len(lines)

    if args.strip_ansi:
        lines = strip_ansi(lines)
    if args.no_progress:
        lines = remove_progress(lines)

    if args.command and args.command in COMMAND_HANDLERS:
        lines = COMMAND_HANDLERS[args.command](lines)
    elif args.auto_detect:
        lines = auto_compress(lines)

    if args.stats and not any([args.grep, args.errors, args.unique, args.dedup,
                                args.top, args.tail, args.head_tail, args.no_empty]):
        print(compute_stats(lines, original_count), end="")
        return

    if args.no_empty:
        lines = filter_no_empty(lines)
    if args.grep:
        lines = filter_grep(lines, args.grep)
    if args.errors:
        lines = filter_errors(lines)
    if args.unique:
        lines = filter_unique(lines)
    if args.dedup:
        lines = filter_dedup(lines)
    if args.top is not None:
        lines = lines[:args.top]
    elif args.tail is not None:
        lines = lines[-args.tail:]
    elif args.head_tail is not None:
        lines, _ = head_tail(lines, args.head_tail)
    elif not any([args.grep, args.errors, args.unique, args.dedup,
                  args.top, args.tail, args.head_tail, args.command, args.auto_detect]) \
            and len(lines) > args.max_lines:
        lines, _ = head_tail(lines, args.context)

    if args.budget:
        lines, _ = enforce_budget(lines, args.budget)

    output = "".join(lines)
    print(output, end="")

    show_stats = (original_count > args.max_lines
                  or args.head_tail is not None
                  or args.stats
                  or args.budget is not None
                  or args.command is not None
                  or args.auto_detect)
    if show_stats:
        print(compute_stats(lines, original_count), end="")


if __name__ == "__main__":
    main()
