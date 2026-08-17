#!/usr/bin/env sh
set -eu

root_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root_dir"
export PYTHONPATH="$root_dir/src${PYTHONPATH:+:${PYTHONPATH}}"
python scripts/run_phase17_release_gate.py "$@"
