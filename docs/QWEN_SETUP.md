# 使用通义千问（Qwen）模型配置指南

## 概述

本项目支持通过 OpenAI 兼容的 API 使用通义千问（Qwen）模型。通义千问是阿里巴巴开发的大语言模型，提供多种版本，包括支持视觉的多模态版本。

## 前置条件

1. **获取 API 密钥**：
   - 访问 [阿里云百炼平台](https://bailian.console.aliyun.com/)
   - 注册并登录账号
   - 创建 API 密钥（API Key）

2. **确认模型支持**：
   - 确保选择的 Qwen 模型支持视觉任务（多模态）
   - 推荐使用 Qwen-VL 系列模型（支持图像理解）

## 配置方法

### 方法一：通过命令行配置（临时使用）

```bash
video-analyzer video.mp4 \
    --client openai_api \
    --api-key your-qwen-api-key \
    --api-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
    --model qwen-vl-max
```

**参数说明**：
- `--client openai_api`：使用 OpenAI 兼容的 API 客户端
- `--api-key`：您的阿里云 API 密钥
- `--api-url`：阿里云 DashScope API 端点
- `--model`：Qwen 模型名称（见下方模型列表）

### 方法二：通过配置文件（推荐）

#### 步骤 1：创建或编辑配置文件

创建 `config/config.json` 文件（如果不存在）：

```json
{
  "clients": {
    "default": "openai_api",
    "temperature": 0.0,
    "openai_api": {
      "api_key": "your-qwen-api-key",
      "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "model": "qwen-vl-max"
    }
  },
  "frames": {
    "per_minute": 60,
    "analysis_threshold": 10.0
  },
  "audio": {
    "whisper_model": "medium",
    "device": "cpu"
  }
}
```

#### 步骤 2：运行项目

```bash
video-analyzer video.mp4
```

配置会自动从 `config/config.json` 加载。

## Qwen 模型列表

### 视觉模型（推荐用于视频分析）

| 模型名称 | 说明 | 适用场景 |
|---------|------|---------|
| `qwen-vl-max` | 最大版本，性能最强 | 高质量视频分析 |
| `qwen-vl-plus` | 增强版，平衡性能和成本 | 推荐用于一般用途 |
| `qwen-vl` | 标准版 | 成本敏感场景 |

### 文本模型（不支持视觉）

注意：纯文本模型不支持图像分析，**不建议用于视频分析**。

| 模型名称 | 说明 |
|---------|------|
| `qwen-max` | 最大版本 |
| `qwen-plus` | 增强版 |
| `qwen-turbo` | 快速版本 |

## API 端点

### 阿里云 DashScope（官方）

- **API 端点**：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- **文档**：[阿里云 DashScope 文档](https://help.aliyun.com/zh/model-studio/)
- **特点**：官方服务，稳定可靠

### 其他 OpenAI 兼容的服务

如果其他服务提供商也提供 Qwen 模型（如 OpenRouter），您可以使用：

```json
{
  "clients": {
    "default": "openai_api",
    "openai_api": {
      "api_key": "your-api-key",
      "api_url": "https://openrouter.ai/api/v1",
      "model": "qwen/qwen-vl-max"
    }
  }
}
```

注意：模型名称可能需要根据服务提供商调整（如添加前缀 `qwen/`）。

## 配置示例

### 示例 1：使用 Qwen-VL-Plus（推荐）

```json
{
  "clients": {
    "default": "openai_api",
    "temperature": 0.2,
    "openai_api": {
      "api_key": "sk-xxxxxxxxxxxxx",
      "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "model": "qwen-vl-plus"
    }
  }
}
```

### 示例 2：使用 Qwen-VL-Max（最高性能）

```json
{
  "clients": {
    "default": "openai_api",
    "temperature": 0.0,
    "openai_api": {
      "api_key": "sk-xxxxxxxxxxxxx",
      "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "model": "qwen-vl-max"
    }
  }
}
```

### 示例 3：命令行快速切换

```bash
# 使用 Qwen-VL-Plus
video-analyzer video.mp4 \
    --client openai_api \
    --api-key sk-xxxxxxxxxxxxx \
    --api-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
    --model qwen-vl-plus

# 使用 Qwen-VL-Max
video-analyzer video.mp4 \
    --client openai_api \
    --api-key sk-xxxxxxxxxxxxx \
    --api-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
    --model qwen-vl-max
```

## 验证配置

### 步骤 1：测试 API 连接

可以使用简单的 Python 脚本测试：

```python
import requests

api_key = "your-api-key"
api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "qwen-vl-plus",
    "messages": [
        {
            "role": "user",
            "content": "你好"
        }
    ]
}

response = requests.post(api_url, headers=headers, json=data)
print(response.json())
```

### 步骤 2：运行项目测试

使用短视频测试：

```bash
video-analyzer test_video.mp4 --max-frames 3
```

## 注意事项

### 1. API 密钥安全

- ❌ **不要**将 API 密钥提交到代码仓库
- ✅ **使用**环境变量或配置文件（不提交到 Git）
- ✅ **添加** `config/config.json` 到 `.gitignore`

### 2. 费用考虑

- Qwen 模型按使用量计费
- 不同模型版本价格不同
- 建议先使用较小模型测试
- 查看 [阿里云定价](https://help.aliyun.com/zh/model-studio/pricing) 了解详细费用

### 3. 模型选择

- **视频分析**：必须使用 Qwen-VL 系列（支持视觉）
- **纯文本任务**：可以使用 Qwen 文本模型
- **性能 vs 成本**：根据需求选择合适的版本

### 4. 网络访问

- 确保服务器可以访问阿里云 API 端点
- 如果在中国大陆，访问速度通常较快
- 如果在海外，可能需要考虑网络延迟

### 5. 速率限制

- 阿里云 API 可能有速率限制
- 项目已内置重试机制
- 如果遇到限流，会自动等待后重试

## 常见问题

### Q1：如何确认模型是否支持视觉？

A：查看模型名称，如果包含 `-vl` 后缀，则支持视觉任务。例如：
- ✅ `qwen-vl-max` - 支持视觉
- ✅ `qwen-vl-plus` - 支持视觉
- ❌ `qwen-max` - 不支持视觉

### Q2：API 端点格式是什么？

A：阿里云 DashScope 的 OpenAI 兼容端点：
```
https://dashscope.aliyuncs.com/compatible-mode/v1
```

完整路径会自动构建为：
```
https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
```

### Q3：可以使用其他 Qwen 服务提供商吗？

A：可以，只要提供 OpenAI 兼容的 API 格式。常见的包括：
- 阿里云 DashScope（官方）
- OpenRouter（如果支持 Qwen）
- 其他第三方服务

### Q4：配置后仍然使用 Ollama？

A：检查以下几点：
1. 确认 `config.json` 中 `"default": "openai_api"`
2. 检查 API 密钥是否正确
3. 检查命令行是否覆盖了配置（命令行优先级更高）

### Q5：如何切换回 Ollama？

A：修改配置文件：

```json
{
  "clients": {
    "default": "ollama",
    "ollama": {
      "url": "http://localhost:11434",
      "model": "llama3.2-vision"
    }
  }
}
```

或使用命令行：

```bash
video-analyzer video.mp4 --client ollama
```

## 相关资源

- [阿里云百炼平台](https://bailian.console.aliyun.com/)
- [DashScope API 文档](https://help.aliyun.com/zh/model-studio/developer-reference/)
- [Qwen 模型文档](https://help.aliyun.com/zh/model-studio/)
- [项目 GitHub 仓库](https://github.com/byjlw/video-analyzer)

## 总结

使用 Qwen 模型的步骤：

1. ✅ 获取阿里云 API 密钥
2. ✅ 选择 Qwen-VL 系列模型（支持视觉）
3. ✅ 配置 `config/config.json` 或使用命令行参数
4. ✅ 运行项目测试

**推荐配置**：
- 模型：`qwen-vl-plus`（平衡性能和成本）
- API 端点：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 温度：`0.2`（稳定输出）



