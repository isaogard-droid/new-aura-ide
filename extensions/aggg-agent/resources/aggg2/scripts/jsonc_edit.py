"""jsonc_edit — хирургическая правка JSON/JSONC-конфигов с сохранением
комментариев, чужих записей и форматирования.

Паттерн индустрии: microsoft/node-jsonc-parser (им VS Code правит свои
settings.json) — текстовые edits по оффсетам вместо переписывания файла.
Правки считаются в координатах ИСХОДНОГО текста и применяются с конца.

Подробности и грабли: skills/jsonc-surgical-edit (канон AGGG2.0),
research.db id=285/286.

Использование:
    from jsonc_edit import load_jsonc, _edit_mcp_section, write_json
    new = _edit_mcp_section(raw, servers, known_names, clean_stale=True)
"""
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

import json
import os


def _parse_jsonc(text):
    """Парсит JSONC-текст (JSON с // и /* */ комментариями) в объект."""
    # UTF-8 BOM (Windows-файлы) ломает json.loads — снимаем на входе
    # (багрепорт v2.4: opencode.json с BOM → молчаливая потеря конфига).
    if text.startswith("\ufeff"):
        text = text.removeprefix("\ufeff")
    out, i, n = [], 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\":
                out.append(text[i + 1] if i + 1 < n else "")
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = j if j != -1 else n
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = (j + 2) if j != -1 else n
            continue
        out.append(c)
        i += 1
    return json.loads("".join(out))


def load_jsonc(path):
    """Парсит JSONC-файл (JSON с комментариями). utf-8-sig: снимает BOM,
    которым помечены конфиги, сохранённые Windows-инструментами (иначе
    json.loads падает на "\ufeff" — багрепорт v2.4 BUG-3)."""
    raw = open(path, encoding="utf-8-sig").read()  # noqa: SIM115 — стиль CLI-скриптов
    return _parse_jsonc(raw)




# Разработано для https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия уникальна, дальше — ещё лучше.
def write_json(path, data):
    # mkdir parents: конфиги новых харнесов (~/.cursor/, ~/.omp/agent/) —
    # каталогов ещё нет, open упал бы (грабля 14.08, ~/.cursor/mcp.json).
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


# --- Точечная правка JSONC (паттерн jsonc-parser от Microsoft: текстовые
# edits по оффсетам вместо переписывания файла — комментарии и формат вне
# правимого участка сохраняются; так VS Code правит свои settings.json). ---


def _skip_string(text, i):
    """i на открывающей кавычке — вернуть индекс ПОСЛЕ закрывающей."""
    j = i + 1
    while j < len(text):
        if text[j] == "\\":
            j += 2
            continue
        if text[j] == '"':
            return j + 1
        j += 1
    return j


def _skip_comments(text, i):
    """Пропускает // и /* */, если они начинаются в i. Возвращает новый i."""
    n = len(text)
    if i + 1 < n and text[i] == "/" and text[i + 1] == "/":
        j = text.find("\n", i)
        return j if j != -1 else n
    if i + 1 < n and text[i] == "/" and text[i + 1] == "*":
        j = text.find("*/", i + 2)
        return (j + 2) if j != -1 else n
    return i

# Источник: тг t.me/aidvizhenie | t,me/hilartem | aidvizh_hub — канал и гиг в ТГ
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


def _skip_value(text, i):
    """i на открывающей { или [ — вернуть индекс ПОСЛЕ парной скобки.
    Строки и комментарии внутри не считаются скобками."""
    depth, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i = _skip_string(text, i)
            continue
        if c == "/":
            j = _skip_comments(text, i)
            if j != i:
                i = j
                continue
        if c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


def _jsonc_key_map(text, want_depth, base=0, limit=None):
    """Карта ключей: {key: (key_start, value_start, value_end)}.

    want_depth — глубина скобок, на которой лежат ключи: 1 для корневого
    объекта (внутри первой {), 0 для секции mcp (base после её {).
    Строки и комментарии игнорируются. Возвращает также (root_end):
    кортеж (map, root_end), где root_end — индекс после закрывающей
    скобки корня (для вставки секции, если её нет)."""
    out, n = {}, limit if limit is not None else len(text)
    depth, root_end = 0, None
    i = base
    while i < n:
        c = text[i]
        if c == '"':
            # строка: ключ на нужной глубине или обычное значение
            key = text[i + 1:_skip_string(text, i) - 1]
            j = _skip_string(text, i)
            k = j
            while k < n and text[k] in " \t\r\n":
                k += 1
            if depth == want_depth and k < n and text[k] == ":":
                v = k + 1
                while v < n and text[v] in " \t\r\n":
                    v += 1
                if v < n and text[v] in "{[":
                    vend = _skip_value(text, v)
                elif v < n and text[v] == '"':
                    vend = _skip_string(text, v)
                else:
                    vend = v
                    while vend < n and text[vend] not in ",}\n":
                        vend += 1
                out[key] = (i, v, vend)
                i = vend
                continue
            i = j
            continue
        if c == "/":
            j = _skip_comments(text, i)
            if j != i:
                i = j
                continue
        if c == "{":
            if depth == 0:
                root_end = None  # не финальная скобка
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                root_end = i + 1
        i += 1
    return out, root_end


def _line_indent(text, pos):
    """ВЕДУЩИЕ пробелы строки, в которой находится pos."""
    line_start = text.rfind("\n", 0, pos) + 1
    ws = text[line_start:pos]
    return ws[:len(ws) - len(ws.lstrip())]





def _opencode_entry(command, environment=None):
    """Запись local-сервера для конфига opencode. ВАЖНО: поле env-переменных
    в opencode называется `environment` (не `env` — тот silently игнорируется
    схемой, opencode issues #26332/#39135)."""
    entry = {"type": "local", "command": list(command), "enabled": True}
    if environment:
        entry["environment"] = dict(environment)
    return entry


def _server_value(command, indent, environment=None):
    """Только значение '{...}' для ЗАМЕНЫ существующей записи: первая
    строка без отступа (продолжает строку ключа), остальные на
    indent+2/indent+4..."""
    dump = json.dumps(_opencode_entry(command, environment), indent=2,
                      ensure_ascii=False)
    lines = dump.splitlines()
    out = [lines[0]]
    for ln in lines[1:]:
        lead = len(ln) - len(ln.lstrip())
        out.append(" " * (indent + lead) + ln.strip())
    return "\n".join(out)


def _server_block(name, command, indent, environment=None):
    """Полная запись '"name": {...}' для ВСТАВКИ: ключ на отступе indent."""
    return " " * indent + f'"{name}": ' + _server_value(command, indent,
                                                         environment)


def _mcp_section_text(servers, mcp_indent, indent_unit=2):
    """Текст серверов для секции mcp: отступ mcp_indent для ключей,
    mcp_indent+indent_unit для содержимого."""
    srv_indent = mcp_indent + indent_unit
    parts = [_server_block(name, s["command"], srv_indent, s.get("env"))
             for name, s in servers.items()]
    body = (",\n".join(parts) + "\n") if parts else ""
    return (f"{' ' * mcp_indent}\"mcp\": {{\n{body}"
            f"{' ' * mcp_indent}}}")


def _edit_mcp_section(raw, servers, known_names, clean_stale=False):
    """Точечная правка секции "mcp" в JSONC-тексте: известные серверы
    добавляются/обновляются/удаляются, чужие записи и ВСЕ комментарии
    вне правимых блоков сохраняются (паттерн jsonc-parser, VS Code).

    clean_stale=True (полная установка без --server) — устаревшие
    известные серверы удаляются. False (частичная) — известные серверы,
    которых нет в доставке, НЕ трогаем (грабля: агентский setup_mcp.sh
    вычищал core-серверы из opencode.jsonc).

    Правки считаются в координатах ИСХОДНОГО текста и применяются с конца,
    поэтому не пересекаются и не портят друг друга.

    Возвращает новый текст или None, если файл не похож на JSON."""
    try:
        top, root_end = _jsonc_key_map(raw, 1)
    except Exception:
        return None
    if root_end is None:
        return None

    if "mcp" not in top:
        # секции нет — создать перед закрывающей скобкой корня
        first_key = next(iter(top), None)
        mcp_indent = len(_line_indent(raw, top[first_key][0])) \
            if first_key else 2
        block = _mcp_section_text(servers, mcp_indent)
        insert_at = root_end - 1
        while insert_at > 1 and raw[insert_at - 1] in " \t\r\n":
            insert_at -= 1
        comma = ",\n" if top else "\n"
        tail = raw[insert_at:]
        return (raw[:insert_at] + comma + block
                + ("" if tail.startswith("\n") else "\n") + tail)

    mcp_key, mcp_vs, mcp_ve = top["mcp"]
    inner, _ = _jsonc_key_map(raw, 0, base=mcp_vs + 1, limit=mcp_ve - 1)
    edits = []  # (start, end, replacement) — применяются с конца

    # 1) удалить устаревшие известные серверы (только при полной установке)
    if clean_stale:
        for name in list(inner):
            if name not in known_names or name in servers:
                continue
            key_start, vs, ve = inner[name]
            s = key_start
            while s > 0 and raw[s - 1] in " \t\r\n":
                s -= 1
            if s > 0 and raw[s - 1] == ",":
                # от запятой предыдущего элемента до конца значения —
                # запятая и перенос следующего остаются на месте
                edits.append((s - 1, ve, ""))
            else:
                # первый элемент: от ключа, забрать ws и запятую после
                e = ve
                while e < len(raw) and raw[e] in " \t\r\n":
                    e += 1
                if e < len(raw) and raw[e] == ",":
                    e += 1
                    while e < len(raw) and raw[e] in " \t\r\n":
                        e += 1
                edits.append((key_start, e, ""))

    # 2) обновить существующие
    srv_indent = len(_line_indent(raw, mcp_key)) + 2
    for name, s in servers.items():
        if name not in inner:
            continue
        _, vs, ve = inner[name]
        edits.append((vs, ve, _server_value(s["command"], srv_indent,
                                            s.get("env"))))

    # 3) вставить отсутствующие одной правкой: ws-хвост секции
    # (между последним элементом и "}") заменяется на запятую + блоки
    new_names = [name for name in servers if name not in inner]
    if new_names:
        insert_at = mcp_ve - 1
        while insert_at > mcp_vs + 1 and raw[insert_at - 1] in " \t\r\n":
            insert_at -= 1
        comma = ",\n" if raw[mcp_vs + 1:insert_at].strip() else "\n"
        blocks = [_server_block(name, servers[name]["command"], srv_indent,
                                servers[name].get("env"))
                  for name in new_names]
        indent_mcp = " " * len(_line_indent(raw, mcp_key))
        edits.append((insert_at, mcp_ve - 1,
                      comma + ",\n".join(blocks) + "\n" + indent_mcp))

    for start, end, repl in sorted(edits, key=lambda e: e[0], reverse=True):
        raw = raw[:start] + repl + raw[end:]
    return raw

# Принадлежит: t.me/aidvizhenie · t.me/hilartem · t.me/aidvizh_hub — ищи в Телеграме
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
