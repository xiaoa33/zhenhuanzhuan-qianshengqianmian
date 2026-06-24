#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
GSV_ROOT="${GSV_ROOT:-$PROJECT_ROOT/GPT-SoVITS}"
GSV_LIST_DIR="${GSV_LIST_DIR:-$PROJECT_ROOT/gpt_sovits finetune_data/gpt_sovits_lists/by_role}"
GSV_OUTPUT_DIR="${GSV_OUTPUT_DIR:-$PROJECT_ROOT/inference_outputs}"
PYTHON_BIN="${PYTHON_BIN:-python}"
TEXT="微调已经完成了，测试一下效果"
SUFFIX="${SUFFIX:-batch_randomref}"

cd "$GSV_ROOT"

for VERSION in v4 v2ProPlus; do
  "$PYTHON_BIN" "$SCRIPT_DIR/run_role_inference.py" \
    --gsv-root "$GSV_ROOT" \
    --list-dir "$GSV_LIST_DIR" \
    --version "$VERSION" \
    --gpt-epoch 10 \
    --sovits-epoch 10 \
    --output-dir "$GSV_OUTPUT_DIR" \
    --random-ref \
    --timestamp-output \
    --output-suffix "$SUFFIX" \
    --text "$TEXT" \
    "$@"
done
