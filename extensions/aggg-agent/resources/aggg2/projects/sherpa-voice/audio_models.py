#!/usr/bin/env python3
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.



# Владелец проекта: https://t.me/aidvizhenie · https://t.me/hilartem. Каждая версия неповторима, новая — ещё лучше.
"""audio_models — load_model: скачивание модели и сборка распознавателя."""
import os

import sherpa_onnx  # noqa: E402, I001 — поздний импорт намеренно: после

from audio_constants import MODEL_RATE, MODELS
from audio_hotwords import _bpe_vocab_path, _build_hotwords_file

# констант MODELS (тяжёлый пакет; места использования и так имеют fallback)

def load_model(model="offline", threads=2, streaming=None):
    """Скачивает модель (если нужно) и возвращает распознаватель.

    model: offline (zipformer int8 74MB) | streaming (29MB, онлайн) |
           gigaam (NeMo transducer 230MB — лучшее качество русского
           + hotwords).
    streaming (legacy): True -> 'streaming', False -> 'offline'
    (для совместимости со старыми вызовами).

    Скачивание защищено от обрыва сети: файлы идут во временную папку и
    переезжают на место только целиком. Неполная/битая папка модели
    удаляется и скачивается заново, а не «пропускается» при старте —
    раньше обрыв сети давал вечную поломку без самолечения."""
    if streaming is not None:
        model = "streaming" if streaming else "offline"
    if model not in MODELS:
        raise ValueError(f"неизвестная модель: {model} (есть: {', '.join(MODELS)})")
    key = model
    meta = MODELS[key]
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    model_dir = os.path.join(base, meta["dir"])
    if key == "gigaam":
        required = ["encoder.int8.onnx", "decoder.onnx", "joiner.onnx",
                    "tokens.txt"]
    else:
        required = ["tokens.txt", "encoder.int8.onnx", "decoder.onnx",
                    "joiner.int8.onnx", "bpe.model"]

    def complete():
        return os.path.isdir(model_dir) and all(
            os.path.isfile(os.path.join(model_dir, f)) for f in required)

    if not complete():
        if os.path.isdir(model_dir):
            import shutil as _sh
            print(f"[~] Папка модели неполная — удаляю и скачиваю заново "
                  f"({meta['dir']})")
            _sh.rmtree(model_dir)
        print(f"[~] Модель не найдена — скачиваю ({meta['dir']}, "
              f"~{meta.get('size', 74)}MB)…")
        os.makedirs(base, exist_ok=True)
        import tarfile
        import urllib.request

        if key == "offline":
            print(f"[~] Загрузка {meta['url']} …")
            tmp = os.path.join(base, "model.tar.bz2.part")
            try:
                # meta["url"] — константа из MODELS (хардкод), не ввод
                # meta["url"] — константа MODELS, не пользовательский ввод
                urllib.request.urlretrieve(meta["url"], tmp)  # nosemgrep
                # nosemgrep ниже: tarfile-extractall-traversal — защита
                # добавлена (member.name проверяется на выход за base)
                with tarfile.open(tmp, "r:bz2") as tf:  # nosemgrep: tarfile-extractall-traversal
                    # Защита от path traversal: не даём архиву распаковаться
                    # за пределы base (semgrep: tarfile-extractall-traversal).
                    for member in tf.getmembers():
                        member_path = os.path.normpath(
                            os.path.join(base, member.name))
                        if not member_path.startswith(
                                os.path.normpath(base) + os.sep):
                            print("[✗] Архив модели содержит опасный путь "
                                  f"({member.name!r}) — распаковка отменена.")
                            raise SystemExit(1)
                    # nosemgrep: защита добавлена выше (проверка member.name
                    # на выход за пределы base перед распаковкой)
                    tf.extractall(base)
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
            if not complete():
                print("[✗] Загрузка модели не удалась — сеть оборвалась? "
                      "Запустите снова: докачается с нуля.")
                raise SystemExit(1)
        else:
            # стриминговая / gigaam — файлы по отдельности (HF); все во
            # временную папку, на место только после полного скачивания
            files = meta.get("files") or ["encoder.int8.onnx",
                                           "decoder.onnx",
                                           "joiner.int8.onnx",
                                           "bpe.model", "tokens.txt"]
            os.makedirs(model_dir + ".part", exist_ok=True)
            try:
                for f in files:
                    url = meta["url"] + f
                    print(f"[~] {f} …")
                    # url из константы MODELS, не пользовательский ввод
                    urllib.request.urlretrieve(  # nosemgrep
                        url, os.path.join(model_dir + ".part", f))
                os.rename(model_dir + ".part", model_dir)
            except Exception as e:
                import shutil as _sh
                _sh.rmtree(model_dir + ".part", ignore_errors=True)
                print(f"[✗] Скачивание модели не завершилось ({e}). "
                      f"Запустите снова — начнётся с нуля.")
                raise SystemExit(1)  # noqa: B904 — системный выход, не цепочка
        print("[✓] Модель готова.")

    if key == "streaming":
        hw = _build_hotwords_file(model_dir)
        recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=os.path.join(model_dir, "tokens.txt"),
            encoder=os.path.join(model_dir, "encoder.int8.onnx"),
            decoder=os.path.join(model_dir, "decoder.onnx"),
            joiner=os.path.join(model_dir, "joiner.int8.onnx"),
            num_threads=threads,
            sample_rate=MODEL_RATE,
            feature_dim=80,
            model_type="zipformer2",
            decoding_method="modified_beam_search",
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=2.4,
            rule2_min_trailing_silence=1.2,
            rule3_min_utterance_length=20,
            hotwords_file=hw,
            hotwords_score=1.5,
            modeling_unit="bpe",
            bpe_vocab=_bpe_vocab_path(model_dir),
        )
        return recognizer, True
    if key == "gigaam":
        # NeMo transducer GigaAM v3: лучшее качество русского в sherpa-onnx
        # И поддерживает hotwords (в отличие от старой CTC v2) — редкие
        # слова из словаря распознаются, а полировка пишет их правильно.
        # Офлайн: распознавание после полной записи фразы.
        hw = _build_hotwords_file(model_dir)
        recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            tokens=os.path.join(model_dir, "tokens.txt"),
            encoder=os.path.join(model_dir, "encoder.int8.onnx"),
            decoder=os.path.join(model_dir, "decoder.onnx"),
            joiner=os.path.join(model_dir, "joiner.onnx"),
            num_threads=threads,
            sample_rate=MODEL_RATE,
            feature_dim=80,
            model_type="nemo_transducer",
            decoding_method="modified_beam_search",
            hotwords_file=hw,
            hotwords_score=1.5,
        )
        return recognizer, False
    hw = _build_hotwords_file(model_dir)
    recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
        tokens=os.path.join(model_dir, "tokens.txt"),
        encoder=os.path.join(model_dir, "encoder.int8.onnx"),
        decoder=os.path.join(model_dir, "decoder.onnx"),
        joiner=os.path.join(model_dir, "joiner.int8.onnx"),
        num_threads=threads,
        sample_rate=MODEL_RATE,
        feature_dim=80,
        decoding_method="modified_beam_search",
        hotwords_file=hw,
        hotwords_score=1.5,
        modeling_unit="bpe",
        bpe_vocab=_bpe_vocab_path(model_dir),
    )
    return recognizer, False

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
