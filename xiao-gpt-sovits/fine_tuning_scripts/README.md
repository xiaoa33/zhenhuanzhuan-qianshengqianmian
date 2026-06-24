# GPT-SoVITS Fine-Tuning Scripts

This directory contains the project-specific scripts used to fine-tune and test the 14 role voices. The scripts are kept separate from upstream GPT-SoVITS code so the final submission can identify our work quickly.

## Files

- `batch_finetune_roles.py`: batch preprocessing, SoVITS training, GPT training, and optional cleanup for role lists under `../../gpt_sovits finetune_data/gpt_sovits_lists/by_role`.
- `run_all_roles_epoch10_final_only.sh`: final training entrypoint used for all roles, both `v4` and `v2ProPlus`, keeping only epoch 10 exported weights.
- `run_batch_finetune_roles.sh`: generic wrapper around `batch_finetune_roles.py --run`.
- `run_role_inference.py`: offline inference for one or more fine-tuned roles.
- `run_all_roles_inference_test.sh`: batch inference smoke test for all roles and both versions.

## Data Contract

The scripts expect GPT-SoVITS list files in:

```text
../../gpt_sovits finetune_data/gpt_sovits_lists/by_role/<role>_all.list
```

Each line uses:

```text
wav_path|speaker_name|zh|text
```

The current lists contain absolute wav paths and `inp_wav_dir` is intentionally left empty during preprocessing. Do not move or rewrite wav files as part of script cleanup.

## Typical Commands

Run a dry-run from this directory:

```bash
python batch_finetune_roles.py --roles zhenhuan --versions v4
```

Run the final epoch-10 training recipe:

```bash
PYTHON_BIN=python bash run_all_roles_epoch10_final_only.sh
```

Run a single-role inference test:

```bash
python run_role_inference.py \
  --roles zhenhuan \
  --version v4 \
  --gpt-epoch 10 \
  --sovits-epoch 10 \
  --text "微调已经完成了，测试一下效果" \
  --random-ref \
  --device cuda
```

## Outputs

Final exported weights are written to:

```text
GPT_weights_v4/
SoVITS_weights_v4/
GPT_weights_v2ProPlus/
SoVITS_weights_v2ProPlus/
```

Inference examples and metadata are written outside the GPT-SoVITS repo:

```text
../../inference_outputs/<version>/<role>/
```
