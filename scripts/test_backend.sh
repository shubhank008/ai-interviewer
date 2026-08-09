#!/usr/bin/env sh
set -eu

export PYTHONPATH="src${PYTHONPATH:+:${PYTHONPATH}}"
python -m coverage erase
python -m coverage run --branch --source=src -m unittest discover -s tests -p 'test_*.py'
printf '%s\n' '[PHASE10] backend-tests-ok'
python -m coverage report --fail-under=80
python -m coverage xml
python -m coverage html
printf '%s\n' '[PHASE10] coverage-enforced-ok'
python scripts/run_mock_turn.py
printf '%s\n' '[PHASE10] mock-interview-e2e-ok'
