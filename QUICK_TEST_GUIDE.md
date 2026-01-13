# 两阶段分析快速测试指南

## 当前测试状态

✅ **代码实现**: 完成
✅ **配置系统**: 正常
✅ **Prompt 加载**: 正常
✅ **解析逻辑**: 正常
⚠️ **Ollama 服务**: 需要启动

## 快速开始（3步）

### 步骤 1: 启动 Ollama（如果使用本地模型）

```bash
# 终端 1: 启动 Ollama 服务
ollama serve

# 终端 2: 下载模型（如果还没有）
ollama pull llama3.2-vision
```

### 步骤 2: 启用两阶段分析

编辑 `video_analyzer/config/default_config.json` 或创建 `config/config.json`:

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

### 步骤 3: 运行测试

```bash
# 小规模测试（推荐先测试）
video-analyzer your_video.mp4 --max-frames 10

# 或使用测试配置
video-analyzer your_video.mp4 --config config --max-frames 10
```

## 验证结果

检查 `output/analysis.json`:

```bash
# 查看是否启用两阶段分析
python -c "import json; data=json.load(open('output/analysis.json')); print('Two-stage enabled:', data['metadata'].get('two_stage_analysis_enabled')); print('Deep analyzed:', data['metadata'].get('frames_deep_analyzed')); print('Screened only:', data['metadata'].get('frames_screened_only'))"
```

预期输出:
```
Two-stage enabled: True
Deep analyzed: 5-10
Screened only: 0-15
```

## 测试检查清单

- [ ] Ollama 服务运行中 (`ollama serve`)
- [ ] 视觉模型已下载 (`ollama pull llama3.2-vision`)
- [ ] 配置文件中 `two_stage_analysis.enabled: true`
- [ ] 运行分析命令
- [ ] 检查输出 JSON 包含 `screening_results`
- [ ] 检查 `metadata.two_stage_analysis_enabled: true`
- [ ] 验证只有部分帧被深度分析

## 常见问题

### Q: Ollama 连接失败
**A**: 确保 Ollama 服务正在运行
```bash
# 检查 Ollama 是否运行
curl http://localhost:11434/api/tags
# 或
python -c "import requests; print(requests.get('http://localhost:11434/api/tags').json())"
```

### Q: 没有帧被选中深度分析
**A**: 降低重要性阈值
```json
{
  "two_stage_analysis": {
    "small_model": {
      "importance_threshold": 4  // 从 6 降到 4
    }
  }
}
```

### Q: 成本仍然很高
**A**: 减少最大深度分析帧数
```json
{
  "two_stage_analysis": {
    "small_model": {
      "max_frames_for_deep_analysis": 5  // 从 10 降到 5
    }
  }
}
```

## 测试脚本

运行基础测试:
```bash
python test_two_stage.py
```

运行集成测试:
```bash
python test_integration.py
```

## 下一步

1. ✅ 代码已实现并测试通过
2. ⏳ 启动 Ollama 服务
3. ⏳ 运行实际视频测试
4. ⏳ 验证成本节省效果
5. ⏳ 根据结果调整参数

## 需要帮助？

查看详细文档:
- `docs/TWO_STAGE_ANALYSIS.md` - 完整使用说明
- `TEST_RESULTS.md` - 详细测试结果
- `test_two_stage.py` - 测试脚本源码






