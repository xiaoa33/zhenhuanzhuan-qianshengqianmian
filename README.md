# 甄嬛传·千声千面 —— AI 角色语音对话系统

> 语音信息处理课程大作业 · 北京邮电大学 · 2026 年 6 月

## 项目简介

**甄嬛传·千声千面**是一个面向电视剧《甄嬛传》的多角色 AI 语音对话系统。系统从 76 集原剧音频中自主构建了包含 **14 个角色、13,605 段语音片段（总时长约 16.7 小时）** 的高质量中文语音数据集，并基于 **CosyVoice3-0.5B**（Zero-shot 语音克隆）和 **GPT-SoVITS**（微调语音合成）双引擎实现了多角色语音克隆与情感语音合成。

系统结合大语言模型（LLM）实现角色性格建模与对话生成，支持**单人智能对话**与**双人即兴对戏**两种交互模式，并通过 SSE 流式传输与 Web Audio API 实现了低延迟的语音播放体验。

## 核心特性

- **自主构建多角色语音数据集**：从原剧音频出发，经人声分离 → VAD 切分 → ASR 转写 → 声纹聚类 → 人工标注 → 数据清洗的完整 Pipeline，覆盖 14 个剧中角色
- **双引擎语音合成**：CosyVoice3 Zero-shot（30 个 Speaker）与 GPT-SoVITS 微调（14 角色 × 2 版本 = 28 组权重），前端可实时切换对比
- **情绪 Speaker 创新方案**：从原剧中手工采集 107 段真实情绪音频，注册为独立 Zero-shot Speaker，在不损失音色保真度的前提下实现喜悦、愤怒、悲伤、平静四种情感语音合成
- **角色智能对话**：LLM 驱动的角色性格建模，支持「现代来客」和「宫廷中人」两种身份的单人对话，以及双角色自动即兴对戏
- **流式语音播放**：SSE + Web Audio API 排队播放，首音延迟约 1.5 秒
- **古风宫廷 UI**：React 前端，深墨绿 + 宫廷金配色，毛笔体标题，Ken Burns 动效背景，14 张角色剧照 + 11 张场景背景图

## 系统架构

```
React 前端 (:5173)
    │
    ▼
yiping-backend FastAPI (:8003)     ← 中间层，统一 API 网关
    │
    ├── xiao-asr_llm (:8001)       ← ASR + LLM 对话生成 + 情绪分析
    ├── CosyVoice TTS (:8002)      ← CosyVoice3 Zero-shot 语音合成（云端）
    └── GPT-SoVITS TTS (:8004)     ← GPT-SoVITS 微调语音合成
```

前端与中间层运行在本地，三个 AI 服务部署于 AutoDL 云端（RTX 4080 SUPER），通过 SSH 隧道连接。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React + Vite + CSS Variables + Web Audio API |
| 中间层 | FastAPI + httpx + SSE |
| 语音合成 | CosyVoice3-0.5B（Zero-shot）、GPT-SoVITS（LoRA 微调） |
| 语音识别 | faster-whisper-small |
| 对话生成 | LLM（角色 Prompt + JSON 结构化输出） |
| 数据处理 | UVR5 + FunASR + 3D-Speaker eres2netv2 + KMeans |

## 目录结构

```
/
├── yiping-frontend/         # React 前端（古风宫廷 UI）
├── yiping-backend/          # FastAPI 中间层（API 网关 + 服务路由）
├── xiao-asr_llm/            # ASR + LLM 对话生成模块
├── xiao-gpt-sovits/         # GPT-SoVITS 推理服务 + 微调脚本
├── siting_data_prepare/     # 数据处理 Pipeline（UVR5 → ASR → 聚类 → 清洗）
├── siting_cosyvoice_tts/    # CosyVoice 微调、Zero-shot 注册、TTS 部署
├── final_paper/             # 终期论文（LaTeX 源码 + 图表）
├── 手动启动指令.md           # 完整的启动与部署指南
└── docs/                    # 设计文档与接口规范
```

## 数据集与模型权重

以下数据因体积较大，统一上传至百度网盘：

> **链接**：https://pan.baidu.com/s/1_uacMyl9y5YvrWsh77Mtww?pwd=kcs7
> **提取码**：kcs7

| 数据 | 说明 |
|------|------|
| `zero_shot_data/` | 127 条精选参考音频（14 角色），用于 Zero-shot Speaker 注册 |
| `emotion_examples/` | 107 条情绪参考音频（4 角色 × 4 情绪），用于情绪 Speaker 注册 |
| `甄嬛传14人物数据.tar` | 全量数据集（13,605 段 WAV + Kaldi 元数据） |
| `exp_GPTSoVITS_weights/` | GPT-SoVITS 14 角色微调权重（v4 + v2ProPlus） |
| `exp_zhenhuan_llm.tar` | CosyVoice3-0.5B 微调权重（12 GB） |

## 快速开始

详细的环境配置、依赖安装与各模块启动指令请参考 [手动启动指令.md](手动启动指令.md)。

## 小组成员

| 成员 | 姓名 | 学号 | 负责内容 |
|------|------|------|---------|
| 成员 A | 李思婷 | 2023212061 | 数据集构建、CosyVoice3 微调与 Zero-shot 方案、情绪 Speaker 创新方案 |
| 成员 B | 张笑 | 2023212062 | GPT-SoVITS 微调、ASR 模块、LLM 对话模块、GPT-SoVITS 服务部署 |
| 成员 C | 黄艺平 | 2023212179 | 前端设计（React 古风 UI）、yiping-backend 中间层、流式 TTS 链路集成 |
