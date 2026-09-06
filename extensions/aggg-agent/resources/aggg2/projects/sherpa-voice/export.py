#!/usr/bin/env python3
# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.




# Каналы-владельцы: https://t.me/aidvizhenie · https://t.me/hilartem. Версия неповторима, новая — ещё лучше.
"""Экспорт транскриптов в MD/PDF.

Вынесено из transcribe.py (монолит >1200 строк): экспорт ни от чего в
транскрайбере не зависит, только от os/time и reportlab (опционально).
# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""
import os
import time

EXPORT_DIR = os.path.expanduser("~/sherpa-voice/exports")

# TTF с кириллицей для PDF. Пути в порядке приоритета: Linux (Liberation
# Sans, метрики Arial) и Windows (Arial). Если ни одного нет — PDF не
# соберётся, сохранится только MD (честно сообщим).
PDF_FONTS = [
    "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf",
    "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def save_text_export(text, summary=None, answer=None, review=None):
    """Сохраняет транскрипт в MD и PDF (если reportlab и шрифт на месте).

    Сгенерированные в меню саммари, ответ и кодинг-промт (ревью промпта
    полировки) добавляются в тот же документ, в порядке: транскрипция →
    саммари → ответ → кодинг-промт (какие есть).
    Возвращает (md_path, pdf_path_или_None, ошибка_или_None). PDF-сбой не
    роняет экспорт: MD сохраняется всегда."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    md_path = os.path.join(EXPORT_DIR, f"transcript_{stamp}.md")
    sections = [("Запись от " + stamp, text)]
    if summary:
        sections.append(("Саммари", summary))
    if answer:
        sections.append(("Ответ", answer))
    if review:
        sections.append(("Кодинг-промт", review))
    with open(md_path, "w", encoding="utf-8") as f:
        for i, (title, body) in enumerate(sections):
            if i:
                f.write("\n")
            f.write(f"{'## ' if i else '# '}{title}\n\n{body}\n")

    fonts = [p for p in PDF_FONTS if os.path.isfile(p)]
    if len(fonts) < 2:
        return md_path, None, None
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate

        def esc(s):
            return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                     .replace("\n", "<br/>"))

        pdf_path = os.path.join(EXPORT_DIR, f"transcript_{stamp}.pdf")
        pdfmetrics.registerFont(TTFont("Rus", fonts[0]))
        pdfmetrics.registerFont(TTFont("Rus-Bold", fonts[1]))
        style = ParagraphStyle("rus", fontName="Rus", fontSize=12, leading=17)
        head = ParagraphStyle("rus-head", fontName="Rus-Bold", fontSize=14,
                              leading=18, spaceBefore=12, spaceAfter=4)
        flow = []
        for _, (title, body) in enumerate(sections):
            flow.append(Paragraph(esc(title), head))
            flow.append(Paragraph(esc(body), style))
        SimpleDocTemplate(pdf_path, pagesize=A4).build(flow)
        return md_path, pdf_path, None
    except Exception as e:
        return md_path, None, f"PDF не собран ({type(e).__name__}: {e}) — сохранён только MD"

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
