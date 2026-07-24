#!/bin/sh
set -eu

download_model=0
install_hook=0
for argument in "$@"; do
  case "$argument" in
    --download-model) download_model=1 ;;
    --install-hook) install_hook=1 ;;
    *)
      echo "Unknown option: $argument" >&2
      exit 2
      ;;
  esac
done

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
venv="$repo_dir/.venv-kws"
python="$venv/bin/python"

if [ ! -x "$python" ]; then
  python3 -m venv "$venv"
fi

"$python" -m pip install --upgrade pip
"$python" -m pip install -r "$repo_dir/launcher/requirements.txt"

if [ "$download_model" -eq 1 ]; then
  echo "WARNING: The upstream model has no explicit model-specific license." >&2
  model_name=sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20
  model_root="$HOME/Library/Application Support/WakeForCodex/models"
  model_dir="$model_root/$model_name"
  legacy_model_dir="$HOME/Library/Application Support/CodexWakeLauncher/models/$model_name"
  model_url="https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/$model_name.tar.bz2"
  expected_hash=68447f4fbc67e70eee3a93961f36e81e98f47aef73ce7e7ca00885c6cd3616a6

  if [ -d "$legacy_model_dir" ]; then
    echo "Using existing model: $legacy_model_dir"
  elif [ ! -d "$model_dir" ]; then
    mkdir -p "$model_root"
    archive=$(mktemp "${TMPDIR:-/tmp}/codex-wake-model.XXXXXX")
    trap 'rm -f "$archive"' EXIT HUP INT TERM
    curl --fail --location "$model_url" --output "$archive"
    actual_hash=$(shasum -a 256 "$archive" | awk '{print $1}')
    if [ "$actual_hash" != "$expected_hash" ]; then
      echo "Model checksum mismatch: $actual_hash" >&2
      exit 1
    fi
    tar -xjf "$archive" -C "$model_root"
    rm -f "$archive"
    trap - EXIT HUP INT TERM
  fi
fi

if [ "$install_hook" -eq 1 ]; then
  "$python" "$repo_dir/scripts/codex_hook.py" --repo-root "$repo_dir"
  echo "Review and trust the new hook once in Codex with /hooks." >&2
fi

cd "$repo_dir"
"$python" -m launcher.doctor
