#!/bin/bash

# Hadoop部署系统启动脚本 (Linux/macOS)

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

# 检查虚拟环境
check_venv() {
    if [ ! -d "venv" ]; then
        log_error "虚拟环境不存在，请先运行安装程序"
        log_info "运行命令：./setup.sh"
        exit 1
    fi
}

# 激活虚拟环境
activate_venv() {
    log_info "激活虚拟环境..."
    source venv/bin/activate
    
    if [ $? -ne 0 ]; then
        log_error "虚拟环境激活失败"
        exit 1
    fi
    
    log_success "虚拟环境激活成功"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    if ! python -c "import flask, paramiko" &> /dev/null; then
        log_warning "依赖未安装，正在安装..."
        pip install -r requirements.txt
        
        if [ $? -ne 0 ]; then
            log_error "依赖安装失败"
            exit 1
        fi
        
        log_success "依赖安装完成"
    else
        log_success "依赖检查通过"
    fi
}

# 创建目录
create_directories() {
    log_info "创建必要目录..."
    
    directories=("uploads" "logs")
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_success "创建目录：$dir"
        fi
    done
}

# 启动应用
start_app() {
    log_info "启动Hadoop部署系统..."
    log_success "访问地址：http://localhost:5000"
    log_info "按 Ctrl+C 停止服务"
    echo
    
    python app.py
}

# 主函数
main() {
    echo "🚀 Hadoop部署系统启动程序"
    echo "================================================"
    
    # 检查虚拟环境
    check_venv
    
    # 激活虚拟环境
    activate_venv
    
    # 检查依赖
    check_dependencies
    
    # 创建目录
    create_directories
    
    # 启动应用
    start_app
}

# 执行主函数
main "$@" 