#!/usr/bin/env bash
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.




# Разработано для https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна, дальше — ещё лучше.
# Запуск тестов sherpa-voice.
#   ./run_tests.sh           # юнит-тесты + проверка зеркал AGENTS.md (быстро, без железа)
#   ./run_tests.sh --e2e     # + полный цикл test_cycle.py (нужны модель, espeak-ng, ключ DeepSeek)
#   ./run_tests.sh --mirrors # только проверка зеркал AGENTS.md
set -euo pipefail
cd "$(dirname "$0")"
# Windows-консоль cp1251 ломает русский вывод (✓/✗) — переключаем на UTF-8.
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
# Кроссплатформенный выбор интерпретатора: bin/python (Linux/macOS) vs
# Scripts/python.exe (Windows); вынесенный venv имеет приоритет.
PY=""
for cand in "$HOME/.venvs/aggg2/bin/python" \
            "$HOME/.venvs/aggg2/Scripts/python.exe" \
            "./venv/bin/python" \
            "./venv/Scripts/python.exe"; do
    if [ -x "$cand" ]; then
        PY="$cand"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "[✗] venv нет — сначала ./run.sh (создаст окружение)"
    exit 1
fi

MIRRORS=("$HOME/.config/opencode/AGENTS.md"
         "$PWD/../../AGENTS.md"
         "$PWD/AGENTS.md")
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


check_mirrors() {
    echo "[~] Проверяю зеркала AGENTS.md…"
    # CRLF-нормализация: на Windows копии пишутся с \r\n, корень — LF;
    # сравниваем без \r, чтобы md5 не различался из-за окончаний строк.
    local first h bad=0
    first=$(tr -d '\r' < "${MIRRORS[0]}" | md5sum | cut -d' ' -f1)
    for f in "${MIRRORS[@]}"; do
        h=$(tr -d '\r' < "$f" | md5sum | cut -d' ' -f1)
        if [ "$h" != "$first" ]; then
            echo "[✗] расхождение: $f"
            bad=1
        fi
    done
    if [ "$bad" = 1 ]; then
        echo "[✗] зеркала разошлись — править все три одинаково"
        return 1
    fi
    echo "[✓] зеркала идентичны"
    return 0
}

case "${1:-}" in
    --mirrors)
        check_mirrors
        ;;
    --e2e)
        check_mirrors
        "$PY" -m unittest discover -s tests -t .
        echo "[~] e2e-цикл (модель, синтез, DeepSeek)…"
        "$PY" test_cycle.py
        ;;
    *)
        check_mirrors
        "$PY" -m unittest discover -s tests -t .
        ;;
esac

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
