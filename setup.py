#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hadoop部署系统安装脚本
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 错误：需要Python 3.8或更高版本")
        print(f"当前版本：{sys.version}")
        sys.exit(1)
    print(f"✅ Python版本检查通过：{sys.version}")

def create_directories():
    """创建必要的目录"""
    directories = ['uploads', 'logs', 'temp']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ 创建目录：{directory}")

def install_dependencies():
    """安装依赖包"""
    print("📦 安装项目依赖...")
    
    try:
        # 升级pip
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
        
        # 安装依赖
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败：{e}")
        return False

def create_virtual_env():
    """创建虚拟环境"""
    print("🔧 创建虚拟环境...")
    
    try:
        # 检查是否已存在虚拟环境
        if Path('venv').exists():
            print("⚠️  虚拟环境已存在，跳过创建")
            return True
        
        # 创建虚拟环境
        subprocess.check_call([sys.executable, '-m', 'venv', 'venv'])
        print("✅ 虚拟环境创建成功")
        
        # 显示激活命令
        if platform.system() == "Windows":
            print("📝 激活虚拟环境命令：venv\\Scripts\\activate")
        else:
            print("📝 激活虚拟环境命令：source venv/bin/activate")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 虚拟环境创建失败：{e}")
        return False

def check_system_requirements():
    """检查系统要求"""
    print("🔍 检查系统要求...")
    
    # 检查内存
    try:
        import psutil
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        print(f"✅ 系统内存：{memory_gb:.1f}GB")
        
        if memory_gb < 4:
            print("⚠️  警告：系统内存不足4GB，可能影响性能")
    except ImportError:
        print("⚠️  无法检查内存信息（需要psutil包）")
    
    # 检查磁盘空间
    try:
        disk_usage = psutil.disk_usage('.')
        disk_gb = disk_usage.free / (1024**3)
        print(f"✅ 可用磁盘空间：{disk_gb:.1f}GB")
        
        if disk_gb < 10:
            print("⚠️  警告：磁盘空间不足10GB")
    except ImportError:
        print("⚠️  无法检查磁盘空间（需要psutil包）")

def create_config_file():
    """创建配置文件"""
    config_content = """# Hadoop部署系统配置文件
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
"""
    
    config_file = Path('config.ini')
    if not config_file.exists():
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print("✅ 配置文件创建成功：config.ini")

def main():
    """主函数"""
    print("🚀 Hadoop部署系统安装程序")
    print("=" * 50)
    
    # 检查Python版本
    check_python_version()
    
    # 检查系统要求
    check_system_requirements()
    
    # 创建虚拟环境
    if not create_virtual_env():
        sys.exit(1)
    
    # 创建目录
    create_directories()
    
    # 安装依赖
    if not install_dependencies():
        sys.exit(1)
    
    # 创建配置文件
    create_config_file()
    
    print("\n" + "=" * 50)
    print("🎉 安装完成！")
    print("\n📋 下一步操作：")
    print("1. 激活虚拟环境：")
    if platform.system() == "Windows":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("2. 启动应用：")
    print("   python app.py")
    print("3. 访问Web界面：")
    print("   http://localhost:5000")
    print("\n📖 更多信息请查看 README.md")

if __name__ == '__main__':
    main() 