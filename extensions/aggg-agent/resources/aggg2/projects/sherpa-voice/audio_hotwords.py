#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.



# Владелец проекта: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия неповторима, новая — ещё лучше.
"""audio_hotwords — hotwords (contextual biasing) для transducer-моделей."""
import os

from audio_constants import HOTWORDS_BASE, HOTWORDS_CACHE


def _seed_hotwords_base():
    """Merge базовых hotwords проекта в кэш-словарь (идемпотентно).

    На новой машине кэш пуст — база (hotwords_base.txt) даёт стартовый
    словарь терминов проекта; персональные коррекции (hotwords.py)
    дополняют поверх. Дубли не создаются: добавляются только
    отсутствующие строки."""
    if not os.path.isfile(HOTWORDS_BASE):
        return
    raw_path = os.path.join(HOTWORDS_CACHE, "hotwords_input.txt")
    existing = set()
    if os.path.isfile(raw_path):
        with open(raw_path, encoding="utf-8") as f:
            existing = {ln.strip() for ln in f if ln.strip()}
    added = []
    with open(HOTWORDS_BASE, encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if w and not w.startswith("#") and w not in existing:
                existing.add(w)
                added.append(w)
    if not added:
        return
    os.makedirs(HOTWORDS_CACHE, exist_ok=True)
    with open(raw_path, "a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(added) + "\n")
    print(f"[hotwords] база проекта: +{len(added)} слов в словарь")


def _bpe_vocab_path(model_dir):
    """bpe.vocab рядом с моделью; экспортируется из bpe.model один раз."""
    src = os.path.join(model_dir, "bpe.model")
    dst = os.path.join(model_dir, "bpe.vocab")
    if os.path.isfile(dst):
        return dst
    if not os.path.isfile(src):
        return ""
    try:
        import sherpa_onnx as _so
        if not hasattr(_so, "text2token"):
            return ""
        # экспорт vocab: все токены из tokens.txt, преобразованные
        # sentencepiece-эквивалентом sherpa (text2token умеет bpe-кодирование)
        with open(os.path.join(model_dir, "tokens.txt"), encoding="utf-8") as f:
            toks = [ln.strip() for ln in f if ln.strip()]
        # берём только символьные токены bpe (не спецтокены <blk> и т.п.)
        vocab = [t for t in toks if not t.startswith("<") and len(t) > 1]
        if not vocab:
            return ""
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(vocab) + "\n")
        print(f"[hotwords] bpe.vocab экспортирован ({len(vocab)} токенов)")
        return dst
    except Exception as e:
        print(f"[hotwords] bpe.vocab не создан ({e})")
        return ""


def _build_hotwords_file(model_dir):
    """Собирает hotwords.txt (токенизированный) из hotwords_input.txt
    (сырые слова, верхний регистр) через sherpa text2token."""
    _seed_hotwords_base()
    raw = os.path.join(HOTWORDS_CACHE, "hotwords_input.txt")
    dst = os.path.join(HOTWORDS_CACHE, "hotwords.txt")
    if not os.path.isfile(raw):
        return ""
    try:
        import sherpa_onnx as _so
        bpe = os.path.join(model_dir, "bpe.model")
        toks = os.path.join(model_dir, "tokens.txt")
        with open(raw, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        if not lines:
            return ""
        out_lines = []
        for line in lines:
            # hotwords: слово + опциональный скор
            parts = line.split()
            word = parts[0]
            score = " " + " ".join(parts[1:]) if len(parts) > 1 else ""
            if os.path.isfile(bpe):
                encoded = _so.text2token(
                    word, tokens=toks, tokens_type="bpe", bpe_model=bpe)
                # text2token возвращает [[tok1], [tok2], ...] — склеиваем
                if encoded:
                    flat = " ".join("".join(ch) for ch in encoded)
                    if flat.strip() and flat.strip() != "▁":
                        out_lines.append(flat + score)
            else:
                # Символьная модель (GigaAM nemo_transducer): токенизация
                # посимвольно через tokens.txt (символ → id). text2token
                # тяжёлый (тянет pypinyin для cjkchar) — свой разбор легче.
                # Только однословные hotwords: фразы с пробелами («опен код»)
                # склеиваются в слитную последовательность, которой в речи
                # нет, и создают шум в beam search (проверено 08.2026).
                # Многословные термины исправляет полировка через vocab.txt.
                if len(parts) > 1 or " " in word:
                    continue
                tok_ids = {}
                try:
                    with open(toks, encoding="utf-8") as tf:
                        for ln in tf:
                            p = ln.split()
                            if len(p) == 2:
                                tok_ids[p[0]] = p[1]
                except OSError:
                    tok_ids = {}
                chars = [ch for ch in word if ch in tok_ids]
                if chars:
                    out_lines.append(" ".join(chars) + score)
        os.makedirs(HOTWORDS_CACHE, exist_ok=True)
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(out_lines) + "\n")
        return dst
    except Exception as e:
        print(f"[hotwords] токенизация не удалась ({e})")
        return ""

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
