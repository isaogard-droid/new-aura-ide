# Vendored from snowballstemmer 3.1.1 (PyPI) — только русский стеммер.
# Источник: https://pypi.org/project/snowballstemmer/ (BSD-2-Clause,
# Richard Boulton / snowballstem.org). Алгоритм Snowball Russian:
# https://snowballstem.org/algorithms/russian/stemmer.html
# Вендорено 17.08.2026 (research.db id=786): пакет целиком тянет 29 языков,
# нам нужен один; базовый фреймворк (basestemmer.py) и таблицы Among
# сохранены как есть.
__all__ = ('RussianStemmer', 'stemmer')

from .russian_stemmer import RussianStemmer


def stemmer(lang):
    if lang.lower() == 'russian':
        return RussianStemmer()
    raise KeyError("Stemming algorithm '%s' not found" % lang)
