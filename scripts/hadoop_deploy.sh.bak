#!/bin/bash
# Hadoop自动部署脚本
# 适用于Linux系统

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 配置变量
HADOOP_VERSION="3.3.6"
HADOOP_URL="https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz"
INSTALL_DIR="/opt/hadoop"
DOWNLOAD_DIR="/tmp/hadoop_download"
HADOOP_USER="hadoop"
HADOOP_GROUP="hadoop"
UPLOAD_DIR="/tmp/hadoop_uploads"  # 用户上传文件目录

# 检查用户上传的文件
check_uploaded_files() {
    log_info "检查用户上传的文件..."
    
    mkdir -p $UPLOAD_DIR
    
    # 检查是否有用户上传的Hadoop包
    if [ -f "$UPLOAD_DIR/hadoop-uploaded.tar.gz" ]; then
        log_info "发现用户上传的Hadoop包"
        HADOOP_UPLOADED_FILE="$UPLOAD_DIR/hadoop-uploaded.tar.gz"
    else
        HADOOP_UPLOADED_FILE=""
    fi
    
    # 检查是否有用户上传的Java包
    if [ -f "$UPLOAD_DIR/java-uploaded.tar.gz" ] || [ -f "$UPLOAD_DIR/java-uploaded.tgz" ] || [ -f "$UPLOAD_DIR/java-uploaded.zip" ]; then
        log_info "发现用户上传的Java包"
        if [ -f "$UPLOAD_DIR/java-uploaded.tar.gz" ]; then
            JAVA_UPLOADED_FILE="$UPLOAD_DIR/java-uploaded.tar.gz"
        elif [ -f "$UPLOAD_DIR/java-uploaded.tgz" ]; then
            JAVA_UPLOADED_FILE="$UPLOAD_DIR/java-uploaded.tgz"
        else
            JAVA_UPLOADED_FILE="$UPLOAD_DIR/java-uploaded.zip"
        fi
    else
        JAVA_UPLOADED_FILE=""
    fi
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        exit 1
    fi
}

# 检查系统环境
check_environment() {
    log_info "检查系统环境..."
    
    # 检查操作系统
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_error "此脚本仅支持Linux系统"
        exit 1
    fi
    
    # 检查内存
    MEMORY_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    MEMORY_GB=$((MEMORY_KB / 1024 / 1024))
    log_info "系统内存: ${MEMORY_GB}GB"
    
    if [[ $MEMORY_GB -lt 4 ]]; then
        log_warning "系统内存不足4GB，可能影响Hadoop性能"
    fi
    
    # 检查磁盘空间
    DISK_SPACE=$(df / | awk 'NR==2 {print $4}')
    DISK_SPACE_GB=$((DISK_SPACE / 1024 / 1024))
    log_info "可用磁盘空间: ${DISK_SPACE_GB}GB"
    
    if [[ $DISK_SPACE_GB -lt 10 ]]; then
        log_error "磁盘空间不足10GB，无法继续安装"
        exit 1
    fi
    
    log_success "系统环境检查完成"
}

# 安装依赖包
install_dependencies() {
    log_info "安装系统依赖包..."
    
    # 如果有用户上传的Java包，优先使用
    if [ -n "$JAVA_UPLOADED_FILE" ]; then
        log_info "使用用户上传的Java包: $JAVA_UPLOADED_FILE"
        install_custom_java
    else
        # 检测包管理器
        if command -v apt-get &> /dev/null; then
            # Ubuntu/Debian
            apt-get update
            apt-get install -y wget curl tar gzip openjdk-8-jdk ssh pdsh
        elif command -v yum &> /dev/null; then
            # CentOS/RHEL
            yum update -y
            yum install -y wget curl tar gzip java-1.8.0-openjdk java-1.8.0-openjdk-devel ssh pdsh
        else
            log_error "未检测到支持的包管理器"
            exit 1
        fi
    fi
    
    log_success "依赖包安装完成"
}

# 安装自定义Java包
install_custom_java() {
    log_info "安装自定义Java包..."
    
    JAVA_INSTALL_DIR="/usr/lib/jvm"
    mkdir -p $JAVA_INSTALL_DIR
    
    # 解压Java包
    if [[ "$JAVA_UPLOADED_FILE" == *.zip ]]; then
        # 解压zip文件
        unzip -q "$JAVA_UPLOADED_FILE" -d $JAVA_INSTALL_DIR
    else
        # 解压tar.gz/tgz文件
        tar -xzf "$JAVA_UPLOADED_FILE" -C $JAVA_INSTALL_DIR
    fi
    
    # 查找解压后的Java目录
    JAVA_DIR=$(find $JAVA_INSTALL_DIR -maxdepth 1 -type d -name "*jdk*" -o -name "*java*" | head -1)
    
    if [ -z "$JAVA_DIR" ]; then
        log_error "无法找到Java安装目录"
        exit 1
    fi
    
    # 创建符号链接
    ln -sf "$JAVA_DIR" "$JAVA_INSTALL_DIR/java-custom"
    
    # 设置环境变量
    cat >> /etc/profile << EOF

# 自定义Java环境变量
export JAVA_HOME=$JAVA_INSTALL_DIR/java-custom
export PATH=\$JAVA_HOME/bin:\$PATH
EOF
    
    # 更新当前会话的环境变量
    export JAVA_HOME="$JAVA_INSTALL_DIR/java-custom"
    export PATH="$JAVA_HOME/bin:$PATH"
    
    # 验证Java安装
    if java -version > /dev/null 2>&1; then
        log_success "自定义Java安装成功"
        java -version
    else
        log_error "自定义Java安装失败"
        exit 1
    fi
}

# 创建Hadoop用户
create_hadoop_user() {
    log_info "创建Hadoop用户..."
    
    # 检查用户是否已存在
    if id "$HADOOP_USER" &>/dev/null; then
        log_warning "用户 $HADOOP_USER 已存在"
    else
        useradd -m -s /bin/bash $HADOOP_USER
        log_success "用户 $HADOOP_USER 创建成功"
    fi
    
    # 创建用户组
    if getent group $HADOOP_GROUP &>/dev/null; then
        log_warning "用户组 $HADOOP_GROUP 已存在"
    else
        groupadd $HADOOP_GROUP
        log_success "用户组 $HADOOP_GROUP 创建成功"
    fi
    
    # 将用户添加到组
    usermod -a -G $HADOOP_GROUP $HADOOP_USER
}

# 配置SSH免密登录
setup_ssh() {
    log_info "配置SSH免密登录..."
    
    # 切换到hadoop用户
    su - $HADOOP_USER << EOF
    # 生成SSH密钥
    if [ ! -f ~/.ssh/id_rsa ]; then
        ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa
    fi
    
    # 配置免密登录
    cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
EOF
    
    log_success "SSH配置完成"
}

# 下载Hadoop
download_hadoop() {
    log_info "下载Hadoop ${HADOOP_VERSION}..."
    
    mkdir -p $DOWNLOAD_DIR
    cd $DOWNLOAD_DIR
    
    # 如果有用户上传的Hadoop包，优先使用
    if [ -n "$HADOOP_UPLOADED_FILE" ]; then
        log_info "使用用户上传的Hadoop包: $HADOOP_UPLOADED_FILE"
        cp "$HADOOP_UPLOADED_FILE" "hadoop-${HADOOP_VERSION}.tar.gz"
        log_success "使用用户上传的Hadoop包"
        return 0
    fi
    
    if [ -f "hadoop-${HADOOP_VERSION}.tar.gz" ]; then
        log_warning "Hadoop安装包已存在，跳过下载"
        return 0
    fi
    
    # 定义下载源列表（按优先级排序）
    download_sources=(
        "https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz"
        "https://mirrors.tuna.tsinghua.edu.cn/apache/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz"
        "https://mirrors.aliyun.com/apache/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz"
        "https://mirrors.huaweicloud.com/apache/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz"
        "https://mirror.bit.edu.cn/apache/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz"
    )
    
    # 尝试从不同源下载
    for source_url in "${download_sources[@]}"; do
        log_info "尝试从源下载: ${source_url}"
        
        # 检查网络连接
        if curl -s --head "$source_url" | head -n 1 | grep "HTTP/1.[01] [23].." > /dev/null; then
            log_info "源可用，开始下载..."
            
            if wget -O "hadoop-${HADOOP_VERSION}.tar.gz" "$source_url" --progress=bar:force:noscroll; then
                log_success "Hadoop下载成功 (源: ${source_url})"
                return 0
            else
                log_warning "从 ${source_url} 下载失败，尝试下一个源"
                rm -f "hadoop-${HADOOP_VERSION}.tar.gz"
            fi
        else
            log_warning "源不可用: ${source_url}"
        fi
    done
    
    log_error "所有下载源都失败，无法下载Hadoop"
    return 1
}

# 安装Hadoop
install_hadoop() {
    log_info "安装Hadoop..."
    
    # 创建安装目录
    mkdir -p $INSTALL_DIR
    
    # 解压Hadoop
    cd $DOWNLOAD_DIR
    tar -xzf "hadoop-${HADOOP_VERSION}.tar.gz" -C $INSTALL_DIR
    
    # 创建符号链接
    ln -sf $INSTALL_DIR/hadoop-${HADOOP_VERSION} $INSTALL_DIR/current
    
    # 设置权限
    chown -R $HADOOP_USER:$HADOOP_GROUP $INSTALL_DIR
    
    log_success "Hadoop安装完成"
}

# 配置Hadoop
configure_hadoop() {
    log_info "配置Hadoop..."
    
    HADOOP_HOME="$INSTALL_DIR/current"
    HADOOP_CONF_DIR="$HADOOP_HOME/etc/hadoop"
    
    # 设置环境变量
    cat >> /home/$HADOOP_USER/.bashrc << EOF

# Hadoop环境变量
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk
export HADOOP_HOME=$HADOOP_HOME
export HADOOP_CONF_DIR=$HADOOP_CONF_DIR
export PATH=\$PATH:\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin
export HADOOP_OPTS="-Djava.library.path=\$HADOOP_HOME/lib/native"
EOF
    
    # 配置core-site.xml
    cat > $HADOOP_CONF_DIR/core-site.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://localhost:9000</value>
    </property>
    <property>
        <name>hadoop.tmp.dir</name>
        <value>/tmp/hadoop-\${user.name}</value>
    </property>
</configuration>
EOF
    
    # 配置hdfs-site.xml
    cat > $HADOOP_CONF_DIR/hdfs-site.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>/data/hadoop/hdfs/namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>/data/hadoop/hdfs/datanode</value>
    </property>
</configuration>
EOF
    
    # 配置mapred-site.xml
    cat > $HADOOP_CONF_DIR/mapred-site.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>mapreduce.framework.name</name>
        <value>yarn</value>
    </property>
    <property>
        <name>mapreduce.application.classpath</name>
        <value>\$HADOOP_HOME/share/hadoop/mapreduce/*:\$HADOOP_HOME/share/hadoop/mapreduce/lib/*</value>
    </property>
</configuration>
EOF
    
    # 配置yarn-site.xml
    cat > $HADOOP_CONF_DIR/yarn-site.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle</value>
    </property>
    <property>
        <name>yarn.resourcemanager.hostname</name>
        <value>localhost</value>
    </property>
</configuration>
EOF
    
    # 创建数据目录
    mkdir -p /data/hadoop/hdfs/namenode
    mkdir -p /data/hadoop/hdfs/datanode
    chown -R $HADOOP_USER:$HADOOP_GROUP /data/hadoop
    
    log_success "Hadoop配置完成"
}

# 启动Hadoop集群
start_hadoop() {
    log_info "启动Hadoop集群..."
    
    # 切换到hadoop用户
    su - $HADOOP_USER << EOF
    # 格式化NameNode
    hdfs namenode -format
    
    # 启动HDFS
    start-dfs.sh
    
    # 启动YARN
    start-yarn.sh
EOF
    
    log_success "Hadoop集群启动完成"
}

# 验证部署
verify_deployment() {
    log_info "验证部署结果..."
    
    # 等待服务启动
    sleep 10
    
    # 检查HDFS状态
    su - $HADOOP_USER -c "hdfs dfsadmin -report" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        log_success "HDFS状态正常"
    else
        log_error "HDFS状态异常"
        return 1
    fi
    
    # 检查YARN状态
    su - $HADOOP_USER -c "yarn node -list" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        log_success "YARN状态正常"
    else
        log_error "YARN状态异常"
        return 1
    fi
    
    # 测试HDFS写入
    su - $HADOOP_USER -c "echo 'Hadoop部署测试' | hdfs dfs -put - /test_deployment.txt" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        log_success "HDFS写入测试成功"
        # 清理测试文件
        su - $HADOOP_USER -c "hdfs dfs -rm /test_deployment.txt" > /dev/null 2>&1
    else
        log_error "HDFS写入测试失败"
        return 1
    fi
    
    log_success "部署验证完成"
}

# 主函数
main() {
    log_info "开始Hadoop自动部署..."
    
    check_root
    check_environment
    check_uploaded_files  # 检查用户上传的文件
    install_dependencies
    create_hadoop_user
    setup_ssh
    download_hadoop
    install_hadoop
    configure_hadoop
    start_hadoop
    verify_deployment
    
    log_success "Hadoop部署完成！"
    log_info "Hadoop Web界面:"
    log_info "  - NameNode: http://localhost:9870"
    log_info "  - ResourceManager: http://localhost:8088"
    log_info "  - NodeManager: http://localhost:8042"
}

# 执行主函数
main "$@"