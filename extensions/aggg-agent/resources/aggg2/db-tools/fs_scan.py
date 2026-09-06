#!/usr/bin/env python3
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Файловый обход для индексации (вынесено из build.py, docs/canon/FILE-SIZE.md):
is_artifact / load_gitignore / scan_files — быстрый проход без чтения
контента. Вендор/стороннее не индексируем (.cursorignore-паттерн)."""
import fnmatch
import os

_BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp",
                 ".ico", ".bmp"}

def is_artifact(fn):
    """Служебные файлы sqlite, бэкапы и изображения — в текстовую базу не
    заносим. .bak/.orig — резервные копии (gen_index пишет index.md.bak
    перед перезаписью): они дублируют содержимое и мусорят поиск
    (кейс 14.08.2026: фантом index.md.bak в wiki.db, research.db id=489)."""
    return fn.endswith((".db", ".db-shm", ".db-wal", ".db-journal",
                        ".bak", ".orig")) or \
        os.path.splitext(fn)[1].lower() in _BINARY_EXTS


def load_gitignore(root):
    """Минимальный парсер .gitignore: имена папок (как skip_dirs) и
    fnmatch-паттерны для файлов. Правила '!' (не-игнор) не обрабатываем."""
    ignore_dirs, ignore_files = set(), []
    p = os.path.join(root, ".gitignore")
    if not os.path.isfile(p):
        return ignore_dirs, ignore_files
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(("#", "!")):
                    continue
                pat = line.rstrip("/")
                if "*" not in pat and "?" not in pat and "[" not in pat:
                    ignore_dirs.add(pat.lstrip("/"))
                else:
                    ignore_files.append(pat)
    except OSError:
        pass
    return ignore_dirs, ignore_files


def scan_files(root, skip_dirs, skip_files, use_gitignore=False,
               root_skip_dirs=None):
    """Быстрый проход без чтения контента: rel -> (mtime, size)."""
    if root_skip_dirs is None:
        root_skip_dirs = set()
    out = {}
    gi_dirs, gi_files = load_gitignore(root) if use_gitignore else (set(), [])
    skip = set(skip_dirs) | gi_dirs
    root_abs = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        # root_skip_dirs исключаются ТОЛЬКО на корневом уровне (вендор в
        # корне), а не по имени везде: канон skills/fable-method/ должен
        # индексироваться.
        dirnames[:] = [d for d in dirnames
                       if d not in skip
                       and not (os.path.abspath(dirpath) == root_abs
                                and d in root_skip_dirs)]
        for fn in sorted(filenames):
            if fn in skip_files or is_artifact(fn):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            if gi_files and any(
                    fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel, p.lstrip("/"))
                    for p in gi_files):
                continue
            out[rel] = (os.path.getmtime(full), os.path.getsize(full))
    return out
