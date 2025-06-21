#!/bin/bash

# Hadoop单节点自动部署脚本
# 支持多服务器批量部署

# 获取服务器标识(从文件名获取)
SCRIPT_NAME=$(basename "$0")
SERVER_ID=${SCRIPT_NAME//[^0-9]/}
[ -z "$SERVER_ID" ] && SERVER_ID=1

# 定义变量
JAVA_HOME_PATH="/usr/lib/jvm/java-8-openjdk-amd64"
HADOOP_VERSION="3.3.4"
HADOOP_URL="https://downloads.apache.org/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz"
INSTALL_DIR="/opt/hadoop_${SERVER_ID}"  # 为每个服务器添加唯一标识

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Server ${SERVER_ID}] $1"
}

# 检查Java是否安装
log "开始部署Hadoop单节点"
log "检查Java安装..."
if ! command -v java &> /dev/null; then
    echo "Java未安装，尝试安装OpenJDK 8..."
    sudo apt-get update && sudo apt-get install -y openjdk-8-jdk
    if [ $? -ne 0 ]; then
        echo "Java安装失败，请手动安装后再试"
        exit 1
    fi
else
    echo "Java已安装"
fi

# 设置Java环境变量
echo "设置Java环境变量..."
export JAVA_HOME=${JAVA_HOME_PATH}
echo "export JAVA_HOME=${JAVA_HOME}" >> ~/.bashrc
echo "export PATH=\$PATH:\$JAVA_HOME/bin" >> ~/.bashrc
source ~/.bashrc

# 下载并安装Hadoop
echo "开始安装Hadoop..."
sudo mkdir -p ${INSTALL_DIR}
cd /tmp
wget ${HADOOP_URL}
sudo tar -xzf hadoop-${HADOOP_VERSION}.tar.gz -C ${INSTALL_DIR} --strip-components=1
sudo chown -R $(whoami):$(whoami) ${INSTALL_DIR}

# 配置Hadoop环境变量
echo "配置Hadoop环境变量..."
echo "export HADOOP_HOME=${INSTALL_DIR}" >> ~/.bashrc
echo "export PATH=\$PATH:\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin" >> ~/.bashrc
source ~/.bashrc

# 计算唯一端口(基础端口+服务器ID)
BASE_PORT=9000
PORT_OFFSET=$((SERVER_ID - 1))
HDFS_PORT=$((BASE_PORT + PORT_OFFSET))

# 创建数据目录
DATA_DIR="/hadoop_data_${SERVER_ID}"
log "创建数据目录: ${DATA_DIR}"
sudo mkdir -p ${DATA_DIR}
sudo chown -R $(whoami):$(whoami) ${DATA_DIR}

# 基本配置
log "配置Hadoop..."
cat > ${INSTALL_DIR}/etc/hadoop/core-site.xml <<EOL
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://localhost:${HDFS_PORT}</value>
    </property>
    <property>
        <name>hadoop.tmp.dir</name>
        <value>${DATA_DIR}</value>
    </property>
</configuration>
EOL

cat > ${INSTALL_DIR}/etc/hadoop/hdfs-site.xml <<EOL
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>file://${DATA_DIR}/namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>file://${DATA_DIR}/datanode</value>
    </property>
</configuration>
EOL

log "格式化HDFS..."
hdfs namenode -format

log "启动Hadoop服务..."
start-dfs.sh

# 添加环境变量到用户profile
log "设置环境变量..."
echo "export HADOOP_HOME=${INSTALL_DIR}" >> ~/.bashrc
echo "export PATH=\$PATH:\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin" >> ~/.bashrc
source ~/.bashrc

log "Hadoop单节点部署完成!"
log "HDFS访问端口: ${HDFS_PORT}"
log "数据目录: ${DATA_DIR}"
log "安装目录: ${INSTALL_DIR}"