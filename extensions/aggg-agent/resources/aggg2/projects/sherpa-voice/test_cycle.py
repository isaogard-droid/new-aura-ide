#!/usr/bin/env python3
# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Автотест полного цикла sherpa-voice БЕЗ участия человека.

Что проверяет (в порядке цепочки):
  1. синтез речи (espeak-ng) -> wav
  2. транскрипция offline-моделью (непустой текст)
  3. транскрипция streaming-моделью (непустой текст)
  4. полировка через DeepSeek
  5. меню действий с подменённым вводом: Саммари, Экспорт, Ответить
  6. экспорт MD + PDF
  7. буфер обмена (copy -> paste)

Честная пометка: речь espeak-ng — синтетическая, модель на ней смысл не
узнаёт (обучена на натуральной речи). Поэтому критерий для шагов 2-3 —
не ПУСТОЙ текст, а непустой: тест проверяет пайплайн, а не качество ASR.
Запуск: ./venv/bin/python test_cycle.py   (в проекте, не требует lock)
"""

import os
import subprocess
import sys

PROJ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJ)
WAV = "/tmp/opencode/tts_cycle.wav"
# Короткая фраза: на длинных espeak-ng генерит речь, которую offline-модель
# не распознаёт (проверено экспериментально: сигнал есть, текст пуст).
# Критерий теста — непустой результат, а не смысл (синтез ≠ натуральная речь).
PHRASE = "Меня слышишь проверка"

passed = failed = 0


def report(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  [✓] {name} {detail}")
    else:
        failed += 1
        print(f"  [✗] {name} {detail}")


def main():
    import transcribe
    from audio import load_model, read_wav, transcribe_offline, transcribe_streaming
    from export import save_text_export

    print("[1] Синтез речи (espeak-ng)")
    r = subprocess.run(
        ["espeak-ng", "-v", "ru", "-s", "120", "-w", WAV, PHRASE],
        capture_output=True)
    report("wav создан", r.returncode == 0 and os.path.isfile(WAV))

    audio = read_wav(WAV)
    print(f"    wav: {len(audio) / 16000:.1f}с")

    print("[2] Транскрипция offline")
    rec, _ = load_model(streaming=False)
    t_off = transcribe_offline(rec, audio)
    report("offline непустой", bool(t_off.strip()), f"-> {t_off!r}")

    print("[3] Транскрипция streaming")
    rec_s, _ = load_model(streaming=True)
    t_str = transcribe_streaming(rec_s, audio)
    report("streaming непустой", bool(t_str.strip()), f"-> {t_str!r}")

    print("[4] Полировка через DeepSeek")
    import deepseek_ai
    if deepseek_ai.load_key():
        polished, err = deepseek_ai.ask(deepseek_ai.PROMPTS["polish"], t_off or "тест")
        report("polish ответил", err is None and bool(polished and polished.strip()),
               f"-> {polished[:50]!r}")
    else:
        report("polish (нет ключа — пропуск)", True, "DEEPSEEK_API_KEY не задан")

    print("[5] Меню действий (мок-ввод: Задачи, Саммари, Экспорт, Ответить, Enter)")
    inputs = iter(["0", "1", "3", "2", ""])
    transcribe.input = lambda *a: next(inputs)
    orig_copy = transcribe.copy_to_clipboard
    transcribe.copy_to_clipboard = lambda t: True
    orig_ask = deepseek_ai.ask

    def fake_ask(prompt, text):
        assert "Транскрипт голосовой записи" in text, "маркер данных потерян"
        return "ответ ИИ", None
    deepseek_ai.ask = fake_ask
    try:
        transcribe.deepseek_menu("тестовая фраза для меню")
        report("меню отработало", True)
    except StopIteration:
        report("меню отработало", False, "вводов не хватило")
    except Exception as e:
        report("меню отработало", False, f"{type(e).__name__}: {e}")
    finally:
        deepseek_ai.ask = orig_ask
        transcribe.copy_to_clipboard = orig_copy

    print("[6] Экспорт MD + PDF")
    md, pdf, err = save_text_export("Экспорт из автотеста")
    report("MD создан", bool(md and os.path.isfile(md)))
    report("PDF создан", bool(pdf and os.path.isfile(pdf)),
           " (нет: шрифт/reportlab отсутствует)" if not pdf else "")
    if err:
        print(f"    примечание: {err}")

    print("[7] Буфер обмена")
    ok = transcribe.copy_to_clipboard("автотест буфера 777")
    got = None
    if ok:
        try:
            import pyperclip
            got = pyperclip.paste()
        except Exception as e:
            report("буфер", False, f"paste: {e}")
            return
    report("copy+paste совпали", ok and got == "автотест буфера 777",
           f"-> {got!r}" if got else "(буфер недоступен в этой сессии)")

    print(f"\nИТОГ: {passed} ✓ / {failed} ✗")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()


# Источник: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия — новая и ещё лучше.

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
