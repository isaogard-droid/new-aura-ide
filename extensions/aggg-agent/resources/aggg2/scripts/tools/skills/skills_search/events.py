"""Логирование событий скиллов."""
import json
import time

from .paths import EVENTS_FILE


def log_event(event_type, data):
    """Записать событие в JSONL."""
    try:
        event = {
            "ts": time.time(),
            "type": event_type,
            "data": data
        }
        with open(EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:  # noqa: BLE001
        pass
