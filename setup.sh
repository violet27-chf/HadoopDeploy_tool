#!/bin/bash
# Hadoop多服务器环境一键快速安装脚本
# 适用：CentOS/Ubuntu，需root权限

set -e

# 1. 关闭防火墙
if systemctl status firewalld &>/dev/null; then
    systemctl stop firewalld
    systemctl disable firewalld
fi
if systemctl status ufw &>/dev/null; then
    ufw disable
fi

# 2. 安装常用依赖
if command -v yum &>/dev/null; then
    yum install -y wget curl openssh-server openssh-clients java-1.8.0-openjdk-devel
elif command -v apt-get &>/dev/null; then
    apt-get update
    apt-get install -y wget curl openssh-server openjdk-8-jdk
fi

# 3. 配置JAVA_HOME
JAVA_HOME=$(dirname $(dirname $(readlink -f $(which javac))))
if ! grep -q "JAVA_HOME" /etc/profile; then
    echo "export JAVA_HOME=$JAVA_HOME" >> /etc/profile
    echo 'export PATH=$PATH:$JAVA_HOME/bin' >> /etc/profile
fi
export JAVA_HOME=$JAVA_HOME
export PATH=$PATH:$JAVA_HOME/bin

# 4. 配置主机名与hosts
HOSTNAME=$(hostname)
IP=$(hostname -I | awk '{print $1}')
if ! grep -q "$IP $HOSTNAME" /etc/hosts; then
    echo "$IP $HOSTNAME" >> /etc/hosts
fi

# 5. 下载并解压Hadoop
HADOOP_VERSION=3.3.6
INSTALL_DIR=/opt/hadoop
HADOOP_HOME=$INSTALL_DIR/hadoop-$HADOOP_VERSION
if [ ! -d "$HADOOP_HOME" ]; then
    mkdir -p $INSTALL_DIR
    cd $INSTALL_DIR
    wget -c https://mirrors.aliyun.com/apache/hadoop/common/hadoop-$HADOOP_VERSION/hadoop-$HADOOP_VERSION.tar.gz
    tar -xzf hadoop-$HADOOP_VERSION.tar.gz
    ln -sf $HADOOP_HOME $INSTALL_DIR/current
fi

# 6. 配置Hadoop环境变量
if ! grep -q "HADOOP_HOME" /etc/profile; then
    echo "export HADOOP_HOME=$HADOOP_HOME" >> /etc/profile
    echo 'export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin' >> /etc/profile
fi
export HADOOP_HOME=$HADOOP_HOME
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin

# 7. 生成SSH密钥对（如无）
if [ ! -f ~/.ssh/id_rsa ]; then
    ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa
fi

# 8. 打印完成信息
clear
echo "\nHadoop环境基础依赖已安装，JAVA_HOME/HADOOP_HOME已配置，主机名与hosts已同步。"
echo "如需多节点免密，请将本机~/.ssh/id_rsa.pub内容追加到所有节点的~/.ssh/authorized_keys。"
echo "Hadoop目录：$HADOOP_HOME"
echo "请重启终端或执行 source /etc/profile 以生效环境变量。" 