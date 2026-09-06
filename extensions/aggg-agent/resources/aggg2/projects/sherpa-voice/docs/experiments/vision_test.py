#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Тест: поддерживает ли DeepSeek API изображения (мультимодальность).

Ключ и модель — из .env рядом со скриптом (через deepseek_ai, как остальной
проект). Скриншот — аргумент; без аргумента берётся самый свежий PNG из
~/Изображения/Снимки экрана. Если модель не умеет картинки — ошибка API."""
import base64
import glob
import json
import os
import sys
import urllib.request

import deepseek_ai

# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

key = deepseek_ai.load_key()
if not key:
    print("[✗] Нет ключа DeepSeek — положите DEEPSEEK_API_KEY в .env рядом со скриптом.")
    sys.exit(1)
model = deepseek_ai.load_model()


def latest_screenshot():
    shots_dir = os.path.expanduser("~/Изображения/Снимки экрана")
    if not os.path.isdir(shots_dir):
        return None
    pngs = sorted(glob.glob(os.path.join(shots_dir, "*.png")),
                  key=os.path.getmtime, reverse=True)
    return pngs[0] if pngs else None


img_path = sys.argv[1] if len(sys.argv) > 1 else latest_screenshot()
if not img_path:
    print("[✗] Файл не передан и свежих скриншотов не найдено. "
          "Использование: docs/experiments/vision_test.py [путь-к-изображению]")
    sys.exit(1)
if not os.path.isfile(img_path):
    print(f"[✗] Файл не найден: {img_path}")
    sys.exit(1)

try:
    with open(img_path, "rb") as _f:
        b64 = base64.b64encode(_f.read()).decode()
except OSError as e:
    print(f"[✗] Не удалось прочитать файл: {e}")
    sys.exit(1)

body = json.dumps({
    "model": model,
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Опиши, что изображено на скриншоте, и назови проблему в интерфейсе. Отвечай по-русски, кратко."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ],
    }],
    "stream": False,
}).encode()

req = urllib.request.Request(
    "https://api.deepseek.com/chat/completions", data=body,
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
try:
    # URL константный (api.deepseek.com), ключ — в Authorization
    with urllib.request.urlopen(req, timeout=120) as r:  # nosemgrep
        data = json.load(r)
    print("OK:", data["choices"][0]["message"]["content"])
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}:", e.read().decode("utf-8", "replace")[:800])
except Exception as e:
    print("ERR:", type(e).__name__, e)


# Разработка и права: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна, следующая — ещё лучше.

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
