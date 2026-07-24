#!/bin/sh
set -eu

lock_file="$HOME/Library/Application Support/WakeForCodex/wake-launcher.lock"

if [ ! -f "$lock_file" ]; then
  echo "launcher=not_running"
  exit 0
fi

pid=$(sed -n '1p' "$lock_file")
case "$pid" in
  ''|*[!0-9]*)
    echo "Invalid launcher lock file: $lock_file" >&2
    exit 1
    ;;
esac

command=$(ps -p "$pid" -o command= 2>/dev/null || true)
case "$command" in
  *"launcher.wake_launcher"*)
    kill -TERM "$pid"
    echo "launcher=stopped pid=$pid"
    ;;
  "")
    echo "launcher=not_running"
    ;;
  *)
    echo "Refusing to stop unrelated process $pid: $command" >&2
    exit 1
    ;;
esac
