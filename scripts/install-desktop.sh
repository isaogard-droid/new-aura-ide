#!/usr/bin/env bash
# Aura IDE — install as a desktop application (Linux).
# Builds the Electron app and creates a desktop launcher/icon.
# Usage: ./scripts/install-desktop.sh [--skip-build]
set -euo pipefail
cd "$(dirname "$0")/.."

PLATFORM="$(uname -s)"
if [ "$PLATFORM" != "Linux" ]; then
  echo "Этот скрипт — для Linux. На Windows используйте scripts/install-desktop.bat (или смотрите docs/desktop-app.md)." >&2
  exit 1
fi

APP_NAME="Aura IDE"
APP_ID="aura-ide"
DEST="$HOME/.local/share/${APP_ID}"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$HOME/.local/share/applications/${APP_ID}.desktop"

if [ "${1:-}" != "--skip-build" ]; then
  echo "[1/3] Сборка Electron-приложения (vscode-linux-x64)…"
  npm run gulp vscode-linux-x64
fi

BUILT="$(ls -d ../VSCode-linux-x64 2>/dev/null || echo '')"
if [ -z "$BUILT" ]; then
  echo "Готовой сборки не найдено в ../VSCode-linux-x64. Запустите без --skip-build." >&2
  exit 1
fi

echo "[2/3] Установка в $DEST …"
rm -rf "$DEST"
cp -r "$BUILT" "$DEST"
mkdir -p "$BIN_DIR" "$HOME/.local/share/applications"
ln -sf "$DEST/aura-ide" "$BIN_DIR/aura-ide" || true

# Иконка из ресурсов сборки
ICON="$DEST/resources/app/resources/linux/code.png"
[ -f "$ICON" ] || ICON="$(find "$DEST/resources" -name '*.png' | head -1)"

echo "[3/3] Создание ярлыка на рабочем столе …"
cat > "$LAUNCHER" <<EOF
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Редактор кода Aura IDE (форк VS Code с плагинами Aura API и AGGG)
Exec=${DEST}/aura-ide
Icon=${ICON}
Terminal=false
Categories=Development;IDE;TextEditor;
Keywords=vscode;code;editor;aura;
StartupWMClass=${APP_ID}
EOF
chmod +x "$LAUNCHER" "$DEST/aura-ide"
ln -sf "$LAUNCHER" "$HOME/Рабочий стол/${APP_ID}.desktop" 2>/dev/null || true
ln -sf "$LAUNCHER" "$HOME/Desktop/${APP_ID}.desktop" 2>/dev/null || true
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "Готово. Aura IDE установлен: $DEST"
echo "Ярлык: $LAUNCHER (и на рабочем столе при наличии XDG Desktop)."
echo "Обновление: ./scripts/update-aura.sh"
