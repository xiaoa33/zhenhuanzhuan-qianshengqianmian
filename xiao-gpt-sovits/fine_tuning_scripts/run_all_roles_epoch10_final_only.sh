#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
GSV_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"

cd "$GSV_ROOT"
exec "$PYTHON_BIN" scripts/batch_finetune_roles.py \
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
