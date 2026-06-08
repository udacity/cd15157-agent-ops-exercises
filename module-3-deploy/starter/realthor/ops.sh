#!/usr/bin/env sh
set -e

echo "=== Running unit tests ==="
uv run pytest tests/ -v

echo ""
echo "=== Running evaluation ==="
uv run python evaluation/run_eval.py

echo ""
echo "All checks passed."
