@echo off
echo 开始打包Hadoop部署系统...

REM 下载便携版Python（如3.9.13）
if not exist python-3.9.13-embed-amd64.zip (
  echo 下载便携版Python...
  curl -LO https://www.python.org/ftp/python/3.9.13/python-3.9.13-embed-amd64.zip
)

REM 解压到python目录
if not exist python (
  echo 解压Python环境...
  powershell -Command "Expand-Archive -Path python-3.9.13-embed-amd64.zip -DestinationPath python"
)

REM 下载get-pip.py
if not exist get-pip.py (
  echo 下载pip安装脚本...
  curl -LO https://bootstrap.pypa.io/get-pip.py
)

REM 复制依赖和项目文件
echo 复制项目文件...
xcopy templates python\templates /E /I /Y
xcopy static python\static /E /I /Y
copy app.py python\
copy requirements.txt python\
copy start.bat python\
copy get-pip.py python\

REM 安装pip和依赖
echo 安装pip和Python依赖...
cd python
python.exe get-pip.py
python.exe -m pip install -r requirements.txt
cd ..

REM 清理临时文件
del get-pip.py

REM 打包为zip
echo 创建压缩包...
powershell Compress-Archive -Path python\* -DestinationPath HadoopDeploy_withPython.zip -Force

echo 打包完成：HadoopDeploy_withPython.zip
pause 