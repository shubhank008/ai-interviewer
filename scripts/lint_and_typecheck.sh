#!/usr/bin/env sh
set -eu

export PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}"
python -m compileall -q src tests
python -m ruff check src tests
python -m mypy src
printf '%s\n' '[PHASE10] backend-quality-ok'
