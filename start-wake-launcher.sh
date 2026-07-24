#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
runner="$repo_dir/run-wake-launcher.sh"
runtime_dir="$HOME/Library/Application Support/WakeForCodex"
log_file="$runtime_dir/wake-launcher.jsonl"
config_file="$repo_dir/config.json"

mkdir -p "$runtime_dir"

if [ -f "$config_file" ]; then
  nohup /bin/sh "$runner" --config "$config_file" --log-file "$log_file" >/dev/null 2>&1 &
else
  nohup /bin/sh "$runner" --log-file "$log_file" >/dev/null 2>&1 &
fi
