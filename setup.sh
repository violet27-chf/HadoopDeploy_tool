#!/bin/bash

# Hadoop部署系统安装脚本 (Linux/macOS)

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查Python版本
check_python() {
    log_info "检查Python版本..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python3，请先安装Python 3.8+"
        log_info "Ubuntu/Debian: sudo apt-get install python3 python3-venv python3-pip"
        log_info "CentOS/RHEL: sudo yum install python3 python3-pip"
        log_info "macOS: brew install python3"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_success "Python版本：$PYTHON_VERSION"
    
    # 检查版本是否满足要求
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_success "Python版本满足要求"
    else
        log_error "需要Python 3.8或更高版本"
        exit 1
    fi
}

# 检查系统要求
check_system() {
    log_info "检查系统要求..."
    
    # 检查内存
    if command -v free &> /dev/null; then
        MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
        log_info "系统内存：${MEMORY_GB}GB"
        
        if [ "$MEMORY_GB" -lt 4 ]; then
            log_warning "系统内存不足4GB，可能影响性能"
        fi
    fi
    
    # 检查磁盘空间
    DISK_SPACE=$(df . | awk 'NR==2 {print $4}')
    DISK_SPACE_GB=$((DISK_SPACE / 1024 / 1024))
    log_info "可用磁盘空间：${DISK_SPACE_GB}GB"
    
    if [ "$DISK_SPACE_GB" -lt 10 ]; then
        log_warning "磁盘空间不足10GB"
    fi
}

# 创建虚拟环境
create_venv() {
    log_info "创建虚拟环境..."
    
    if [ -d "venv" ]; then
        log_warning "虚拟环境已存在，跳过创建"
        return
    fi
    
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        log_success "虚拟环境创建成功"
    else
        log_error "虚拟环境创建失败"
        exit 1
    fi
}

# 激活虚拟环境
activate_venv() {
    log_info "激活虚拟环境..."
    source venv/bin/activate
    
    if [ $? -eq 0 ]; then
        log_success "虚拟环境激活成功"
    else
        log_error "虚拟环境激活失败"
        exit 1
    fi
}

# 安装依赖
install_dependencies() {
    log_info "安装项目依赖..."
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        log_success "依赖安装完成"
    else
        log_error "依赖安装失败"
        log_info "尝试使用国内镜像源："
        log_info "pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/"
        exit 1
    fi
}

# 创建目录
create_directories() {
    log_info "创建必要目录..."
    
    directories=("uploads" "logs" "temp")
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_success "创建目录：$dir"
        else
            log_info "目录已存在：$dir"
        fi
    done
}

# 创建配置文件
create_config() {
    log_info "创建配置文件..."
    
    if [ ! -f "config.ini" ]; then
        cat > config.ini << EOF
# Hadoop部署系统配置文件
[app]
debug = true
host = 0.0.0.0
port = 5000

[upload]
max_file_size = 2147483648  # 2GB
allowed_extensions = .tar.gz,.tgz,.zip

[deploy]
timeout = 300
log_level = INFO
EOF
        log_success "配置文件创建成功：config.ini"
    else
        log_info "配置文件已存在：config.ini"
    fi
}

# 设置权限
set_permissions() {
    log_info "设置文件权限..."
    
    # 设置脚本执行权限
    chmod +x setup.sh
    chmod +x scripts/*.sh
    
    log_success "权限设置完成"
}

# 显示完成信息
show_completion() {
    echo
    echo "================================================"
    log_success "安装完成！"
    echo
    echo "📋 下一步操作："
    echo "1. 激活虚拟环境："
    echo "   source venv/bin/activate"
    echo
    echo "2. 启动应用："
    echo "   python app.py"
    echo
    echo "3. 访问Web界面："
    echo "   http://localhost:5000"
    echo
    echo "📖 更多信息请查看 README.md"
    echo
}

# 主函数
main() {
    echo "🚀 Hadoop部署系统安装程序"
    echo "================================================"
    
    # 检查Python
    check_python
    
    # 检查系统要求
    check_system
    
    # 创建虚拟环境
    create_venv
    
    # 激活虚拟环境
    activate_venv
    
    # 安装依赖
    install_dependencies
    
    # 创建目录
    create_directories
    
    # 创建配置文件
    create_config
    
    # 设置权限
    set_permissions
    
    # 显示完成信息
    show_completion
}

# 执行主函数
main "$@" 