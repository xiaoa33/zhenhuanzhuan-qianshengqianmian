#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
GSV_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
TEXT="微调已经完成了，测试一下效果"
SUFFIX="${SUFFIX:-batch_randomref}"

cd "$GSV_ROOT"

for VERSION in v4 v2ProPlus; do
  "$PYTHON_BIN" scripts/run_role_inference.py \
    --version "$VERSION" \
    --gpt-epoch 10 \
    --sovits-epoch 10 \
    --random-ref \
    --timestamp-output \
    --output-suffix "$SUFFIX" \
    --text "$TEXT" \
    "$@"
done
