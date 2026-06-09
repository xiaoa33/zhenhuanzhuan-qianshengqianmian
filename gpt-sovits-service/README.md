# GPT-SoVITS TTS Service

独立 TTS 服务，监听 `8002`，实现 `POST /synthesize`，响应格式兼容 `yiping-backend/services/tts_client.py`。

## 启动

稳定测试模式：

```bash
cd zhenhuanzhuan-qianshengqianmian/gpt-sovits-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```

实时演示推荐模式：

```bash
cd /mnt/sdb/wangxinran/zhangxiao/template/VIP_BigHW/zhenhuanzhuan-qianshengqianmian/gpt-sovits-service
GSV_BACKEND=persistent GSV_CACHE_SIZE=1 \
  /mnt/sdc/zhangyuxuan/envs/zx_VIP/bin/python -m uvicorn main:app --port 8002
```

`persistent` 模式会按 `(role, version)` 缓存 GPT-SoVITS 的 `TTS` 对象。第一次请求某个角色仍需加载模型，之后同一角色只执行推理，不再每轮重新加载权重。

服务会调用已有 GPT-SoVITS 推理脚本：

```bash
/mnt/sdc/zhangyuxuan/envs/zx_VIP/bin/python \
  /mnt/sdb/wangxinran/zhangxiao/template/VIP_BigHW/GPT-SoVITS/scripts/run_role_inference.py
```

## 关键环境变量

```env
GSV_ROOT=/mnt/sdb/wangxinran/zhangxiao/template/VIP_BigHW/GPT-SoVITS
GSV_PYTHON=/mnt/sdc/zhangyuxuan/envs/zx_VIP/bin/python
GSV_VERSION=v4
GSV_FALLBACK_VERSION=v2ProPlus
GSV_GPT_EPOCH=10
GSV_SOVITS_EPOCH=10
GSV_DEVICE=cuda
GSV_TIMEOUT_SEC=600
GSV_BACKEND=persistent
GSV_CACHE_SIZE=1
```

默认路径已按当前项目结构设置，通常不需要额外配置。

## 参考音频选择

- `zhenhuan` 和 `huangshang`：优先从 `zhenhuanzhuan-qianshengqianmian/emotion_samples/{role}/{emotion}/` 随机取一条。
- 其他角色：从 `dataset/gpt_sovits_lists/by_role/{role}_all.list` 中随机取一条可读音频。
- 情绪样本的参考文本会按 wav 文件名去角色 list 中查找。

已处理网站角色 ID 与 GPT-SoVITS 权重名不一致的问题：

| 网站 ID | GPT-SoVITS role |
|---|---|
| `anlinrong` | `anlingrong` |
| `yixiu` | `huanghou` |
| `wensichu` | `wenshichu` |

## 与 CosyVoice 共存

如果同时需要 CosyVoice 云端隧道，不要让隧道占用本地 `8002`。建议：

```bash
# GPT-SoVITS service
uvicorn main:app --reload --port 8002

# CosyVoice tunnel 改到本地 8003
ssh -L 8003:localhost:8003 -p 28281 root@connect.bjb1.seetacloud.com
```

主后端保持：

```env
TTS_SERVICE_URL=http://localhost:8002
USE_MOCK_TTS=false
```
