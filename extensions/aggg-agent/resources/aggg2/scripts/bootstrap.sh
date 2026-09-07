#!/usr/bin/env bash
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# Бутстрап НОВОГО железа (Linux/macOS): runtime'ы через mise → setup.py.
# Решает «курицу-и-яйцо»: setup.py — python, а python может отсутствовать.
#
#   ./scripts/bootstrap.sh              # полная установка
#   ./scripts/bootstrap.sh --check      # план setup.py, ничего не ставя
#   ./scripts/bootstrap.sh --skip-db    # любые аргументы уходят в setup.py
#
# Схема (индустриальный паттерн, mise.jdx.dev): один curl → mise
# (без sudo, ~/.local/bin) → mise use -g ставит недостающие runtime'ы
# (python/node/bun/go/rust) → setup.py доставляет MCP/LSP/харнесы/базы.
set -euo pipefail
cd "$(dirname "$0")/.."

MISE="$HOME/.local/bin/mise"
SHIMS="$HOME/.local/share/mise/shims"

have() { command -v "$1" >/dev/null 2>&1; }

CHECK=0
if [ "${1:-}" = "--check" ]; then CHECK=1; SETUP_ARGS=(--check); else SETUP_ARGS=("$@"); fi
# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


RUNTIMES=()
have python3 || RUNTIMES+=(python@3)
have node    || RUNTIMES+=(node@lts)
have bun     || RUNTIMES+=(bun@latest)
have go      || RUNTIMES+=(go@latest)
have rustc   || RUNTIMES+=(rust@latest)

if [ ${#RUNTIMES[@]} -gt 0 ]; then
    echo "== не хватает runtime'ов: ${RUNTIMES[*]} =="
    if [ "$CHECK" -eq 1 ]; then
        echo "   (--check: план без установки — mise не ставим)"
    else
        if [ ! -x "$MISE" ]; then
            echo "== ставим mise (менеджер runtime'ов, без sudo) =="
            curl -fsSL https://mise.run | sh
        fi
        # shims в КОНЕЦ PATH: системные версии не перебиваем, недостающие
        # берутся из mise (иначе shim на непоставленный python уронил бы системный)
        export PATH="$PATH:$SHIMS"
        echo "== ставим через mise: ${RUNTIMES[*]} =="
        "$MISE" use --global "${RUNTIMES[@]}"
    fi
else
    echo "== все runtime'ы уже на месте (python/node/bun/go/rust) =="
fi

echo "== запускаем setup.py ${SETUP_ARGS[*]} =="
exec python3 scripts/setup.py "${SETUP_ARGS[@]}"


# Принадлежит и разработано: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна, новая — ещё лучше.

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
