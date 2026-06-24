#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
GSV_ROOT="${GSV_ROOT:-$PROJECT_ROOT/GPT-SoVITS}"
GSV_LIST_DIR="${GSV_LIST_DIR:-$PROJECT_ROOT/gpt_sovits finetune_data/gpt_sovits_lists/by_role}"
PYTHON_BIN="${PYTHON_BIN:-python}"

cd "$GSV_ROOT"
exec "$PYTHON_BIN" "$SCRIPT_DIR/batch_finetune_roles.py" \
  --gsv-root "$GSV_ROOT" \
  --list-dir "$GSV_LIST_DIR" \
  --run \
  --versions v4 v2ProPlus \
  --s2-epochs-v4 10 \
  --s2-epochs-v2proplus 10 \
  --s2-save-every-epoch-v4 10 \
  --s2-save-every-epoch-v2proplus 10 \
  --gpt-epochs 10 \
  --gpt-save-every-epoch 10 \
  --clean-train-ckpt \
  --prune-exported-weights \
  "$@"
