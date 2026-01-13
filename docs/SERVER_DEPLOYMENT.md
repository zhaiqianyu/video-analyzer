# 服务器部署指南

本指南将帮助您在Linux服务器上部署和运行视频分析工具。

## 目录

- [前置要求](#前置要求)
- [步骤1：服务器环境准备](#步骤1服务器环境准备)
- [步骤2：安装Python和依赖](#步骤2安装python和依赖)
- [步骤3：安装FFmpeg](#步骤3安装ffmpeg)
- [步骤4：部署项目代码](#步骤4部署项目代码)
- [步骤5：配置Ollama（可选）](#步骤5配置ollama可选)
- [步骤6：配置API密钥](#步骤6配置api密钥)
- [步骤7：测试运行](#步骤7测试运行)
- [步骤8：后台运行](#步骤8后台运行)
- [步骤9：远程访问配置](#步骤9远程访问配置)
- [故障排除](#故障排除)

## 前置要求

### 硬件要求

- **CPU**: 4核心或以上（推荐8核心）
- **内存**: 至少16GB（推荐32GB或更多）
- **GPU** (可选但推荐):
  - NVIDIA GPU: 至少12GB VRAM
  - 或使用云端API（无需GPU）
- **存储**: 至少50GB可用空间（用于模型和视频文件）

### 软件要求

- Linux操作系统（Ubuntu 20.04+ / CentOS 7+ / Debian 11+）
- Python 3.11 或更高版本
- 管理员权限（sudo）

## 步骤1：服务器环境准备

### 1.1 更新系统

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 1.2 安装基础工具

```bash
# Ubuntu/Debian
sudo apt-get install -y git curl wget build-essential

# CentOS/RHEL
sudo yum install -y git curl wget gcc gcc-c++ make
```

## 步骤2：安装Python和依赖

### 2.1 安装Python 3.11+

```bash
# Ubuntu/Debian
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# CentOS/RHEL (需要EPEL仓库)
sudo yum install -y epel-release
sudo yum install -y python311 python311-pip python311-devel
```

### 2.2 验证Python版本

```bash
python3 --version  # 应该显示 3.11 或更高
pip3 --version
```

## 步骤3：安装FFmpeg

FFmpeg是处理视频和音频的必需工具。

```bash
# Ubuntu/Debian
sudo apt-get install -y ffmpeg

# CentOS/RHEL
sudo yum install -y epel-release
sudo rpm --import https://download1.rpmfusion.org/free/el/rpmfusion-free-el-7.noarch.rpm
sudo yum install -y ffmpeg ffmpeg-devel

# 验证安装
ffmpeg -version
```

## 步骤4：部署项目代码

### 4.1 克隆或上传项目

**方法A：从GitHub克隆（推荐）**

```bash
cd /opt  # 或您选择的目录
sudo git clone https://github.com/byjlw/video-analyzer.git
sudo chown -R $USER:$USER video-analyzer
cd video-analyzer
```

**方法B：上传本地项目**

```bash
# 在本地使用scp上传
scp -r video-analyzer user@server:/opt/

# 或使用rsync
rsync -avz video-analyzer/ user@server:/opt/video-analyzer/
```

### 4.2 创建虚拟环境

```bash
cd /opt/video-analyzer
python3 -m venv venv
source venv/bin/activate
```

### 4.3 安装项目依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装项目
pip install -e .

# 或仅安装依赖
pip install -r requirements.txt
```

### 4.4 验证安装

```bash
video-analyzer --help
```

## 步骤5：配置Ollama（可选）

如果您想使用本地模型进行小模型筛选，需要安装和配置Ollama。

### 5.1 安装Ollama

```bash
# 下载并安装Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 或手动安装
# 访问 https://ollama.ai/download 获取安装脚本
```

### 5.2 下载模型

```bash
# 下载小模型（用于筛选）
ollama pull llama3.2-vision

# 验证模型
ollama list
```

### 5.3 配置Ollama服务

```bash
# 创建systemd服务文件
sudo nano /etc/systemd/system/ollama.service
```

添加以下内容：

```ini
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=ollama
Group=ollama
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
# 创建ollama用户（如果不存在）
sudo useradd -r -s /bin/false ollama

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama

# 检查状态
sudo systemctl status ollama
```

### 5.4 测试Ollama连接

```bash
curl http://localhost:11434/api/tags
```

## 步骤6：配置API密钥

### 6.1 创建配置文件

```bash
cd /opt/video-analyzer
mkdir -p config
cp config/default_config.json config/config.json
```

### 6.2 编辑配置文件

```bash
nano config/config.json
```

根据您的需求配置：

**选项A：使用本地Ollama + 云端API（推荐）**

```json
{
    "clients": {
        "default": "openai_api",
        "temperature": 0.0,
        "ollama": {
            "url": "http://localhost:11434",
            "model": "llama3.2-vision"
        },
        "openai_api": {
            "api_key": "your-api-key-here",
            "model": "qwen-vl-max",
            "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
        }
    },
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

**选项B：完全使用云端API**

```json
{
    "clients": {
        "default": "openai_api",
        "openai_api": {
            "api_key": "your-api-key-here",
            "model": "qwen-vl-max",
            "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
        }
    }
}
```

### 6.3 设置配置文件权限（安全）

```bash
chmod 600 config/config.json  # 仅所有者可读写
```

## 步骤7：测试运行

### 7.1 准备测试视频

```bash
# 创建测试目录
mkdir -p /opt/video-analyzer/test_videos

# 上传测试视频（使用scp或其他方式）
# scp test.mp4 user@server:/opt/video-analyzer/test_videos/
```

### 7.2 运行测试

```bash
cd /opt/video-analyzer
source venv/bin/activate

# 基本测试
video-analyzer test_videos/test.mp4 --max-frames 5

# 查看结果
cat output/analysis.json | python3 -m json.tool
```

## 步骤8：后台运行

### 方法A：使用systemd服务（推荐）

创建服务文件：

```bash
sudo nano /etc/systemd/system/video-analyzer.service
```

添加内容：

```ini
[Unit]
Description=Video Analyzer Service
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/opt/video-analyzer
Environment="PATH=/opt/video-analyzer/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/video-analyzer/venv/bin/video-analyzer /path/to/video.mp4
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 方法B：使用screen（简单）

```bash
# 安装screen
sudo apt-get install -y screen  # Ubuntu/Debian
sudo yum install -y screen      # CentOS/RHEL

# 创建screen会话
screen -S video-analyzer

# 在screen中运行
cd /opt/video-analyzer
source venv/bin/activate
video-analyzer /path/to/video.mp4

# 分离会话：按 Ctrl+A 然后 D
# 重新连接：screen -r video-analyzer
```

### 方法C：使用tmux

```bash
# 安装tmux
sudo apt-get install -y tmux  # Ubuntu/Debian
sudo yum install -y tmux      # CentOS/RHEL

# 创建tmux会话
tmux new -s video-analyzer

# 在tmux中运行
cd /opt/video-analyzer
source venv/bin/activate
video-analyzer /path/to/video.mp4

# 分离会话：按 Ctrl+B 然后 D
# 重新连接：tmux attach -t video-analyzer
```

### 方法D：使用nohup

```bash
cd /opt/video-analyzer
source venv/bin/activate
nohup video-analyzer /path/to/video.mp4 > output.log 2>&1 &

# 查看进程
ps aux | grep video-analyzer

# 查看日志
tail -f output.log
```

## 步骤9：远程访问配置

### 9.1 配置防火墙（如果需要）

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 5000/tcp  # 如果使用Web UI
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

### 9.2 使用Web UI（可选）

如果安装了Web UI：

```bash
# 安装Web UI
pip install video-analyzer-ui

# 后台运行Web UI
nohup video-analyzer-ui --host 0.0.0.0 --port 5000 > ui.log 2>&1 &

# 访问：http://your-server-ip:5000
```

### 9.3 使用SSH隧道访问本地服务

```bash
# 在本地机器上运行
ssh -L 5000:localhost:5000 user@server

# 然后访问 http://localhost:5000
```

## 故障排除

### 问题1：Ollama连接失败

```bash
# 检查Ollama服务状态
sudo systemctl status ollama

# 检查端口是否监听
netstat -tlnp | grep 11434

# 查看Ollama日志
sudo journalctl -u ollama -f
```

### 问题2：GPU未使用

```bash
# 检查GPU
nvidia-smi  # NVIDIA GPU
lspci | grep -i vga  # 查看所有GPU

# 检查Ollama GPU支持
ollama ps
```

### 问题3：内存不足

```bash
# 检查内存使用
free -h

# 优化配置：减少帧数
# 编辑 config/config.json，降低 max_frames_for_deep_analysis
```

### 问题4：FFmpeg未找到

```bash
# 检查FFmpeg安装
which ffmpeg
ffmpeg -version

# 如果未安装，重新安装
sudo apt-get install -y ffmpeg  # Ubuntu/Debian
```

### 问题5：Python依赖问题

```bash
# 重新安装依赖
cd /opt/video-analyzer
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### 问题6：权限问题

```bash
# 确保用户有权限访问目录
sudo chown -R $USER:$USER /opt/video-analyzer
chmod +x /opt/video-analyzer/venv/bin/video-analyzer
```

## 性能优化建议

### 1. 使用GPU加速

- 确保安装了NVIDIA驱动和CUDA
- 配置Ollama使用GPU
- 使用 `--device cuda` 参数运行Whisper

### 2. 优化配置

- 减少提取的帧数（`frames.per_minute`）
- 启用两阶段分析以节省成本
- 使用更小的Whisper模型（`small` 而不是 `large`）

### 3. 资源监控

```bash
# 监控CPU和内存
htop

# 监控GPU（NVIDIA）
watch -n 1 nvidia-smi

# 监控磁盘空间
df -h
```

## 安全建议

1. **保护API密钥**：确保 `config/config.json` 权限为 600
2. **使用防火墙**：只开放必要的端口
3. **定期更新**：保持系统和依赖包更新
4. **使用HTTPS**：如果使用Web UI，配置反向代理（Nginx）和SSL证书
5. **限制访问**：使用SSH密钥认证，禁用密码登录

## 下一步

- 查看[使用指南](USAGES.md)了解详细配置选项
- 查看[两阶段分析文档](TWO_STAGE_ANALYSIS.md)了解成本优化
- 查看[硬件兼容性文档](HARDWARE_COMPATIBILITY.md)了解硬件要求

## 常见使用场景

### 场景1：批量处理视频

```bash
#!/bin/bash
# batch_process.sh
cd /opt/video-analyzer
source venv/bin/activate

for video in /path/to/videos/*.mp4; do
    echo "Processing: $video"
    video-analyzer "$video" --output "output/$(basename $video .mp4)"
done
```

### 场景2：定时任务（cron）

```bash
# 编辑crontab
crontab -e

# 添加定时任务（每天凌晨2点处理新视频）
0 2 * * * cd /opt/video-analyzer && source venv/bin/activate && video-analyzer /path/to/video.mp4
```

### 场景3：API服务（使用Flask/FastAPI）

可以创建一个简单的API服务来接收视频分析请求，参考 `video-analyzer-ui` 的实现。

---

**需要帮助？** 查看项目文档或提交Issue。


