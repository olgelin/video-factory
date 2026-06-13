# Video Factory - Agent Rules

## 项目概述
14-skill视频生产pipeline，从话题到成片全自动。

## 编码规范
- Python 3.11+，不锁死任何LLM provider
- 配置走环境变量（VF_API_KEY, VF_BASE_URL, VF_MODEL）
- API Key绝不硬编码，绝不提交到git
- 重型ML用core venv（Python 3.12），轻量LLM用默认python

## 测试要求
- 每个skill的impl.py必须可独立运行
- pipeline冒烟测试：15/15 skill可导入 + LLM调用成功
- 验收标准：用户看视频说通过，不是代码标✅

## 架构约束
- V3 = 14个独立skill，不要整合到旧pipeline
- skill输出字段必须对齐下游（storyboard→hf-builder字段映射）
- LLM输出在reasoning_content字段时需要提取JSON
- BGM不锁死时间（audio_duration=-1）

## 常见坑
- 小米MiMo偶尔超时（429/timeout），靠重试不靠降级模型
- topic_selector含敏感词时LLM会拒绝，需要neutralize_prompt
- VoxCPM2需要reference_wav_path，不能传空
- ACE-Step VAE解码可能卡住（VRAM不够时）
