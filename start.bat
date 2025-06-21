@echo off
chcp 65001 >nul
echo 🚀 Hadoop部署系统启动程序
echo ================================================

:: 检查虚拟环境是否存在
if not exist venv (
    echo ❌ 虚拟环境不存在，请先运行安装程序
    echo 📝 运行命令：setup.bat
    pause
    exit /b 1
)

:: 激活虚拟环境
echo 🔄 激活虚拟环境...
call venv\Scripts\activate.bat

:: 检查依赖是否安装
python -c "import flask, paramiko" >nul 2>&1
if errorlevel 1 (
    echo ❌ 依赖未安装，正在安装...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
)

:: 创建必要目录
if not exist uploads mkdir uploads
if not exist logs mkdir logs

:: 启动应用
echo 🚀 启动Hadoop部署系统...
echo 📍 访问地址：http://localhost:5000
echo 📝 按 Ctrl+C 停止服务
echo.

python app.py

pause 