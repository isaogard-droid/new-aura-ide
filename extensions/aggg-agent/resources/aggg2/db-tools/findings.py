#!/usr/bin/env python3
# Shim: канон-команда `python3 db-tools/findings.py add|search|related|...`
# ведёт в кластер знаний knowledge/ (docs/canon/ARCHITECTURE.md: ≤15 файлов-братьев).
# Импорт findings тоже прозрачен: sys.modules подменяется на knowledge.findings.
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
sys.path.insert(0, os.path.join(_here, "knowledge"))
sys.path.insert(0, os.path.join(_root, "scripts"))
sys.modules.pop("findings", None)  # иначе __import__ вернёт сам shim
_f = __import__("findings")
sys.modules[__name__] = _f

if __name__ == "__main__":
    sys.exit(_f.main())
