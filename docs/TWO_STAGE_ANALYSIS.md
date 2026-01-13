# 两阶段分析功能说明

## 概述

两阶段分析功能通过"小模型筛选 + 大模型深度分析"的方式，大幅降低 API token 消耗（约 60-70%），同时保证关键帧的分析质量。

## 工作原理

### 阶段一：小模型快速筛选
- 使用轻量级模型（如本地 Ollama 的 `llama3.2-vision`）对所有帧进行快速筛选
- 每帧生成：
  - 简要描述（1-2句话）
  - 重要性评分（0-10分）
  - 是否需要深度分析（是/否）

### 阶段二：大模型深度分析
- 仅对筛选出的关键帧使用大模型（如 `qwen-vl-max`）进行详细分析
- 筛选标准：
  - 重要性评分 ≥ 阈值（默认 6 分）
  - 或标记为"需要深度分析"
  - 最多选择 N 帧（默认 10 帧）
  - 确保时间分布（开头、中段、结尾都有帧）

## 配置方法

### 方法一：修改配置文件（推荐）

编辑 `config/default_config.json` 或创建 `config/config.json`：

```json
{
  "two_stage_analysis": {
    "enabled": true,
    "small_model": {
      "client": "ollama",
      "model": "llama3.2-vision",
      "importance_threshold": 6,
      "max_frames_for_deep_analysis": 10
    },
    "large_model": {
      "client": "openai_api",
      "model": "qwen-vl-max"
    }
  }
}
```

### 配置参数说明

#### `two_stage_analysis.enabled`
- 类型：`boolean`
- 默认：`false`
- 说明：是否启用两阶段分析

#### `two_stage_analysis.small_model`
小模型配置：

- `client`: 客户端类型
  - `"ollama"`: 使用本地 Ollama（推荐，零成本）
  - `"openai_api"`: 使用 API 服务（如 Qwen-VL）
  
- `model`: 模型名称
  - Ollama: `"llama3.2-vision"`（推荐）
  - API: `"qwen-vl"`（低成本）或 `"qwen-vl-plus"`（性能更好）
  
- `importance_threshold`: 重要性阈值（0-10）
  - 默认：`6`
  - 说明：评分 ≥ 此值的帧会被考虑深度分析
  
- `max_frames_for_deep_analysis`: 最大深度分析帧数
  - 默认：`10`
  - 说明：即使有更多帧满足条件，也最多只深度分析这么多帧

#### `two_stage_analysis.large_model`
大模型配置（可选，默认使用主配置）：

- `client`: 客户端类型（通常与主配置一致）
- `model`: 大模型名称（如 `"qwen-vl-max"`）

## 使用示例

### 示例 1：使用本地 Ollama（零成本）

```json
{
  "two_stage_analysis": {
    "enabled": true,
    "small_model": {
      "client": "ollama",
      "model": "llama3.2-vision",
      "importance_threshold": 6,
      "max_frames_for_deep_analysis": 10
    }
  }
}
```

运行：
```bash
video-analyzer video.mp4
```

### 示例 2：使用 Qwen-VL 作为小模型

```json
{
  "two_stage_analysis": {
    "enabled": true,
    "small_model": {
      "client": "openai_api",
      "model": "qwen-vl",
      "api_key": "your-api-key",
      "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "importance_threshold": 6,
      "max_frames_for_deep_analysis": 10
    }
  }
}
```

## 输出格式

启用两阶段分析后，输出 JSON 会包含额外字段：

```json
{
  "metadata": {
    "two_stage_analysis_enabled": true,
    "small_model": {
      "client": "ollama",
      "model": "llama3.2-vision",
      "importance_threshold": 6,
      "max_frames_for_deep_analysis": 10
    },
    "frames_deep_analyzed": 10,
    "frames_screened_only": 50
  },
  "screening_results": [
    {
      "frame_number": 0,
      "timestamp": 0.0,
      "description": "画面显示...",
      "importance_score": 8,
      "needs_deep_analysis": true,
      "raw_response": "..."
    }
  ],
  "frame_analyses": [
    {
      "response": "详细分析内容...",
      "screening_description": "快速筛选描述...",
      "importance_score": 8,
      "analyzed_by": "large_model"
    }
  ]
}
```

### 字段说明

- `screening_results`: 所有帧的筛选结果
- `frame_analyses`: 帧分析结果
  - 如果 `analyzed_by` 为 `"large_model"`：使用大模型深度分析
  - 如果 `analyzed_by` 为 `"small_model_only"`：仅使用小模型筛选，未深度分析

## 成本对比

假设分析 60 帧视频：

| 方案 | 输入 Token | 输出 Token | 总成本 | 节省比例 |
|------|-----------|-----------|--------|---------|
| 单阶段（全分析） | 90,000-150,000 | 18,000 | 108,000-168,000 | - |
| 两阶段（10帧深度） | 20,000 + 6,000 | 3,000 + 18,000 | 47,000 | **约 60-70%** |

*注：使用本地 Ollama 时，小模型筛选阶段成本为 0*

## 调优建议

### 如果漏掉重要帧
- 降低 `importance_threshold`（如从 6 降到 4）
- 增加 `max_frames_for_deep_analysis`（如从 10 增加到 15）

### 如果成本仍然较高
- 降低 `max_frames_for_deep_analysis`（如从 10 降到 5）
- 提高 `importance_threshold`（如从 6 提高到 7）

### 如果筛选不准确
- 尝试使用中文能力更强的模型（如 `qwen-vl`）作为小模型
- 调整筛选 prompt（`frame_screening.txt`）

## 注意事项

1. **确保 Ollama 运行**：如果使用本地模型，确保 Ollama 服务正在运行
   ```bash
   ollama serve
   ```

2. **模型已下载**：确保小模型已下载
   ```bash
   ollama pull llama3.2-vision
   ```

3. **向后兼容**：默认情况下 `enabled: false`，不影响现有工作流

4. **时间分布保证**：系统会自动确保选择的帧分布在视频的不同时间段

## 故障排除

### 问题：筛选结果解析失败
- 检查 `frame_screening.txt` prompt 格式是否正确
- 查看 `screening_results` 中的 `raw_response` 字段

### 问题：没有帧被选中深度分析
- 检查 `importance_threshold` 是否设置过高
- 查看 `screening_results` 中的 `importance_score` 分布

### 问题：Ollama 连接失败
- 确认 Ollama 服务正在运行：`curl http://localhost:11434/api/tags`
- 检查配置文件中的 URL 是否正确

## 相关文件

- 筛选 Prompt: `video_analyzer/prompts/frame_analysis/frame_screening.txt`
- 配置文件: `video_analyzer/config/default_config.json`
- 核心实现: `video_analyzer/analyzer.py`




