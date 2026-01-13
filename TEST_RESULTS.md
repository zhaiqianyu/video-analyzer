# 两阶段分析功能测试结果

## 测试日期
2024年（当前测试）

## 测试环境
- 操作系统: Windows
- Python: 3.x
- 项目路径: D:\project-ls\video-analyzer

## 测试结果总览

### ✅ 通过的测试 (3/4)

1. **配置加载测试** ✅
   - 两阶段配置正确加载
   - 小模型配置: ollama/llama3.2-vision
   - 重要性阈值: 6
   - 最大深度分析帧数: 10

2. **Prompt 加载测试** ✅
   - Frame Analysis prompt: 1844 字符
   - Video Reconstruction prompt: 3781 字符
   - Frame Screening prompt: 331 字符
   - 所有 prompt 文件正确加载

3. **筛选结果解析测试** ✅
   - 能够正确解析重要性评分
   - 能够正确解析是否需要深度分析
   - 能够正确提取简要描述

### ❌ 未通过的测试 (1/4)

4. **Ollama 连接测试** ❌
   - 原因: Ollama 服务未运行
   - 状态: `Connection refused` (端口 11434)
   - 解决方案: 需要启动 Ollama 服务

## 测试文件

### 1. test_two_stage.py
基础功能测试脚本，测试：
- 配置加载
- Prompt 加载
- Ollama 连接
- 筛选结果解析

运行方式:
```bash
python test_two_stage.py
```

### 2. test_integration.py
集成测试脚本，检查：
- 测试配置文件
- Ollama 服务状态
- 使用说明

运行方式:
```bash
python test_integration.py
```

### 3. config/test_config.json
测试配置文件，已启用两阶段分析：
- `two_stage_analysis.enabled: true`
- 小模型: ollama/llama3.2-vision
- 最大深度分析帧数: 5（测试用）

## 下一步操作

### 选项 1: 使用本地 Ollama（推荐，零成本）

1. **安装 Ollama**（如果未安装）:
   ```bash
   # 访问 https://ollama.ai 下载安装
   ```

2. **启动 Ollama 服务**:
   ```bash
   ollama serve
   ```

3. **下载视觉模型**:
   ```bash
   ollama pull llama3.2-vision
   ```

4. **运行测试**:
   ```bash
   # 使用测试配置
   video-analyzer your_video.mp4 --config config --max-frames 10
   ```

### 选项 2: 使用 API 模型（需要 API key）

修改 `config/test_config.json` 中的小模型配置：

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
      "max_frames_for_deep_analysis": 5
    }
  }
}
```

### 选项 3: 仅测试代码逻辑（不调用实际模型）

可以运行单元测试验证代码逻辑，但需要模拟 LLM 客户端。

## 验证测试结果

运行分析后，检查 `output/analysis.json`:

1. **确认两阶段分析已启用**:
   ```json
   {
     "metadata": {
       "two_stage_analysis_enabled": true,
       "frames_deep_analyzed": 5,
       "frames_screened_only": 15
     }
   }
   ```

2. **检查筛选结果**:
   ```json
   {
     "screening_results": [
       {
         "frame_number": 0,
         "importance_score": 8,
         "needs_deep_analysis": true,
         "description": "..."
       }
     ]
   }
   ```

3. **检查帧分析结果**:
   ```json
   {
     "frame_analyses": [
       {
         "analyzed_by": "large_model",  // 或 "small_model_only"
         "importance_score": 8,
         "response": "..."
       }
     ]
   }
   ```

## 预期行为

### 两阶段分析流程

1. **阶段一：筛选** (所有帧)
   - 使用小模型（ollama/llama3.2-vision）
   - 生成简要描述
   - 评分重要性（0-10）
   - 判断是否需要深度分析

2. **阶段二：深度分析** (选中的帧)
   - 选择标准：
     - 重要性评分 ≥ 6
     - 或标记为"需要深度分析"
     - 最多 5 帧（测试配置）
     - 确保时间分布
   - 使用大模型（qwen-vl-max）
   - 生成详细分析

### 成本对比

假设 20 帧视频：

| 方案 | 小模型调用 | 大模型调用 | 总成本 |
|------|-----------|-----------|--------|
| 单阶段 | 0 | 20 | 100% |
| 两阶段 | 20 | 5 | ~30% |

*注：使用本地 Ollama 时，小模型调用成本为 0*

## 已知问题

1. **Ollama 未运行**
   - 状态: 测试失败
   - 影响: 无法使用本地模型进行筛选
   - 解决: 启动 Ollama 服务

2. **Windows 控制台编码**
   - 状态: 已修复
   - 影响: Unicode 字符显示问题
   - 解决: 使用 ASCII 字符替代

## 测试结论

✅ **代码实现完整**: 所有核心功能已实现
✅ **配置系统正常**: 配置加载和解析正常
✅ **Prompt 系统正常**: 所有 prompt 文件正确加载
✅ **解析逻辑正常**: 筛选结果解析功能正常
⚠️ **需要 Ollama**: 需要启动 Ollama 服务才能进行完整测试

## 建议

1. **立即测试**: 启动 Ollama 后运行完整测试
2. **小规模测试**: 先用 `--max-frames 5` 测试
3. **验证结果**: 检查筛选准确性和成本节省
4. **调整参数**: 根据实际效果调整阈值和最大帧数






