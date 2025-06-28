@echo off
REM Hadoop多服务器环境一键快速安装脚本（Windows版）
REM 需以管理员身份运行

REM 1. 检查并安装OpenSSH（Windows 10/11自带）
where ssh >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到OpenSSH，请在"可选功能"中安装"OpenSSH Client"！
    pause
    exit /b
)

REM 2. 检查并安装Java（需手动或用choco）
where java >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到Java，请先手动安装Java 8或以上版本！
    pause
    exit /b
)

REM 3. 配置JAVA_HOME环境变量
for /f "delims=" %%i in ('where java') do set JAVA_PATH=%%i
set JAVA_HOME=%JAVA_PATH%\..\..
setx JAVA_HOME "%JAVA_HOME%"
setx PATH "%PATH%;%JAVA_HOME%\bin"

REM 4. 获取本机IP和主机名
for /f "tokens=2 delims=: " %%i in ('ipconfig ^| findstr /i "IPv4"') do set IP=%%i
set IP=%IP:~1%
set HOSTNAME=%COMPUTERNAME%

REM 5. 写入hosts文件
findstr /C:"%IP% %HOSTNAME%" %SystemRoot%\System32\drivers\etc\hosts >nul 2>nul
if %errorlevel% neq 0 (
    echo %IP% %HOSTNAME%>>%SystemRoot%\System32\drivers\etc\hosts
)

REM 6. 下载并解压Hadoop
set HADOOP_VERSION=3.3.6
set INSTALL_DIR=%SystemDrive%\hadoop
set HADOOP_HOME=%INSTALL_DIR%\hadoop-%HADOOP_VERSION%
if not exist %HADOOP_HOME% (
    mkdir %INSTALL_DIR%
    powershell -Command "Invoke-WebRequest -Uri https://mirrors.aliyun.com/apache/hadoop/common/hadoop-%HADOOP_VERSION%/hadoop-%HADOOP_VERSION%.tar.gz -OutFile %INSTALL_DIR%\hadoop-%HADOOP_VERSION%.tar.gz"
    powershell -Command "tar -xzf %INSTALL_DIR%\hadoop-%HADOOP_VERSION%.tar.gz -C %INSTALL_DIR%"
)

REM 7. 配置HADOOP_HOME环境变量
setx HADOOP_HOME "%HADOOP_HOME%"
setx PATH "%PATH%;%HADOOP_HOME%\bin;%HADOOP_HOME%\sbin"

REM 8. 生成SSH密钥对（如无）
if not exist %USERPROFILE%\.ssh\id_rsa (
    powershell -Command "ssh-keygen -t rsa -N '' -f $env:USERPROFILE\.ssh\id_rsa"
)

REM 9. 完成提示
cls
echo.
echo Hadoop环境基础依赖已检测，JAVA_HOME/HADOOP_HOME已配置，主机名与hosts已同步。
echo 如需多节点免密，请将 %USERPROFILE%\.ssh\id_rsa.pub 内容追加到所有节点的 %USERPROFILE%\.ssh\authorized_keys。
echo Hadoop目录：%HADOOP_HOME%
echo 请重启命令行窗口以生效环境变量。
pause 