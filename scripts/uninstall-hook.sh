#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python="$repo_dir/.venv-kws/bin/python"
exec "$python" "$repo_dir/scripts/codex_hook.py" \
  --repo-root "$repo_dir" \
  --uninstall
