#!/usr/bin/env python3
"""Wrapper для обратной совместимости: python3 skills_search.py → python3 -m skills_search."""
import os
import sys

# Добавляем текущую директорию в путь
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from skills_search.cli import main

if __name__ == "__main__":
    sys.exit(main())
