# Platform upstream risk scan

Date: 2026-07-25

Scope: a bounded primary-source review of the upstream contracts that Wake for
Codex currently depends on. This is not a proposal to expand the product beyond
local wake word → microphone release → configured Voice hotkey → listening
resume.

## Verified facts

### sherpa-onnx runtime and KWS model

- The `sherpa-onnx` source repository is Apache-2.0, but its own KWS
  documentation separately tells users to check the license of the selected
  model. The source-code license therefore should not be treated as an explicit
  license grant for every pretrained model artifact
  ([repository license](https://github.com/k2-fsa/sherpa-onnx/blob/master/LICENSE),
  [KWS model-license note](https://k2-fsa.github.io/sherpa/onnx/kws/apk.html)).
- Upstream documents the exact
  `sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20` archive and download URL used
  by this project. The documented archive listing contains model, vocabulary,
  and test-audio files but no model-specific license
  ([model documentation](https://k2-fsa.github.io/sherpa/onnx/kws/pretrained_models/index.html#sherpa-onnx-kws-zipformer-zh-en-3m-2025-12-20-chinese-english)).
- In this scan, the archive downloaded directly from the upstream GitHub
  Release had SHA-256
  `68447f4fbc67e70eee3a93961f36e81e98f47aef73ce7e7ca00885c6cd3616a6`,
  matching both the project's pinned value and the digest exposed by the
  [GitHub Release API](https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/kws-models).
  Its 26 archive entries contained no `LICENSE`, `LICENCE`, `COPYING`, or
  `NOTICE` file.
- The upstream clarification request covering this exact bilingual model is
  still open and has no maintainer response as of the scan date
  ([k2-fsa/sherpa-onnx#3760](https://github.com/k2-fsa/sherpa-onnx/issues/3760)).
  Consequently, commercial-use, modification, and redistribution permissions
  for the weights and accompanying vocabulary files remain unverified.

### sherpa-onnx, sounddevice, and PortAudio platform constraints

- Upstream's CPU-only Python installation path lists macOS `x64` and `arm64`,
  and Windows `x64` and `x86`. It does not list Windows ARM64 for the Python
  wheel path used by this project
  ([sherpa-onnx Python installation](https://k2-fsa.github.io/sherpa/onnx/python/install.html)).
  Upstream has separate native Windows ARM64 libraries/build instructions, but
  that is not the same as a supported `pip install sherpa-onnx==1.13.4` path
  ([Windows ARM64 native build](https://k2-fsa.github.io/sherpa/onnx/install/windows/generated/build_cpu/windows_arm64_cpu_build.html)).
- At the start of this scan, the project pinned `numpy==2.5.1`, whose PyPI
  metadata requires Python `>=3.12`
  ([NumPy 2.5.1 PyPI JSON](https://pypi.org/pypi/numpy/2.5.1/json)).
  This conflicts with the README's “Python 3.11 or newer” claim and the CI
  matrix's Python 3.11 row
  ([requirements](../../launcher/requirements.txt),
  [CI workflow](../../.github/workflows/ci.yml),
  [README](../../README.md)).
- The initial CI workflow did not install `launcher/requirements.txt`; it
  compiled source and ran tests whose import paths avoided the runtime
  audio/KWS dependencies. Therefore the green Python 3.11 jobs did not verify
  that a Python 3.11 user could install or start the pinned runtime. For
  comparison, NumPy 2.4.2 advertises Python `>=3.11`
  ([NumPy 2.4.2 PyPI JSON](https://pypi.org/pypi/numpy/2.4.2/json)); this is
  evidence that a compatible pin is possible, not a recommendation of that
  exact version.
- `sounddevice` 0.5.5 installs PortAudio automatically when installed with
  `pip` on macOS or Windows. A package-manager or custom PortAudio library can
  override that bundled library, so the actually loaded backend is partly an
  environment property
  ([sounddevice installation](https://python-sounddevice.readthedocs.io/en/0.5.5/installation.html)).
- PortAudio stream sharing is host-API dependent. The `sounddevice` contract
  says portable applications should assume a device can be used by at most one
  stream at a time
  ([stream API](https://python-sounddevice.readthedocs.io/en/0.5.5/api/streams.html)).
  Releasing Wake for Codex's input stream before triggering Voice is therefore
  the correct portable boundary.
- The PortAudio callback runs at high or real-time priority. Its documented
  constraints say not to allocate memory or call operations that may block or
  take unpredictable time. The same documentation recommends `blocksize=0`
  unless an algorithm requires fixed-size callback blocks
  ([callback and block-size contract](https://python-sounddevice.readthedocs.io/en/0.5.5/api/streams.html)).
- `sounddevice` exposes `check_input_settings()` specifically to validate a
  device, channel count, sample type, and sample rate, raising when the
  combination is unsupported
  ([official module API](https://python-sounddevice.readthedocs.io/en/0.5.5/api/checking-hardware.html#sounddevice.check_input_settings)).

### Windows microphone lifecycle signal

- Microsoft's supported user-facing contract is that Windows shows microphone
  use in the system tray and exposes a seven-day resource-access history in
  Settings
  ([Windows privacy controls](https://learn.microsoft.com/en-us/windows/security/book/privacy-controls)).
- This review found no official Microsoft API or registry contract defining
  `HKCU\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone`,
  `LastUsedTimeStart`, `LastUsedTimeStop`, their update timing, or application
  key naming as a stable programmatic interface. Microsoft documents
  microphone privacy policy controls, but not those usage-history values
  ([Privacy Policy CSP](https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-privacy)).
- Wake for Codex currently depends on those undocumented values and an
  `OpenAI.Codex_` registry-key prefix. This is observable Windows behavior, not
  a Microsoft-supported lifecycle API.

### macOS CoreAudio and synthetic hotkey signal

- Apple currently publishes
  `kAudioDevicePropertyDeviceIsRunningSomewhere` as a CoreAudio property
  selector for macOS and Mac Catalyst, without a deprecation marker
  ([Apple API reference](https://developer.apple.com/documentation/coreaudio/kaudiodevicepropertydeviceisrunningsomewhere)).
  It is a device-level “running somewhere” signal: it reports that the audio
  device is running in at least one process, not which application owns the
  input.
- Apple currently publishes `CGEvent` keyboard-event creation and event
  posting APIs without deprecation markers
  ([keyboard-event creation](https://developer.apple.com/documentation/coregraphics/cgevent/init%28keyboardeventsource%3Avirtualkey%3Akeydown%3A%29),
  [event posting](https://developer.apple.com/documentation/coregraphics/cgevent/post%28tap%3A%29)).
- `AXIsProcessTrusted()` reports whether the current process is a trusted
  Accessibility client
  ([Apple API reference](https://developer.apple.com/documentation/applicationservices/1460720-axisprocesstrusted)).
  Apple Developer Technical Support now describes posting `CGEvent`s as a
  distinct `PostEvent` TCC privilege and points developers to
  `CGPreflightPostEventAccess` and `CGRequestPostEventAccess`; the permission
  still appears under Accessibility in System Settings
  ([Apple DTS answer](https://developer.apple.com/forums/thread/789896)).
  Therefore `AXIsProcessTrusted()` is not the most precise current preflight
  for the action Wake for Codex performs.
- Apple requires explicit user authorization when a third-party process
  controls the Mac through Accessibility-related capabilities
  ([Apple Support](https://support.apple.com/guide/mac-help/mh43185/mac)).

### Codex Hook and Voice shortcut

- OpenAI publicly documents user-level `~/.codex/hooks.json`,
  `SessionStart`, `commandWindows`, hook trust review, and the
  `startup|resume|clear|compact` matcher values. The project's optional
  `SessionStart` hook using `startup|resume`, an absolute launcher path, and a
  Windows override conforms to that published shape
  ([OpenAI Codex Hooks](https://learn.chatgpt.com/docs/hooks.md)).
- OpenAI publicly documents the user-configured
  **Settings > Voice > Voice chat hotkey**
  ([OpenAI ChatGPT Voice](https://learn.chatgpt.com/docs/features/voice.md)).
  The documented integration seam is a user-selected shortcut; Wake for Codex
  does not need to inspect or mutate Codex settings.

## Inferences

- Direct upstream download plus a pinned SHA-256 materially reduces artifact
  substitution risk, but it does not resolve copyright or redistribution
  permission. Continuing to exclude the model from the repository and Release
  assets is the narrowest defensible posture while the license is unknown.
- The current Python 3.11 support claim is a false positive at the installation
  boundary: source-only tests pass, while the exact dependency set cannot be
  resolved on 3.11 because of the NumPy `Requires-Python` constraint.
- The current audio callback calls `indata[:, 0].copy()` and performs queue
  operations. The copy is an allocation inside the real-time callback, contrary
  to PortAudio's general callback guidance. The bounded queue prevents
  unbounded memory growth and drops old audio under pressure, so this is a
  potential glitch/false-negative risk under load rather than evidence of a
  current correctness failure.
- `doctor` currently confirms that an input device can be queried, but does not
  validate the launcher's exact `16 kHz / mono / float32` stream format.
  `sd.check_input_settings(...)` would close that diagnostic gap without
  opening the microphone or adding a subsystem.
- Windows lifecycle detection can break after a Codex packaging identity
  change, a Windows registry-layout change, privacy-history cleanup, or on a
  machine where Codex has never yet produced a matching entry. Because no
  supported Microsoft contract exists, more unit tests around the current
  registry shape cannot turn the heuristic into a stable API.
- On macOS, any process using the default input device can satisfy
  `DeviceIsRunningSomewhere`; a device switch can also change what “default
  input” means during polling. The current pre-launch “wait until inactive”
  check is conservative and prevents an already-busy device from being
  misattributed to Codex, but the signal still cannot prove Codex ownership.
- The current Codex integration is appropriately shallow: both the hook and
  hotkey are documented user-facing seams, while microphone lifecycle remains
  an OS heuristic. Adding Codex process inspection or UI automation would not
  make either OS signal an official Voice-session API.

## Unknowns

- The license, commercial-use rights, modification rights, redistribution
  rights, and training-data provenance of
  `sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20` remain unknown.
- Microsoft does not publicly commit to the current CapabilityAccessManager
  usage-history registry schema, application-key prefix, timestamp units, or
  update latency.
- Apple documents the CoreAudio selector but does not promise that every
  built-in, USB, Bluetooth, aggregate, or virtual input device reports
  `DeviceIsRunningSomewhere` with identical timing or reliability.
- It is not established from public Apple documentation that
  `AXIsProcessTrusted()` alone will remain a sufficient preflight for event
  posting on every supported macOS release. The current specific API is the
  PostEvent access check.
- This scan found no public OpenAI API for reading the configured Voice hotkey
  or receiving a machine-readable Voice-session started/ended event. Absence
  from the current public documentation is not proof that no internal mechanism
  exists; it means the project should not depend on one.

## Lightweight implications

1. **Keep the model policy unchanged for the v0.2.0 Release.** Do not commit,
   mirror, modify, or attach the model to GitHub Releases. Keep the direct
   upstream URL, pinned SHA-256, warning, and upstream clarification link.
2. **Resolve the Python 3.11 contract before calling the matrix green.** Choose
   one small, explicit path: pin a NumPy release compatible with Python 3.11,
   or drop Python 3.11 and align the README and CI matrix to Python 3.12+.
   Whichever path is chosen, make at least one CI path install the exact runtime
   requirements so dependency compatibility is actually exercised.
   **v0.2.0 status:** resolved with the compatible NumPy 2.4.2 pin and runtime
   dependency installation in every supported CI combination.
3. **Tighten `doctor`, not the architecture.** Add a read-only
   `sd.check_input_settings(device, channels=1, dtype="float32",
   samplerate=16000)` check. Report Windows ARM64 as unsupported by the current
   pinned Python-wheel install path instead of attempting a native-build
   subsystem.
4. **Label Windows lifecycle detection as a 0.x compatibility heuristic.** Preserve its
   bounded timeouts and explicit failure. Improve the error for “no matching
   Codex microphone history” and include one manual smoke check after material
   Codex Desktop or Windows updates; do not build a registry abstraction layer.
5. **Use the precise macOS permission preflight when making the next small
   platform patch.** Prefer `CGPreflightPostEventAccess` where available and
   keep the existing user-granted permission flow. Retain `cooldown` as the
   simple fallback for unreliable CoreAudio device state.
6. **Treat callback tuning as evidence-driven.** Existing `audio_status`
   logging already exposes overflow/underflow symptoms. Only if field evidence
   shows dropped callbacks, test `blocksize=0` and a lower-allocation handoff;
   avoid introducing a new audio engine.
7. **Keep Codex integration optional and user-owned.** The existing Hook and
   configurable hotkey match public OpenAI documentation. Do not add setting
   discovery, Voice UI automation, or additional lifecycle hooks.
