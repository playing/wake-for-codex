"""Verify the installed KWS model against its bundled reference audio."""

from __future__ import annotations

import json
import wave
from pathlib import Path

from .model_config import ModelLayout, default_model_dir
from .phrase_manifest import (
    load_phrase_manifest,
    validate_keyword_artifacts,
)

import numpy as np
import sherpa_onnx


def main() -> int:
    kws_root = Path(__file__).resolve().parent
    phrase_definitions = load_phrase_manifest(kws_root / "phrases.json")
    validate_keyword_artifacts(
        phrase_definitions,
        kws_root / "keywords_raw.txt",
        kws_root / "keywords.txt",
    )

    model = ModelLayout(default_model_dir())
    spotter = sherpa_onnx.KeywordSpotter(
        tokens=str(model.tokens),
        encoder=str(model.encoder),
        decoder=str(model.decoder),
        joiner=str(model.joiner),
        keywords_file=str(model.test_wavs / "keywords.txt"),
        num_threads=1,
        provider="cpu",
    )

    wave_path = model.test_wavs / "zh_5.wav"
    with wave.open(str(wave_path), "rb") as source:
        if source.getnchannels() != 1 or source.getsampwidth() != 2:
            raise RuntimeError("Bundled self-test wave has an unexpected format")
        sample_rate = source.getframerate()
        samples = np.frombuffer(source.readframes(source.getnframes()), np.int16)
        audio = samples.astype(np.float32) / 32768.0

    stream = spotter.create_stream()
    stream.accept_waveform(sample_rate, audio)
    stream.accept_waveform(sample_rate, np.zeros(int(sample_rate * 0.8), np.float32))
    stream.input_finished()

    detections: list[str] = []
    while spotter.is_ready(stream):
        spotter.decode_stream(stream)
        keyword = spotter.get_result(stream)
        if keyword:
            detections.append(keyword)
            spotter.reset_stream(stream)

    print(json.dumps({"detections": detections}, ensure_ascii=True))
    return 0 if detections else 1


if __name__ == "__main__":
    raise SystemExit(main())
