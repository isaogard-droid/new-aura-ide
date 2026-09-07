#!/usr/bin/env python3
"""Semble MCP server wrapper for AGGG2.0.

Семантический поиск по коду: эмбеддинги + BM25 + code-aware reranking.
98% меньше токенов чем grep+read, 99% качества трансформера.

Использование:
    mcp/semble_mcp.py  # запускает MCP stdio server
"""
import asyncio
import os
from pathlib import Path

# Определяем корень AGGG2.0 относительно этого файла (mcp/semble_mcp.py → ../)
AGGG2_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("SEMBLE_REPO", str(AGGG2_ROOT))

from semble.mcp import serve
from semble.types import ContentType

if __name__ == "__main__":
    asyncio.run(serve(content=[ContentType.CODE, ContentType.DOCS, ContentType.CONFIG]))
