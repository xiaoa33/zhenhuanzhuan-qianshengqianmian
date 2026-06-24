# GPT-SoVITS TTS Service

独立 TTS 服务，监听 `8004`，实现 `POST /synthesize`，响应格式兼容 `yiping-backend/services/tts_client.py`。

## 启动

稳定测试模式：

```bash
cd xiao-gpt-sovits
pip install -r requirements.txt
uvicorn main:app --reload --port 8004
```

实时演示推荐模式：

```bash
cd xiao-gpt-sovits
GSV_BACKEND=persistent GSV_CACHE_SIZE=1 \
  python -m uvicorn main:app --port 8004
```

`persistent` 模式会按 `(role, version)` 缓存 GPT-SoVITS 的 `TTS` 对象。第一次请求某个角色仍需加载模型，之后同一角色只执行推理，不再每轮重新加载权重。

服务默认调用项目根目录内的 GPT-SoVITS 推理环境：

```bash
GSV_ROOT=../GPT-SoVITS
GSV_LIST_DIR="../gpt_sovits finetune_data/gpt_sovits_lists/by_role"
```

## 关键环境变量

```env
GSV_ROOT=../GPT-SoVITS
GSV_PYTHON=python
GSV_LIST_DIR="../gpt_sovits finetune_data/gpt_sovits_lists/by_role"
GSV_VERSION=v4
GSV_FALLBACK_VERSION=v2ProPlus
GSV_GPT_EPOCH=10
GSV_SOVITS_EPOCH=10
GSV_DEVICE=cuda
GSV_TIMEOUT_SEC=600
GSV_BACKEND=persistent
GSV_CACHE_SIZE=1
GSV_REF_MIN_SEC=3.0
GSV_REF_MAX_SEC=10.0
```

默认路径已按当前项目结构设置，通常不需要额外配置。

## 参考音频选择

- `zhenhuan` 和 `huangshang`：优先从 `../emotion_samples/{role}/{emotion}/` 随机取一条。
- 其他角色：从 `../gpt_sovits finetune_data/gpt_sovits_lists/by_role/{role}_all.list` 中随机取一条可读音频。
- 情绪样本的参考文本会按 wav 文件名去角色 list 中查找。
- 参考音频默认只选择 `3-10` 秒范围内的音频。GPT-SoVITS 内部也会校验这个范围，不建议放宽。

已处理网站角色 ID 与 GPT-SoVITS 权重名不一致的问题：

| 网站 ID | GPT-SoVITS role |
|---|---|
| `anlinrong` | `anlingrong` |
| `yixiu` | `huanghou` |
| `wensichu` | `wenshichu` |

## 与 CosyVoice 共存

当前约定 CosyVoice 继续占用原来的本地 `8002`，GPT-SoVITS 改到 `8004`：

```bash
# GPT-SoVITS service
uvicorn main:app --reload --port 8004

# CosyVoice tunnel 保持本地 8002
ssh -L 8002:localhost:8003 -p 28281 root@connect.bjb1.seetacloud.com
```

主后端保持：

```env
TTS_SERVICE_URL=http://localhost:8002
GPT_SOVITS_SERVICE_URL=http://localhost:8004
COSYVOICE_SERVICE_URL=http://localhost:8002
USE_MOCK_TTS=false
```
