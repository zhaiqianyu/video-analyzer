#!/bin/bash
# 服务器快速部署脚本
# 使用方法: bash scripts/server_setup.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "视频分析工具 - 服务器部署脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}请不要使用root用户运行此脚本${NC}"
   exit 1
fi

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo -e "${RED}无法检测操作系统${NC}"
    exit 1
fi

echo -e "${GREEN}检测到操作系统: $OS $VER${NC}"

# 项目目录
PROJECT_DIR="/opt/video-analyzer"
CURRENT_DIR=$(pwd)

# 函数：检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 函数：安装Python
install_python() {
    echo -e "${YELLOW}正在安装Python 3.11+...${NC}"
    
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt-get update
        sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        sudo yum install -y epel-release
        sudo yum install -y python311 python311-pip python311-devel
    else
        echo -e "${RED}不支持的操作系统: $OS${NC}"
        exit 1
    fi
    
    # 验证安装
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version)
        echo -e "${GREEN}Python安装成功: $PYTHON_VERSION${NC}"
    else
        echo -e "${RED}Python安装失败${NC}"
        exit 1
    fi
}

# 函数：安装FFmpeg
install_ffmpeg() {
    echo -e "${YELLOW}正在安装FFmpeg...${NC}"
    
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt-get install -y ffmpeg
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        sudo yum install -y epel-release
        sudo rpm --import https://download1.rpmfusion.org/free/el/rpmfusion-free-el-7.noarch.rpm
        sudo yum install -y ffmpeg ffmpeg-devel
    fi
    
    if command_exists ffmpeg; then
        echo -e "${GREEN}FFmpeg安装成功${NC}"
        ffmpeg -version | head -n 1
    else
        echo -e "${RED}FFmpeg安装失败${NC}"
        exit 1
    fi
}

# 函数：安装Ollama
install_ollama() {
    echo -e "${YELLOW}正在安装Ollama...${NC}"
    
    if command_exists ollama; then
        echo -e "${GREEN}Ollama已安装${NC}"
    else
        echo -e "${YELLOW}下载并安装Ollama...${NC}"
        curl -fsSL https://ollama.ai/install.sh | sh
        
        # 创建systemd服务
        if [ ! -f /etc/systemd/system/ollama.service ]; then
            echo -e "${YELLOW}配置Ollama服务...${NC}"
            sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
            sudo systemctl daemon-reload
            sudo systemctl enable ollama
            sudo systemctl start ollama
            echo -e "${GREEN}Ollama服务已启动${NC}"
        fi
    fi
    
    # 下载模型
    echo -e "${YELLOW}下载llama3.2-vision模型（这可能需要一些时间）...${NC}"
    ollama pull llama3.2-vision || echo -e "${YELLOW}模型下载失败，您可以稍后手动运行: ollama pull llama3.2-vision${NC}"
}

# 函数：部署项目
deploy_project() {
    echo -e "${YELLOW}正在部署项目...${NC}"
    
    # 如果项目不在/opt，询问是否移动
    if [ "$CURRENT_DIR" != "$PROJECT_DIR" ]; then
        read -p "是否将项目部署到 $PROJECT_DIR? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo mkdir -p /opt
            if [ -d "$PROJECT_DIR" ]; then
                echo -e "${YELLOW}目录已存在，更新代码...${NC}"
                cd "$PROJECT_DIR"
                git pull || echo -e "${YELLOW}无法更新，请手动检查${NC}"
            else
                echo -e "${YELLOW}复制项目到 $PROJECT_DIR...${NC}"
                sudo cp -r "$CURRENT_DIR" "$PROJECT_DIR"
                sudo chown -R $USER:$USER "$PROJECT_DIR"
            fi
            cd "$PROJECT_DIR"
        else
            PROJECT_DIR="$CURRENT_DIR"
            echo -e "${YELLOW}使用当前目录: $PROJECT_DIR${NC}"
        fi
    fi
    
    # 创建虚拟环境
    if [ ! -d "$PROJECT_DIR/venv" ]; then
        echo -e "${YELLOW}创建Python虚拟环境...${NC}"
        python3 -m venv "$PROJECT_DIR/venv"
    fi
    
    # 激活虚拟环境并安装依赖
    echo -e "${YELLOW}安装项目依赖...${NC}"
    source "$PROJECT_DIR/venv/bin/activate"
    pip install --upgrade pip
    pip install -e "$PROJECT_DIR"
    
    echo -e "${GREEN}项目部署完成${NC}"
}

# 函数：创建配置文件
create_config() {
    echo -e "${YELLOW}创建配置文件...${NC}"
    
    CONFIG_DIR="$PROJECT_DIR/config"
    mkdir -p "$CONFIG_DIR"
    
    if [ ! -f "$CONFIG_DIR/config.json" ]; then
        if [ -f "$CONFIG_DIR/default_config.json" ]; then
            cp "$CONFIG_DIR/default_config.json" "$CONFIG_DIR/config.json"
            echo -e "${GREEN}配置文件已创建: $CONFIG_DIR/config.json${NC}"
            echo -e "${YELLOW}请编辑配置文件并添加您的API密钥${NC}"
        else
            echo -e "${YELLOW}创建默认配置文件...${NC}"
            cat > "$CONFIG_DIR/config.json" <<EOF
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
EOF
            echo -e "${GREEN}配置文件已创建${NC}"
        fi
    else
        echo -e "${YELLOW}配置文件已存在，跳过创建${NC}"
    fi
    
    chmod 600 "$CONFIG_DIR/config.json"
}

# 函数：验证安装
verify_installation() {
    echo -e "${YELLOW}验证安装...${NC}"
    
    source "$PROJECT_DIR/venv/bin/activate"
    
    # 检查命令
    if command_exists video-analyzer; then
        echo -e "${GREEN}✓ video-analyzer 命令可用${NC}"
        video-analyzer --help | head -n 5
    else
        echo -e "${RED}✗ video-analyzer 命令不可用${NC}"
    fi
    
    # 检查Ollama
    if command_exists ollama; then
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Ollama 服务运行正常${NC}"
        else
            echo -e "${YELLOW}⚠ Ollama 服务未运行，请运行: sudo systemctl start ollama${NC}"
        fi
    fi
    
    # 检查FFmpeg
    if command_exists ffmpeg; then
        echo -e "${GREEN}✓ FFmpeg 已安装${NC}"
    else
        echo -e "${RED}✗ FFmpeg 未安装${NC}"
    fi
}

# 主函数
main() {
    echo -e "${GREEN}开始部署...${NC}"
    
    # 检查Python
    if ! command_exists python3; then
        install_python
    else
        PYTHON_VERSION=$(python3 --version)
        echo -e "${GREEN}Python已安装: $PYTHON_VERSION${NC}"
    fi
    
    # 检查FFmpeg
    if ! command_exists ffmpeg; then
        install_ffmpeg
    else
        echo -e "${GREEN}FFmpeg已安装${NC}"
    fi
    
    # 询问是否安装Ollama
    read -p "是否安装Ollama（用于本地模型）? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_ollama
    else
        echo -e "${YELLOW}跳过Ollama安装${NC}"
    fi
    
    # 部署项目
    deploy_project
    
    # 创建配置
    create_config
    
    # 验证
    verify_installation
    
    echo ""
    echo -e "${GREEN}=========================================="
    echo "部署完成！"
    echo "==========================================${NC}"
    echo ""
    echo "下一步："
    echo "1. 编辑配置文件: nano $PROJECT_DIR/config/config.json"
    echo "2. 添加您的API密钥"
    echo "3. 测试运行: cd $PROJECT_DIR && source venv/bin/activate && video-analyzer test.mp4 --max-frames 5"
    echo ""
    echo "详细文档请查看: docs/SERVER_DEPLOYMENT.md"
}

# 运行主函数
main


