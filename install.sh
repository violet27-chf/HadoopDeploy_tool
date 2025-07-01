#!/bin/bash

# HadoopDeploy_tool 一键安装脚本
# 作者: violet27-chf
# 版本: 1.0.0
# 描述: 自动安装和配置HadoopDeploy_tool项目

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目信息
PROJECT_NAME="HadoopDeploy_tool"
PROJECT_VERSION="1.0.0"
GITHUB_REPO="https://github.com/violet27-chf/HadoopDeploy_tool"
INSTALL_DIR="/opt/hadoopdeploy"
SERVICE_USER="hadoopdeploy"
SERVICE_GROUP="hadoopdeploy"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# 进度条函数
show_progress() {
    local current=$1
    local total=$2
    local width=40
    local percent=$(( 100 * current / total ))
    local filled=$(( width * current / total ))
    local empty=$(( width - filled ))
    printf "\r["
    for ((i=0; i<filled; i++)); do printf "#"; done
    for ((i=0; i<empty; i++)); do printf " "; done
    printf "] %3d%%" "$percent"
}

total_steps=7  # 主要步骤数（根据实际步骤调整）
current_step=1

log_step_with_progress() {
    local msg="$1"
    show_progress $current_step $total_steps
    echo -e "  $msg"
    current_step=$((current_step+1))
}

# 显示欢迎信息
show_welcome() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    HadoopDeploy_tool                         ║"
    echo "║                    一键安装脚本                               ║"
    echo "║                                                              ║"
    echo "║  让Hadoop集群部署变得简单高效                                  ║"
    echo "║  支持全自动、半自动、手动三种部署模式                           ║"
    echo "║                                                              ║"
    echo "║  作者: violet27-chf                                          ║"
    echo "║  版本: 1.0.0                                                 ║"
    echo "║                                                              ║"
    echo "║  让Hadoop集群部署变得简单高效                                  ║"
    echo "║  支持全自动、半自动、手动三种部署模式                           ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "项目信息:"
    echo "  - 名称: $PROJECT_NAME"
    echo "  - 版本: $PROJECT_VERSION"
    echo "  - 仓库: $GITHUB_REPO"
    echo "  - 安装目录: $INSTALL_DIR"
    echo ""
    echo "此脚本将自动完成以下操作:"
    echo "  1. 检查系统环境"
    echo "  2. 安装Python和依赖"
    echo "  3. 下载项目文件"
    echo "  4. 配置环境变量"
    echo "  5. 创建系统服务"
    echo "  6. 启动Web界面"
    echo ""
    
    read -p "是否继续安装? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "安装已取消"
        exit 0
    fi
}

# 检查系统环境
check_system() {
    log_step_with_progress "检查系统环境..."
    
    # 检查操作系统
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_info "检测到Linux系统"
        if [[ -f /etc/os-release ]]; then
            . /etc/os-release
            log_info "发行版: $NAME $VERSION"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        log_info "检测到macOS系统"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    
    # 检查是否为root用户
    if [[ $EUID -eq 0 ]]; then
        log_warning "检测到root用户，建议使用普通用户运行"
    fi
    
    # 检查网络连接
    log_info "检查网络连接..."
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        log_error "网络连接失败，请检查网络设置"
        exit 1
    fi
    log_success "网络连接正常"
    
    # 检查磁盘空间
    log_info "检查磁盘空间..."
    available_space=$(df / | awk 'NR==2 {print $4}')
    required_space=1048576  # 1GB in KB
    if [[ $available_space -lt $required_space ]]; then
        log_error "磁盘空间不足，需要至少1GB可用空间"
        exit 1
    fi
    log_success "磁盘空间充足"
}

# 安装系统依赖
install_dependencies() {
    log_step_with_progress "安装系统依赖..."
    
    if [[ -f /etc/debian_version ]]; then
        # Debian/Ubuntu系统
        log_info "使用apt安装依赖..."
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv git curl wget unzip
    elif [[ -f /etc/redhat-release ]]; then
        # CentOS/RHEL系统
        log_info "使用yum安装依赖..."
        sudo yum update -y
        sudo yum install -y python3 python3-pip git curl wget unzip
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS系统
        log_info "使用Homebrew安装依赖..."
        if ! command -v brew &> /dev/null; then
            log_info "安装Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python3 git curl wget
    else
        log_error "不支持的系统，请手动安装Python3和Git"
        exit 1
    fi
    
    # 验证安装
    if ! command -v python3 &> /dev/null; then
        log_error "Python3安装失败"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        log_error "Git安装失败"
        exit 1
    fi
    
    log_success "系统依赖安装完成"
}

# 创建安装目录
create_directories() {
    log_step_with_progress "创建安装目录..."
    
    # 创建主安装目录
    sudo mkdir -p $INSTALL_DIR
    sudo chown $USER:$USER $INSTALL_DIR
    
    # 创建日志目录
    sudo mkdir -p /var/log/hadoopdeploy
    sudo chown $USER:$USER /var/log/hadoopdeploy
    
    # 创建配置目录
    sudo mkdir -p /etc/hadoopdeploy
    sudo chown $USER:$USER /etc/hadoopdeploy
    
    log_success "目录创建完成"
}

# 下载项目文件
download_project() {
    log_step_with_progress "下载项目文件..."
    
    cd $INSTALL_DIR
    
    # 检查是否已存在项目文件
    if [[ -d "HadoopDeploy_tool" ]]; then
        log_info "检测到已存在的项目文件，更新中..."
        cd HadoopDeploy_tool
        git pull origin main
    else
        log_info "克隆项目仓库..."
        git clone $GITHUB_REPO.git
        cd HadoopDeploy_tool
    fi
    
    # 检查克隆是否成功
    if [[ ! -f "app.py" ]]; then
        log_error "项目文件下载失败"
        exit 1
    fi
    
    log_success "项目文件下载完成"
}

# 安装Python依赖
install_python_deps() {
    log_step_with_progress "安装Python依赖..."
    
    cd $INSTALL_DIR/HadoopDeploy_tool
    
    # 创建虚拟环境
    log_info "创建Python虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    log_info "安装Python包..."
    pip install flask paramiko jinja2
    
    # 验证安装
    if ! python3 -c "import flask, paramiko" 2>/dev/null; then
        log_error "Python依赖安装失败"
        exit 1
    fi
    
    log_success "Python依赖安装完成"
}

# 配置环境变量
setup_environment() {
    log_step_with_progress "配置环境变量..."
    
    # 创建环境变量文件
    cat > $INSTALL_DIR/HadoopDeploy_tool/.env << EOF
# HadoopDeploy_tool 环境配置
HADOOPDEPLOY_HOME=$INSTALL_DIR/HadoopDeploy_tool
HADOOPDEPLOY_LOG=/var/log/hadoopdeploy
HADOOPDEPLOY_CONFIG=/etc/hadoopdeploy
FLASK_ENV=production
FLASK_DEBUG=0
EOF
    
    # 添加到用户环境变量
    if [[ -f ~/.bashrc ]]; then
        echo "" >> ~/.bashrc
        echo "# HadoopDeploy_tool 环境变量" >> ~/.bashrc
        echo "export HADOOPDEPLOY_HOME=$INSTALL_DIR/HadoopDeploy_tool" >> ~/.bashrc
        echo "export PATH=\$PATH:\$HADOOPDEPLOY_HOME" >> ~/.bashrc
    fi
    
    if [[ -f ~/.zshrc ]]; then
        echo "" >> ~/.zshrc
        echo "# HadoopDeploy_tool 环境变量" >> ~/.zshrc
        echo "export HADOOPDEPLOY_HOME=$INSTALL_DIR/HadoopDeploy_tool" >> ~/.zshrc
        echo "export PATH=\$PATH:\$HADOOPDEPLOY_HOME" >> ~/.zshrc
    fi
    
    log_success "环境变量配置完成"
}

# 创建启动脚本
create_startup_script() {
    log_step_with_progress "创建启动脚本..."
    
    cat > $INSTALL_DIR/HadoopDeploy_tool/start.sh << 'EOF'
#!/bin/bash

# HadoopDeploy_tool 启动脚本

set -e

# 加载环境变量
if [[ -f .env ]]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 激活虚拟环境
source venv/bin/activate

# 检查端口是否被占用
PORT=${1:-5000}
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "端口 $PORT 已被占用，请使用其他端口"
    exit 1
fi

# 启动应用
echo "启动 HadoopDeploy_tool..."
echo "访问地址: http://localhost:$PORT"
echo "按 Ctrl+C 停止服务"

python app.py --port $PORT
EOF
    
    chmod +x $INSTALL_DIR/HadoopDeploy_tool/start.sh
    
    log_success "启动脚本创建完成"
}

# 创建系统服务
create_systemd_service() {
    log_step_with_progress "创建系统服务..."
    
    # 检查是否为root用户
    if [[ $EUID -ne 0 ]]; then
        log_warning "需要root权限创建系统服务，跳过此步骤"
        return
    fi
    
    cat > /etc/systemd/system/hadoopdeploy.service << EOF
[Unit]
Description=HadoopDeploy_tool Web Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR/HadoopDeploy_tool
Environment=PATH=$INSTALL_DIR/HadoopDeploy_tool/venv/bin
ExecStart=$INSTALL_DIR/HadoopDeploy_tool/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # 重新加载systemd
    systemctl daemon-reload
    
    # 启用服务
    systemctl enable hadoopdeploy.service
    
    log_success "系统服务创建完成"
}

# 配置防火墙
configure_firewall() {
    log_step_with_progress "配置防火墙..."
    
    # 检查是否为root用户
    if [[ $EUID -ne 0 ]]; then
        log_warning "需要root权限配置防火墙，跳过此步骤"
        return
    fi
    
    # 检测防火墙类型
    if command -v ufw &> /dev/null; then
        # Ubuntu防火墙
        ufw allow 5000/tcp
        log_info "Ubuntu防火墙已配置"
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS防火墙
        firewall-cmd --permanent --add-port=5000/tcp
        firewall-cmd --reload
        log_info "CentOS防火墙已配置"
    else
        log_warning "未检测到支持的防火墙，请手动开放5000端口"
    fi
}

# 创建卸载脚本
create_uninstall_script() {
    log_step_with_progress "创建卸载脚本..."
    
    cat > $INSTALL_DIR/uninstall.sh << 'EOF'
#!/bin/bash

# HadoopDeploy_tool 卸载脚本

set -e

echo "开始卸载 HadoopDeploy_tool..."

# 停止服务
if systemctl is-active --quiet hadoopdeploy.service; then
    sudo systemctl stop hadoopdeploy.service
    sudo systemctl disable hadoopdeploy.service
fi

# 删除服务文件
if [[ -f /etc/systemd/system/hadoopdeploy.service ]]; then
    sudo rm /etc/systemd/system/hadoopdeploy.service
    sudo systemctl daemon-reload
fi

# 删除安装目录
if [[ -d /opt/hadoopdeploy ]]; then
    sudo rm -rf /opt/hadoopdeploy
fi

# 删除日志目录
if [[ -d /var/log/hadoopdeploy ]]; then
    sudo rm -rf /var/log/hadoopdeploy
fi

# 删除配置目录
if [[ -d /etc/hadoopdeploy ]]; then
    sudo rm -rf /etc/hadoopdeploy
fi

echo "HadoopDeploy_tool 卸载完成"
EOF
    
    chmod +x $INSTALL_DIR/uninstall.sh
    
    log_success "卸载脚本创建完成"
}

# 显示安装完成信息
show_completion() {
    log_step_with_progress "安装完成！"
    
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                   安装完成！                                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo "项目信息:"
    echo "  - 安装目录: $INSTALL_DIR"
    echo "  - 配置文件: /etc/hadoopdeploy"
    echo "  - 日志目录: /var/log/hadoopdeploy"
    echo ""
    
    echo "启动方式:"
    echo "  1. 手动启动:"
    echo "     cd $INSTALL_DIR/HadoopDeploy_tool"
    echo "     ./start.sh"
    echo ""
    echo "  2. 系统服务启动:"
    echo "     sudo systemctl start hadoopdeploy"
    echo "     sudo systemctl enable hadoopdeploy"
    echo ""
    
    echo "访问地址:"
    echo "  - 本地访问: http://localhost:5000"
    echo "  - 远程访问: http://$(hostname -I | awk '{print $1}'):5000"
    echo ""
    
    echo "管理命令:"
    echo "  - 启动服务: sudo systemctl start hadoopdeploy"
    echo "  - 停止服务: sudo systemctl stop hadoopdeploy"
    echo "  - 重启服务: sudo systemctl restart hadoopdeploy"
    echo "  - 查看状态: sudo systemctl status hadoopdeploy"
    echo "  - 查看日志: sudo journalctl -u hadoopdeploy -f"
    echo ""
    
    echo "卸载方式:"
    echo "  sudo $INSTALL_DIR/uninstall.sh"
    echo ""
    
    echo "文档和帮助:"
    echo "  - GitHub: $GITHUB_REPO"
    echo "  - 问题反馈: $GITHUB_REPO/issues"
    echo ""
    
    log_success "感谢使用 HadoopDeploy_tool！"
}

# 主安装流程
main() {
    # 检查是否为root用户（可选）
    if [[ $EUID -eq 0 ]]; then
        log_warning "检测到root用户运行，建议使用普通用户"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
    
    # 显示欢迎信息
    show_welcome
    
    # 执行安装步骤
    check_system
    install_dependencies
    create_directories
    download_project
    install_python_deps
    setup_environment
    create_startup_script
    create_systemd_service
    configure_firewall
    create_uninstall_script
    
    # 显示完成信息
    show_completion
}

# 错误处理
trap 'log_error "安装过程中发生错误，请检查日志"; exit 1' ERR

# 脚本入口
main "$@"

# 安装结束后显示100%进度
show_progress $total_steps $total_steps
printf "  安装完成！\n" 