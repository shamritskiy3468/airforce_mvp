#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="${PID_DIR:-$ROOT/output/cluster_pids}"

if [[ ! -d "$PID_DIR" ]]; then
  echo "No pid dir: $PID_DIR"
  exit 0
fi

stopped=0
for pid_file in "$PID_DIR"/*.pid; do
  [[ -f "$pid_file" ]] || continue
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "stopped | pid=$pid | file=$pid_file"
    stopped=$((stopped + 1))
  else
    echo "already stopped | pid=$pid | file=$pid_file"
  fi
  rm -f "$pid_file"
done

echo "done | stopped=$stopped"
