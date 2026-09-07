#!/usr/bin/env bash
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# Запуск sherpa-voice: микрофон → текст (локально, без облака).
# Первый запуск создаст venv и скачает модель (~71MB).
#
# Использование:
#   ./run.sh                  # офлайн-модель (лучшее качество)
#   ./run.sh --streaming      # стриминговая small (быстрее, чуть хуже)
#   ./run.sh --file audio.wav # распознать файл
#   ./run.sh --device "hw:0,0"  # явное устройство микрофона
set -euo pipefail

cd "$(dirname "$0")"

VENV_DIR="${SHERPA_VENV:-$HOME/.venvs/aggg2}"
if [ -d "$VENV_DIR" ]; then
    PY="$VENV_DIR/bin/python"
else
    PY=./venv/bin/python
    if [ ! -d venv ]; then
        echo "[~] Первый запуск: создаю venv и ставлю зависимости…"
        python3 -m venv venv
        ./venv/bin/pip install --quiet --upgrade pip
        ./venv/bin/pip install --quiet -r requirements.txt
        echo "[✓] Окружение готово."
    fi
fi
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


exec "$PY" transcribe.py "$@"


# Оригинал от https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна и лучше предыдущей.

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
