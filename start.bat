@echo off
REM Hadoop一键启动脚本（Windows）
REM 需提前配置好JAVA_HOME/HADOOP_HOME，建议以管理员身份运行

REM 1. 加载环境变量
setlocal
if exist "%USERPROFILE%\.hadoop_env" (
    call "%USERPROFILE%\.hadoop_env"
) else (
    call "%HADOOP_HOME%\etc\hadoop\hadoop-env.cmd"
)

REM 2. 启动HDFS
call "%HADOOP_HOME%\sbin\start-dfs.cmd"

REM 3. 启动YARN
call "%HADOOP_HOME%\sbin\start-yarn.cmd"

REM 4. 打印进程状态
jps

echo.
echo Hadoop集群已启动。可用jps命令查看NameNode、DataNode、ResourceManager、NodeManager等进程。
pause 