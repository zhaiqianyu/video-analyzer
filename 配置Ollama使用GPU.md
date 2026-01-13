# 配置 Ollama 使用 Intel Arc GPU

## 当前状态检查

运行检查脚本：
```bash
python check_ollama_gpu.py
```

## Intel Arc GPU 支持情况

⚠️ **重要提示**：Ollama 对 Intel Arc GPU 的支持可能有限。Windows 版本主要支持 NVIDIA GPU 和部分 AMD GPU。

## 配置步骤

### 方法 1: 检查 Ollama 版本

确保使用最新版本的 Ollama：
1. 访问 https://ollama.ai/download
2. 下载并安装最新版本
3. 重启 Ollama 服务

### 方法 2: 设置环境变量（尝试）

在 PowerShell 中设置环境变量（可能不适用于 Intel Arc）：

```powershell
# 设置 GPU 层数（尝试）
$env:OLLAMA_NUM_GPU=1
$env:OLLAMA_GPU_LAYERS=32

# 重启 Ollama
# 停止当前服务，然后重新启动
ollama serve
```

### 方法 3: 检查 GPU 使用情况

1. **打开任务管理器**
   - 按 `Ctrl + Shift + Esc`
   - 切换到"性能"选项卡
   - 选择 GPU

2. **运行模型测试**
   ```bash
   # 在另一个终端运行
   ollama run llama3.2-vision "Describe this image" --image test.jpg
   ```

3. **观察 GPU 使用率**
   - 查看 "Compute" 或 "DirectML" 的使用率
   - 如果使用率 > 0%，说明 GPU 在工作
   - 如果使用率 = 0%，说明在使用 CPU

### 方法 4: 查看 Ollama 日志

启动 Ollama 时查看日志输出：
```bash
ollama serve
```

查找以下信息：
- GPU 设备检测
- DirectML 相关信息
- 设备类型（CPU/GPU）

## 如果 GPU 不支持怎么办？

### 方案 A: 使用 CPU（当前方案）

如果 Ollama 不支持 Intel Arc GPU，当前使用 CPU 的方案仍然有效：
- ✅ 功能正常
- ⚠️ 速度较慢（每帧 3-4 分钟）

### 方案 B: 优化配置以减少处理时间

1. **减少帧数**
   ```json
   {
     "frames": {
       "per_minute": 30  // 从 60 降到 30
     }
   }
   ```

2. **提高筛选阈值**
   ```json
   {
     "two_stage_analysis": {
       "small_model": {
         "importance_threshold": 7,  // 从 6 提高到 7
         "max_frames_for_deep_analysis": 5  // 从 10 降到 5
       }
     }
   }
   ```

3. **使用更小的 Whisper 模型**
   ```json
   {
     "audio": {
       "whisper_model": "small"  // 从 medium 改为 small
     }
   }
   ```

### 方案 C: 考虑替代方案

如果 GPU 支持确实有限，可以考虑：

1. **LM Studio** - 对 Intel GPU 支持更好
   - 下载：https://lmstudio.ai/
   - 可能支持 Intel Arc GPU

2. **使用云端 API** - 完全使用 API（成本更高）
   - 将小模型也改为 API 调用
   - 速度更快但成本增加

## 验证 GPU 是否工作

运行以下命令测试：

```bash
# 1. 运行检查脚本
python check_ollama_gpu.py

# 2. 手动测试（在任务管理器打开的情况下）
ollama run llama3.2-vision "test"

# 3. 观察任务管理器中的 GPU 使用率
```

## 当前建议

基于您的 Intel Arc GPU，建议：

1. ✅ **先运行检查脚本**确认 GPU 是否被使用
2. ⚠️ **如果 GPU 不支持**，保持当前 CPU 配置
3. 🚀 **优化配置**以减少处理时间（减少帧数、提高阈值）
4. 💡 **考虑长期方案**：如果经常使用，考虑使用 LM Studio 或完全使用 API

## 相关资源

- Ollama 官方文档: https://github.com/ollama/ollama
- Intel Arc GPU 支持: 查看 Ollama GitHub Issues
- LM Studio: https://lmstudio.ai/



