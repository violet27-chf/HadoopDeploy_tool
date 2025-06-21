@echo off
chcp 65001 >nul
echo 🚀 Hadoop部署系统安装程序
echo ================================================

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python，请先安装Python 3.8+
    echo 📥 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python已安装
python --version

:: 检查Python版本
for /f "tokens=2" %%i in ('python -c "import sys; print(sys.version.split()[0])"') do set PYTHON_VERSION=%%i
echo 📋 Python版本：%PYTHON_VERSION%

:: 创建虚拟环境
if exist venv (
    echo ⚠️  虚拟环境已存在，跳过创建
) else (
    echo 🔧 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo ✅ 虚拟环境创建成功
)

:: 激活虚拟环境
echo 🔄 激活虚拟环境...
call venv\Scripts\activate.bat

:: 升级pip
echo 📦 升级pip...
python -m pip install --upgrade pip

:: 安装依赖
echo 📦 安装项目依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 依赖安装失败
    echo 💡 尝试使用国内镜像源：
    echo pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
    pause
    exit /b 1
)

:: 创建必要目录
echo 📁 创建必要目录...
if not exist uploads mkdir uploads
if not exist logs mkdir logs
if not exist temp mkdir temp

:: 创建配置文件
if not exist config.ini (
    echo 📝 创建配置文件...
    (
        echo # Hadoop部署系统配置文件
        echo [app]
        echo debug = true
        echo host = 0.0.0.0
        echo port = 5000
        echo.
        echo [upload]
        echo max_file_size = 2147483648
        echo allowed_extensions = .tar.gz,.tgz,.zip
        echo.
        echo [deploy]
        echo timeout = 300
        echo log_level = INFO
    ) > config.ini
    echo ✅ 配置文件创建成功
)

echo.
echo ================================================
echo 🎉 安装完成！
echo.
echo 📋 下一步操作：
echo 1. 激活虚拟环境：
echo    venv\Scripts\activate
echo.
echo 2. 启动应用：
echo    python app.py
echo.
echo 3. 访问Web界面：
echo    http://localhost:5000
echo.
echo 📖 更多信息请查看 README.md
echo.
pause 