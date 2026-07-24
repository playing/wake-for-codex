# Third-party notices

Wake for Codex does not bundle third-party model weights in this repository.

Runtime dependencies:

| Dependency | License | Purpose |
|---|---|---|
| [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) | Apache-2.0 | Local keyword spotting runtime |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | MIT | Transitive ONNX inference runtime |
| [NumPy](https://github.com/numpy/numpy) | BSD-3-Clause | Audio sample arrays |
| [python-sounddevice](https://github.com/spatialaudio/python-sounddevice) | MIT | PortAudio microphone capture |
| [pypinyin](https://github.com/mozillazg/python-pinyin) | MIT | Chinese keyword preparation |
| [SentencePiece](https://github.com/google/sentencepiece) | Apache-2.0 | Tokenization support |
| [Click](https://github.com/pallets/click) | BSD-3-Clause | sherpa-onnx CLI dependency |

## KWS model artifact

The default model is:

`sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20`

Installation scripts download the original archive directly from the
[sherpa-onnx `kws-models` release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/kws-models)
and verify:

```text
SHA-256 68447f4fbc67e70eee3a93961f36e81e98f47aef73ce7e7ca00885c6cd3616a6
```

The upstream release and model documentation do not currently include an explicit
model-specific license for these weights and accompanying vocabulary files. The
model is therefore not committed, mirrored, modified, or redistributed by this
project. Users should review the upstream terms before downloading or using it.
Upstream license clarification is being tracked in
[k2-fsa/sherpa-onnx#3760](https://github.com/k2-fsa/sherpa-onnx/issues/3760).
