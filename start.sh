#!/bin/bash
# Hadoop一键启动脚本（Linux）
# 需提前配置好JAVA_HOME/HADOOP_HOME

set -e

# 1. 加载环境变量
if [ -f ~/.hadoop_env ]; then
    source ~/.hadoop_env
elif [ -f /etc/profile ]; then
    source /etc/profile
fi

# 2. 启动HDFS
$HADOOP_HOME/sbin/start-dfs.sh

# 3. 启动YARN
$HADOOP_HOME/sbin/start-yarn.sh

# 4. 打印进程状态
jps

echo "\nHadoop集群已启动。可用jps命令查看NameNode、DataNode、ResourceManager、NodeManager等进程。" 