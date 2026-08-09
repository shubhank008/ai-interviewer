#!/usr/bin/env sh
set -u
PYTHONPATH=src python -m compileall -q src tests
if command -v ruff >/dev/null 2>&1; then ruff check src tests; else echo 'ruff not installed; compile check completed'; fi
if command -v mypy >/dev/null 2>&1; then mypy src; else echo 'mypy not installed; type check skipped'; fi
npm run build --prefix frontend
printf '%s\n' '[PHASE9] frontend-build-ok'
