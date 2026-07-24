#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python="$repo_dir/.venv-kws/bin/python"

if [ ! -x "$python" ]; then
  echo "KWS Python runtime not found: $python" >&2
  exit 1
fi

export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1
case " $* " in
  *" --config "*) ;;
  *)
    if [ -f "$repo_dir/config.json" ]; then
      set -- --config "$repo_dir/config.json" "$@"
    fi
    ;;
esac
cd "$repo_dir"
exec "$python" -m launcher.wake_launcher "$@"
