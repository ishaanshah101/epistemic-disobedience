#!/usr/bin/env bash
# Reproduce the whole study from a clean checkout.
#
#   ./run.sh gpt-4o-mini        collect, score, and plot
#   ./run.sh gpt-4o-mini 5      the same, with 5 trials per cell
#
# Needs an API key in OPENAI_API_KEY or in a file called .openai_key.
set -euo pipefail
MODEL="${1:?usage: ./run.sh <model-id> [trials]}"
TRIALS="${2:-5}"

echo "==> unit tests"
python3 tests/test_classify.py
python3 src/stats.py

echo "==> collecting ${TRIALS} trials per cell from ${MODEL}"
python3 src/run_api.py --model "$MODEL" --trials "$TRIALS"

echo "==> scoring"
python3 src/analyze.py --sources openai_api --tag main
python3 src/analyze_human.py

echo "==> figures"
python3 src/figures.py main

echo "==> verifying the paper against the data"
python3 src/verify_paper.py

echo "==> done. tables in results/tables, figures in results/figures"
