@echo off
setlocal

REM 设置Inno Setup编译器路径（如有不同请修改）
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

REM 编译安装包
%ISCC% installer.iss

pause 