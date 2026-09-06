#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


"""chat.mix — подмешка (копилка готовых фрагментов).
Вынесено из chat.py механически (verbatim), 15.08.2026 — гейт god-файлов."""
import ui_utils
from store import load_mix, save_mix


def _mix_menu():
    """Подменю подмешки: показать / изменить / вкл-выкл / очистить.
    Одно действие — один заход: после кнопки сразу возврат в меню действий
    (раньше подменю показывалось снова и снова — «много раз»).
    Изменения пишутся в mix.txt и переживают перезапуски. Файл читается
    заново на каждом шаге: правки, сделанные вручную в редакторе
    (например, многострочный текст), подхватываются сразу."""
    while True:
        enabled, mix_text = load_mix()
        status = "вкл" if enabled else "выкл"
        preview_line = mix_text.split("\n")[0] if mix_text.strip() else ""
        if len(preview_line) > 40:
            preview_line = preview_line[:40] + "…"
        preview = f"«{preview_line}»" if preview_line else "(пусто)"
        if mix_text.strip() and "\n" in mix_text:
            extra = mix_text.count("\n")
            preview += f" · ещё {extra} строк" if extra > 1 else " · ещё 1 строка"
        try:
            sub = input(f"\n[ai] Подмешка ({status}): {preview} — файл: {ui_utils.MIX_FILE}\n"
                        f"[ai] [1] 📖 Показать  [2] ✏️ Изменить  [3] 🔄 Вкл/выкл  "
                        f"[4] 🗑 Очистить  [Enter] назад\n    > ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not sub:
            return
        if sub == "1":
            if mix_text.strip():
                print(f"[mix] Начало:\n{mix_text}\n[mix] Конец.")
            else:
                print("[i] Подмешка пуста — впишите текст (пункт 2).")
            return
        elif sub == "2":
            print("[i] Многострочный ввод: Enter — новая строка, пустая строка — закончить.")
            print("[i] (пусто сразу = оставить как было; файл для ручной правки: "
                  + ui_utils.MIX_FILE + ")")
            lines = []
            while True:
                try:
                    line = input("    > ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not line:
                    break
                lines.append(line)
            if not lines:
                print("[i] Оставил как было.")
            else:
                mix_text = "\n".join(lines)
                enabled = True
                if save_mix(enabled, mix_text):
                    print("[✓] Подмешка сохранена и включена.")
            return
        elif sub == "3":
            if not mix_text.strip():
                print("[i] Сначала впишите текст (пункт 2) — пустую подмешку включать нечего.")
                continue
            enabled = not enabled
            if save_mix(enabled, mix_text):
                print(f"[✓] Подмешка {'включена' if enabled else 'выключена'}.")
            return
        elif sub == "4":
            enabled = False
            mix_text = ""
            if save_mix(False, ""):
                print("[✓] Подмешка очищена и выключена.")
            return
        else:
            print("[i] Не понял выбор — Enter = назад.")


# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
