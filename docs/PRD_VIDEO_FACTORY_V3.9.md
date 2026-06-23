# 视频工厂 v3.9 质量提升 PRD

> **文档版本**: 1.0  
> **创建日期**: 2026-06-23  
> **状态**: 待审批

---

## 一、项目背景

### 1.1 现状

视频工厂v3.8已实现14步pipeline自动化，能稳定产出视频。但存在以下核心问题：
- 稳定性不足：部分skill无错误处理，偶发崩溃
- 质量不稳定：依赖选题质量，无法保证一致输出
- 可维护性差：无测试、无文档、prompt散落

### 1.2 目标

| 维度 | 当前 | 目标 |
|------|------|------|
| 稳定性 | 70%成功率 | 95%成功率 |
| 视频质量 | 7/10 | 8.5/10 |
| 可维护性 | 无测试/文档 | 完整覆盖 |
| 开发效率 | 改一个怕一个 | 改了敢跑 |

---

## 二、问题清单

### 2.1 🔴 P0 - 阻塞性问题（必须修复）

#### 2.1.1 Skill文件结构不规范
- **现状**: 14个skill只有1个有SKILL.md，无法被Hermes skill系统识别
- **影响**: 无法复用、无法分享、无法版本管理
- **标准结构**:
  ```
  skills/<skill_name>/
  ├── SKILL.md          # 必须：元数据+使用说明
  ├── impl.py           # 必须：实现代码
  ├── references/       # 可选：参考文档、prompt模板
  ├── templates/        # 可选：输出模板
  └── scripts/          # 可选：辅助脚本
  ```

#### 2.1.2 lyrics_writer零错误处理
- **现状**: 0个try/except，任何异常直接崩溃
- **影响**: pipeline中断，前面步骤白跑
- **位置**: `hf-project/skills/lyrics_writer/impl.py`

#### 2.1.3 无资源预检
- **现状**: 不检查GPU内存、磁盘空间、模型是否加载
- **影响**: 运行到一半才发现资源不足
- **典型场景**: BGM生成占6GB VRAM + hf_builder并行时OOM

#### 2.1.4 无超时控制
- **现状**: 单个skill可能无限挂起
- **影响**: pipeline卡死，需手动kill
- **典型场景**: API调用无响应、模型推理卡住

### 2.2 🟡 P1 - 质量问题（尽快修复）

#### 2.2.1 script_writer深度不够
- **现状**: 口播能用但缺乏"别人看不到的角度"
- **影响**: 视频质量天花板
- **根因**: prompt缺乏深度引导、无真实数据注入

#### 2.2.2 hf_builder视觉丰富度不足
- **现状**: number_impact缺失、场景重复感
- **影响**: 画面不够饱满
- **根因**: prompt未强制要求装饰元素

#### 2.2.3 transcriber一直fallback
- **现状**: FunASR报错，只能用近似SRT
- **影响**: 字幕不准
- **根因**: torch 2.5.1兼容问题

#### 2.2.4 选题无结构感验证
- **现状**: topic_selector不检查选题是否有天然子话题
- **影响**: 选到"燃油车"这类开放式话题时质量差
- **教训**: 6/20验证——"经济数据预警"（三盏红灯结构）远好于"燃油车"

#### 2.2.5 design_system未被充分利用
- **现状**: specs一直是0 scenes，设计系统输出未注入hf_builder
- **影响**: 视觉风格不一致
- **根因**: 设计规范未被pipeline消费

#### 2.2.6 并发不安全
- **现状**: Phase 2/3并行执行共享context字典，无锁
- **影响**: 数据竞争，偶发异常
- **位置**: `main_full.py` run_parallel函数

### 2.3 🟢 P2 - 可维护性问题（计划修复）

#### 2.3.1 零测试覆盖
- **现状**: 没有任何test_*.py文件
- **影响**: 改代码没信心，不知道是否破坏现有功能

#### 2.3.2 依赖管理混乱
- **现状**: requirements.txt有注释掉的依赖，无lock文件
- **影响**: 环境不可复现

#### 2.3.3 日志不统一
- **现状**: 有的用print，有的用logger，格式不一
- **影响**: 排查问题困难

#### 2.3.4 配置分散
- **现状**: 每个skill硬编码路径、阈值
- **影响**: 改配置要改多个文件

#### 2.3.5 prompt散落各处
- **现状**: 每个skill的prompt硬编码在impl.py里
- **影响**: 无法A/B测试、无法版本管理

#### 2.3.6 无断点续传
- **现状**: pipeline失败后必须从头开始
- **影响**: 浪费时间

#### 2.3.7 无性能指标
- **现状**: 不记录每步耗时、token消耗
- **影响**: 无法优化瓶颈

#### 2.3.8 无版本管理
- **现状**: 输出文件无版本号，无法回溯
- **影响**: 无法对比不同版本效果

#### 2.3.9 无回滚机制
- **现状**: 出问题无法回到上一个工作版本
- **影响**: 风险高

#### 2.3.10 context无限膨胀
- **现状**: 12步传递下来context可能有几十个key
- **影响**: 内存浪费、调试困难

#### 2.3.11 feedback机制未生效
- **现状**: auto_optimizer存在但未真正调用，质量阈值未生效
- **影响**: 反馈闭环断裂

#### 2.3.12 无健康检查
- **现状**: pipeline开始前不检查依赖是否就绪
- **影响**: 运行到一半才发现问题

#### 2.3.13 无文档
- **现状**: 无API文档、架构图、故障排除指南
- **影响**: 新人上手困难

---

## 三、需求规格

### 3.1 功能需求

#### FR-01: 统一错误处理框架
- **描述**: 所有skill继承基类，统一try/catch/fallback
- **验收标准**:
  - [ ] 所有skill有至少1个fallback路径
  - [ ] 异常不导致pipeline中断
  - [ ] 错误日志包含skill名、步骤、原因

#### FR-02: 资源预检
- **描述**: pipeline开始前检查GPU/CPU/内存/磁盘/模型
- **验收标准**:
  - [ ] GPU内存不足时提前报错
  - [ ] 磁盘空间不足时提前报错
  - [ ] 模型未加载时提前报错

#### FR-03: 超时控制
- **描述**: 每个skill执行带超时，默认300s
- **验收标准**:
  - [ ] 超时后skill被终止
  - [ ] 超时后pipeline继续执行（或优雅退出）
  - [ ] 超时日志记录

#### FR-04: Skill文件结构规范化
- **描述**: 所有skill符合标准结构
- **验收标准**:
  - [ ] 每个skill有SKILL.md
  - [ ] prompt模板在references/目录
  - [ ] 无__pycache__/混入

#### FR-05: Prompt管理器
- **描述**: prompt从impl.py抽离，支持版本化
- **验收标准**:
  - [ ] prompt在references/目录
  - [ ] 支持多版本
  - [ ] 可热更新（不改代码）

#### FR-06: 断点续传
- **描述**: 支持从失败步骤继续
- **验收标准**:
  - [ ] 每步完成后保存checkpoint
  - [ ] 支持--resume参数
  - [ ] checkpoint包含context快照

#### FR-07: 统一配置管理
- **描述**: 所有配置集中管理
- **验收标准**:
  - [ ] 配置在config.yaml
  - [ ] 支持环境变量覆盖
  - [ ] 支持命令行覆盖

#### FR-08: 性能监控
- **描述**: 记录每步耗时、token消耗、文件大小
- **验收标准**:
  - [ ] 输出metrics.json
  - [ ] 包含每步详细指标
  - [ ] 支持历史对比

#### FR-09: 选题结构感验证
- **描述**: topic_selector检查选题是否有天然子话题
- **验收标准**:
  - [ ] 优先选有三段结构的选题
  - [ ] 拒绝开放式问题
  - [ ] 输出结构感评分

#### FR-10: 单元测试框架
- **描述**: 为每个skill编写单元测试
- **验收标准**:
  - [ ] 每个skill至少3个测试用例
  - [ ] 测试覆盖正常路径+异常路径
  - [ ] 可一键运行全部测试

### 3.2 非功能需求

#### NFR-01: 稳定性
- **指标**: pipeline成功率 ≥ 95%
- **测量**: 连续运行20次，失败不超过1次

#### NFR-02: 性能
- **指标**: 单次pipeline耗时 ≤ 15分钟
- **测量**: 从topic_scout到audio_mixer完成

#### NFR-03: 可维护性
- **指标**: 测试覆盖率 ≥ 60%
- **测量**: pytest --cov

#### NFR-04: 可扩展性
- **指标**: 新增skill ≤ 30分钟
- **测量**: 从创建目录到pipeline集成

---

## 四、解决方案

### 4.1 架构设计

```
video-factory/
├── main_full.py              # 入口（重构）
├── config.yaml               # 统一配置
├── skills/
│   ├── base.py               # 🆕 Skill基类
│   ├── topic_scout/
│   │   ├── SKILL.md
│   │   ├── impl.py
│   │   └── references/
│   │       └── prompt.txt
│   └── ... (其他skill)
├── core/
│   ├── resource_checker.py   # 🆕 资源预检
│   ├── timeout_guard.py      # 🆕 超时控制
│   ├── checkpoint.py         # 🆕 断点续传
│   ├── metrics.py            # 🆕 性能监控
│   └── config.py             # 🆕 配置管理
├── tests/                    # 🆕 测试目录
│   ├── test_topic_scout.py
│   └── ...
└── feedback_system/          # 重构
    ├── quality_tracker.py
    └── auto_optimizer.py
```

### 4.2 Skill基类设计

```python
# skills/base.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import time
import logging

class SkillBase(ABC):
    """所有skill的基类"""
    
    name: str = "unnamed"
    timeout: int = 300  # 默认超时300秒
    
    def run(self, context: dict) -> dict:
        """统一入口：验证 → 执行 → 验证输出"""
        start_time = time.time()
        
        try:
            # 1. 输入验证
            self.validate_input(context)
            
            # 2. 执行
            result = self.execute(context)
            
            # 3. 输出验证
            self.validate_output(result)
            
            # 4. 记录指标
            elapsed = time.time() - start_time
            self.record_metrics(elapsed)
            
            return result
            
        except Exception as e:
            # 5. fallback
            logging.error(f"{self.name} failed: {e}")
            return self.fallback(context, e)
    
    @abstractmethod
    def execute(self, context: dict) -> dict:
        """子类实现：核心逻辑"""
        pass
    
    def validate_input(self, context: dict):
        """输入验证（可选覆盖）"""
        pass
    
    def validate_output(self, result: dict):
        """输出验证（可选覆盖）"""
        pass
    
    def fallback(self, context: dict, error: Exception) -> dict:
        """降级策略（可选覆盖）"""
        raise error
    
    def record_metrics(self, elapsed: float):
        """记录性能指标"""
        pass
```

### 4.3 资源预检设计

```python
# core/resource_checker.py
import torch
import shutil
import psutil

class ResourceChecker:
    """资源预检"""
    
    @staticmethod
    def check_gpu(min_memory_gb: float = 6.0) -> bool:
        if not torch.cuda.is_available():
            return False
        free_memory = torch.cuda.mem_get_info()[0] / (1024**3)
        return free_memory >= min_memory_gb
    
    @staticmethod
    def check_disk(min_space_gb: float = 10.0) -> bool:
        free_space = shutil.disk_usage("/").free / (1024**3)
        return free_space >= min_space_gb
    
    @staticmethod
    def check_ram(min_gb: float = 8.0) -> bool:
        available = psutil.virtual_memory().available / (1024**3)
        return available >= min_gb
    
    @classmethod
    def preflight(cls) -> dict:
        """执行所有检查"""
        checks = {
            "gpu": cls.check_gpu(),
            "disk": cls.check_disk(),
            "ram": cls.check_ram(),
        }
        return {
            "passed": all(checks.values()),
            "checks": checks,
        }
```

### 4.4 断点续传设计

```python
# core/checkpoint.py
import json
from pathlib import Path
from datetime import datetime

class CheckpointManager:
    """断点续传管理"""
    
    def __init__(self, output_dir: Path):
        self.dir = output_dir / "checkpoints"
        self.dir.mkdir(exist_ok=True)
    
    def save(self, step: int, context: dict):
        """保存checkpoint"""
        data = {
            "step": step,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }
        with open(self.dir / f"step{step}.json", "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, step: int) -> Optional[dict]:
        """加载checkpoint"""
        path = self.dir / f"step{step}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None
    
    def get_latest(self) -> Optional[int]:
        """获取最新checkpoint步骤"""
        checkpoints = sorted(self.dir.glob("step*.json"))
        if checkpoints:
            return int(checkpoints[-1].stem.replace("step", ""))
        return None
```

### 4.5 Prompt管理器设计

```python
# core/prompt_manager.py
from pathlib import Path

class PromptManager:
    """Prompt版本管理"""
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
    
    def get_prompt(self, skill_name: str, version: str = "latest") -> str:
        """获取prompt"""
        prompt_dir = self.skills_dir / skill_name / "references"
        
        if version == "latest":
            # 找最新版本
            prompts = sorted(prompt_dir.glob("prompt_v*.txt"))
            if prompts:
                return prompts[-1].read_text()
        
        # 指定版本
        prompt_file = prompt_dir / f"prompt_{version}.txt"
        if prompt_file.exists():
            return prompt_file.read_text()
        
        raise FileNotFoundError(f"Prompt not found: {skill_name}/{version}")
    
    def list_versions(self, skill_name: str) -> list:
        """列出所有版本"""
        prompt_dir = self.skills_dir / skill_name / "references"
        return [p.stem for p in prompt_dir.glob("prompt_v*.txt")]
```

---

## 五、优先级排序

| 阶段 | 任务 | 优先级 | 预计时间 | 依赖 |
|------|------|--------|----------|------|
| **Phase 1** | 统一错误处理框架 | P0 | 1天 | 无 |
| **Phase 1** | 资源预检 | P0 | 0.5天 | 无 |
| **Phase 1** | 超时控制 | P0 | 0.5天 | 无 |
| **Phase 1** | Skill文件结构规范化 | P0 | 1天 | 无 |
| **Phase 2** | Prompt管理器 | P1 | 1天 | Phase 1 |
| **Phase 2** | 断点续传 | P1 | 1天 | Phase 1 |
| **Phase 2** | 统一配置管理 | P1 | 0.5天 | 无 |
| **Phase 2** | 性能监控 | P1 | 0.5天 | 无 |
| **Phase 2** | 选题结构感验证 | P1 | 0.5天 | 无 |
| **Phase 3** | 单元测试框架 | P2 | 2天 | Phase 1 |
| **Phase 3** | 文档生成 | P2 | 1天 | Phase 1 |
| **Phase 3** | 日志统一 | P2 | 0.5天 | Phase 1 |
| **Phase 3** | 反馈机制修复 | P2 | 1天 | Phase 1 |

**总计**: 约10天

---

## 六、验收标准

### 6.1 Phase 1验收

- [ ] 所有skill继承SkillBase
- [ ] 所有skill有至少1个fallback路径
- [ ] pipeline开始前执行资源预检
- [ ] 单个skill超时300s后被终止
- [ ] 所有skill目录有SKILL.md
- [ ] 无__pycache__/混入skill目录

### 6.2 Phase 2验收

- [ ] prompt在references/目录，支持版本选择
- [ ] 支持--resume参数从checkpoint继续
- [ ] 配置集中在config.yaml
- [ ] 输出metrics.json包含每步指标
- [ ] topic_selector优先选有结构感的选题

### 6.3 Phase 3验收

- [ ] 每个skill至少3个测试用例
- [ ] 测试覆盖率 ≥ 60%
- [ ] 有API文档、架构图、故障排除指南
- [ ] 日志格式统一，支持按级别过滤
- [ ] feedback_history.json记录趋势分析

### 6.4 整体验收

- [ ] pipeline成功率 ≥ 95%（连续20次）
- [ ] 单次pipeline耗时 ≤ 15分钟
- [ ] 新增skill ≤ 30分钟
- [ ] 视频质量评分 ≥ 8.5/10

---

## 七、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 重构引入新bug | 中 | 高 | 渐进式迁移，每步测试 |
| 性能下降 | 低 | 中 | 基准测试对比 |
| 时间超期 | 中 | 中 | 优先P0，P2可延后 |
| 用户不接受新结构 | 低 | 高 | 提前沟通，保持向后兼容 |

---

## 八、附录

### 8.1 相关文档

- [AGENTS.md](../AGENTS.md) - 项目规范
- [design.md](../design.md) - 设计文档
- [WORKFLOW.md](WORKFLOW.md) - 工作流说明

### 8.2 变更记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-23 | 1.0 | 初始版本 |

---

## 九、待确认

1. **Phase 1是否立即开始？**
2. **是否需要保持向后兼容？**
3. **测试框架用pytest还是unittest？**
4. **配置格式用yaml还是toml？**
