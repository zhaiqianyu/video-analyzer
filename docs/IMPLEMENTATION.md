# Video Analyzer 项目实现方案

## 项目概述

Video Analyzer 是一个智能视频分析工具，结合了视觉大模型（如 Llama3.2 Vision）和 Whisper 语音识别技术，通过提取关键帧、分析视觉内容、转录音频，生成全面的视频描述。

## 架构设计

### 整体架构

项目采用模块化设计，分为三个主要部分：

1. **核心分析模块** (`video_analyzer/`)
2. **Web UI 模块** (`video-analyzer-ui/`)
3. **配置文件与提示词模板**

```
视频输入
    ↓
┌─────────────────────────────────────┐
│  阶段1: 帧提取与音频处理            │
│  - OpenCV 关键帧提取                │
│  - FFmpeg 音频提取                  │
│  - Whisper 音频转录                 │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  阶段2: 帧分析                      │
│  - LLM 视觉模型分析每个关键帧       │
│  - 上下文感知的渐进式分析           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  阶段3: 视频重建                    │
│  - 合并所有帧分析结果               │
│  - 整合音频转录                     │
│  - 生成最终视频描述                 │
└─────────────────────────────────────┘
    ↓
JSON 输出（analysis.json）
```

## 核心模块详解

### 1. 视频处理模块 (`frame.py`)

**功能**：从视频中提取关键帧

**关键算法**：
- **自适应采样**：根据视频时长和目标帧率计算采样间隔
  ```python
  sample_interval = max(1, total_frames // (target_frames * 2))
  ```
- **帧差异分析**：使用灰度图像和绝对差分计算帧间差异
  ```python
  diff = cv2.absdiff(gray1, gray2)
  score = np.mean(diff)
  ```
- **关键帧选择**：选择差异分数最高的帧，确保捕获最重要的场景变化

**配置参数**：
- `frames_per_minute`: 每分钟提取的帧数（默认：60）
- `max_frames`: 最大帧数限制
- `FRAME_DIFFERENCE_THRESHOLD`: 帧差异阈值（默认：10.0）

### 2. 音频处理模块 (`audio_processor.py`)

**功能**：提取和转录视频中的音频

**实现流程**：
1. **音频提取**：使用 FFmpeg 提取音频为 WAV 格式
   - 采样率：16kHz
   - 声道：单声道
   - 格式：PCM 16-bit
2. **语音转录**：使用 faster-whisper 进行转录
   - 支持 VAD（语音活动检测）
   - 单词级时间戳
   - 多语言支持

**配置参数**：
- `whisper_model`: Whisper 模型大小（tiny/base/small/medium/large）
- `language`: 目标语言代码（可选，默认自动检测）
- `device`: 计算设备（cpu/cuda/mps）

### 3. 视觉分析模块 (`analyzer.py`)

**功能**：使用 LLM 分析视频帧并生成描述

**核心类：VideoAnalyzer**

**关键方法**：
1. **`analyze_frame(frame)`**：
   - 分析单个帧
   - 包含前序帧的上下文信息（`{PREVIOUS_FRAMES}`）
   - 支持用户自定义问题（`{prompt}`）

2. **`reconstruct_video(frame_analyses, frames, transcript)`**：
   - 合并所有帧分析结果
   - 整合音频转录
   - 生成最终视频描述

**提示词系统**：
- `frame_analysis.txt`: 单帧分析提示词
- `describe.txt`: 视频重建提示词
- 支持动态替换令牌：`{PREVIOUS_FRAMES}`, `{prompt}`, `{FRAME_NOTES}`, `{FIRST_FRAME}`, `{TRANSCRIPT}`

### 4. LLM 客户端模块 (`clients/`)

**设计模式**：抽象基类 + 具体实现

**基类：LLMClient**
- 定义通用接口：`generate()` 方法
- 提供图像编码功能：`encode_image()`

**实现类**：

1. **OllamaClient** (`ollama.py`)：
   - 本地 Ollama API 客户端
   - 图像格式：base64，通过 `images` 数组传递
   - 适用于本地运行，无需 API 密钥

2. **GenericOpenAIAPIClient** (`generic_openai_api.py`)：
   - 兼容 OpenAI API 格式
   - 支持 OpenRouter、OpenAI 等服务
   - 图像格式：`image_url` 类型的内容数组
   - 需要 API 密钥和端点 URL

### 5. 配置系统 (`config.py`)

**配置优先级（从高到低）**：
1. 命令行参数
2. 用户配置文件（`config/config.json`）
3. 默认配置（`config/default_config.json`）

**主要配置项**：
```json
{
  "clients": {
    "default": "ollama",
    "temperature": 0.0,
    "ollama": {...},
    "openai_api": {...}
  },
  "frames": {
    "per_minute": 60,
    "analysis_threshold": 10.0
  },
  "audio": {
    "whisper_model": "medium",
    "language": "en",
    "device": "cpu"
  }
}
```

### 6. 提示词加载系统 (`prompt.py`)

**路径解析优先级**：
1. 用户指定目录（`prompt_dir`）
   - 绝对路径
   - 用户主目录路径（`~`）
   - 相对路径（相对于当前工作目录）
2. 包资源（作为后备）

**开发模式支持**：
- 使用 `pip install -e .` 安装后
- 修改提示词文件立即生效
- 无需重新安装

## Web UI 模块

### 架构 (`video-analyzer-ui/server.py`)

**技术栈**：
- Flask：Web 服务器框架
- 服务器发送事件（SSE）：实时输出流

**主要路由**：
1. `GET /`：主页
2. `POST /upload`：文件上传
3. `POST /analyze/<session_id>`：启动分析
4. `GET /analyze/<session_id>/stream`：实时输出流
5. `GET /results/<session_id>`：下载结果
6. `POST /cleanup/<session_id>`：清理会话

**会话管理**：
- 每个上传生成唯一 `session_id`
- 临时目录存储上传文件和结果
- 支持会话清理

## 数据流程

### 输入处理流程

```
视频文件 (MP4/AVI/MOV/MKV)
    ↓
┌──────────────────────┐
│  CLI/UI 接收         │
└──────────────────────┘
    ↓
┌──────────────────────┐
│  配置加载            │
│  - 命令行参数        │
│  - 用户配置          │
│  - 默认配置          │
└──────────────────────┘
```

### 阶段1：帧提取与音频处理

```
视频文件
    ├──→ VideoProcessor.extract_keyframes()
    │       ├── OpenCV 读取视频
    │       ├── 计算目标帧数
    │       ├── 自适应采样
    │       ├── 帧差异分析
    │       └── 保存关键帧为 JPEG
    │
    └──→ AudioProcessor
            ├── extract_audio() → FFmpeg 提取
            └── transcribe() → Whisper 转录
```

### 阶段2：帧分析

```
关键帧列表
    ↓
for each frame:
    ├── 加载提示词模板 (frame_analysis.txt)
    ├── 替换令牌
    │   ├── {PREVIOUS_FRAMES} → 前序帧分析
    │   └── {prompt} → 用户问题
    ├── LLM 生成分析
    └── 存储分析结果
```

### 阶段3：视频重建

```
所有帧分析结果
    ↓
┌──────────────────────────────┐
│ reconstruct_video()          │
│  ├── 格式化所有帧分析        │
│  ├── 加载提示词 (describe.txt)│
│  ├── 替换令牌                │
│  │   ├── {FRAME_NOTES}       │
│  │   ├── {FIRST_FRAME}       │
│  │   ├── {TRANSCRIPT}        │
│  │   └── {prompt}            │
│  └── LLM 生成最终描述        │
└──────────────────────────────┘
    ↓
JSON 输出
```

### 输出格式

```json
{
  "metadata": {
    "client": "ollama",
    "model": "llama3.2-vision",
    "frames_extracted": 30,
    "transcription_successful": true
  },
  "transcript": {
    "text": "...",
    "segments": [...]
  },
  "frame_analyses": [
    {
      "response": "...",
      "timestamp": 0.5
    }
  ],
  "video_description": {
    "response": "..."
  }
}
```

## 关键技术点

### 1. 关键帧提取算法

**挑战**：如何高效地选择有代表性的帧

**解决方案**：
- 使用自适应采样减少计算量
- 基于帧差异分数排序选择
- 支持最大帧数限制避免过度提取

**局限性**：
- 采样间隔内的帧可能被遗漏
- 快速变化场景可能只选择一个帧
- 使用 max_frames 时可能跳过重要变化

### 2. 上下文感知分析

**实现方式**：
- 每个帧分析包含前序帧的上下文
- 通过 `{PREVIOUS_FRAMES}` 令牌传递
- 保持时间顺序和连续性

**优势**：
- 更连贯的分析结果
- 能够跟踪场景变化
- 减少重复描述

### 3. 多客户端支持

**扩展性设计**：
- 抽象基类定义接口
- 易于添加新的 LLM 提供商
- 统一的配置管理

**添加新客户端步骤**：
1. 继承 `LLMClient`
2. 实现 `generate()` 方法
3. 在配置中添加客户端配置
4. 更新 `create_client()` 函数

### 4. 错误处理与容错

**策略**：
- 音频提取失败时继续视频分析
- 转录失败时仅使用视觉分析
- 帧分析失败时记录错误但继续处理
- 支持分阶段处理（`--start-stage`）

## 性能优化

### 1. 帧提取优化
- 自适应采样减少处理的帧数
- 使用灰度图像比较降低计算复杂度

### 2. 并行处理潜力
- 帧分析可以并行化（当前是串行）
- 音频提取和帧提取可以并行进行

### 3. 资源管理
- 分析完成后清理临时文件
- 支持保留帧选项（`--keep-frames`）

## 使用场景

1. **视频内容分析**：快速了解视频内容
2. **视频摘要生成**：自动生成视频描述
3. **视频搜索**：基于内容的视频检索
4. **无障碍访问**：为视障用户提供视频描述
5. **内容审核**：自动识别视频内容

## 扩展方向

### 1. 功能扩展
- 支持批量处理
- 添加更多输出格式（Markdown、HTML）
- 支持视频片段分析
- 添加情感分析

### 2. 性能优化
- 并行帧分析
- GPU 加速帧提取
- 缓存机制

### 3. UI 增强
- 实时预览帧分析结果
- 可视化时间轴
- 交互式配置界面

## 技术栈总结

**核心依赖**：
- `opencv-python`: 视频处理
- `faster-whisper`: 音频转录
- `torch`: 深度学习框架
- `requests`: HTTP 客户端

**UI 依赖**：
- `flask`: Web 框架
- `werkzeug`: WSGI 工具

**可选依赖**：
- `ollama`: 本地 LLM（如果使用 Ollama）
- OpenAI API 客户端（如果使用云服务）

## 部署建议

### 本地部署
1. 安装 Python 3.11+
2. 安装 FFmpeg
3. 安装依赖：`pip install -e .`
4. 配置 Ollama 或 API 密钥
5. 运行 CLI 或启动 UI 服务器

### 云部署
- 考虑使用容器化（Docker）
- 配置环境变量管理敏感信息
- 使用云存储保存结果
- 考虑使用队列系统处理大量任务

