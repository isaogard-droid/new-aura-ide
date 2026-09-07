#!/usr/bin/env bash
# Aura IDE — pull new changes and rebuild the installed desktop app (Linux).
# Usage: ./scripts/update-aura.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/4] git pull (main)…"
git checkout main 2>/dev/null || true
git pull --ff-only origin main

echo "[2/4] npm install…"
npm install --no-audit --no-fund

echo "[3/4] rebuild…"
npm run gulp vscode-linux-x64

echo "[4/4] reinstall (keeps settings in ~/.vscode-oss-aura)…"
./scripts/install-desktop.sh --skip-build

echo "Готово. Обновление установлено. Запустите Aura IDE заново."
