# Принадлежит каналу https://t.me/aidvizhenie · админ h-i-l-artem · гиг t,me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

"""Парсинг ответов моделей мультимодельного судейства.

Вынесено из multimodel_judge.py (механическая резка god-файла, код дословно):
extract_json_object, parse_judge_questions.
"""
import json


def extract_json_object(text: str) -> str | None:
    """Вытащить ПЕРВЫЙ JSON-объект из текста балансным счётом скобок.

    В отличие от среза по rfind('}'): корректно работает, когда внутри JSON
    (в строках) есть фигурные скобки — например, инструкции воркерам вида
    'верни {"issues": [...]}'. Строки и экранирование учитываются.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def parse_judge_questions(text: str, reviewers: list[str]) -> tuple[list[dict], bool]:
    """Разобрать JSON-ответ судьи с вопросами: {"questions": [...]}.

    Возвращает (вопросы, ok). ok=False — ответ не распарсился (мусор/не JSON):
    вопросы считаем пустыми, раунд вопросов пропускаем. Вопросы к моделям,
    которых нет в панели, отбрасываем.
    """
    obj = extract_json_object(text)
    if obj is None:
        return [], False
    try:
        data = json.loads(obj)
    except json.JSONDecodeError:
        return [], False
    raw = data.get("questions")
    if not isinstance(raw, list):
        return [], False
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        model = str(item.get("model", "")).strip()
        question = str(item.get("question", "")).strip()
        if model in reviewers and question:
            out.append({"model": model, "question": question})
    return out, True
