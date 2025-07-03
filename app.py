from flask import Flask, config, render_template, request, flash, jsonify, send_from_directory, abort, Response, send_file
from flask_cors import CORS
import paramiko
import subprocess
import re
import ast
from threading import Lock
import json
import threading
import time
import os
import requests
from io import BytesIO

app = Flask(__name__)
CORS(app)

deploy_lock = Lock()

auto_deploy_status = {
    'status': 'idle',  # idle, running, done, error
    'step': 0,
    'total_steps': 6,
    'progress': 0,
    'message': '',
    'log': [],
    'cluster_links': {},
    'steps': []
}

semi_auto_deploy_status = {
    'status': 'idle',  # idle, running, done, error
    'step': 0,
    'total_steps': 6,
    'progress': 0,
    'message': '',
    'log': [],
}

WEBHDFS_URL = 'http://localhost:9870/webhdfs/v1'
WEBHDFS_USER = 'hadoop'  # 可根据实际情况修改

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/toolchain')
def toolchain():
    return render_template('toolchain.html')

@app.route('/deploy/start')
def start():
    return render_template('start.html')

@app.route('/deploy/method')
def deploy_method():
    return render_template('components/deploy-method.html')

@app.route('/deploy/auto')
def deploy_auto():
    return render_template('components/deploy-auto.html')

@app.route('/deploy/semiAutoConfig')
def deploy_semi_auto():
    return render_template('components/deploy-semi-auto.html')

@app.route('/deploy/semi-auto/progress')
def deploy_semi_auto_progress():
    return render_template('components/deploy-semi-auto-progress.html')

@app.route('/deploy/manualConfig')
def deploy_manual():
    return render_template('components/deploy-manual.html')

@app.route('/deploy/manual/progress')
def deploy_manual_progress():
    return render_template('components/deploy-manual-progress.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy-policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    return render_template('terms-of-service.html')

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/hdfs-manager')
def hdfs_manager():
    return render_template('hdfs-manager.html')   

@app.route('/api/scan_hosts', methods=['POST'])
def scan_hosts():
    try:
        request_data = request.get_json()
        subnet = request_data.get('subnet', '')
        if not subnet:
            return jsonify({"success": False, "error": "缺少网段参数"}), 400
        result = subprocess.run(f"nmap -sn {subnet}", shell=True, capture_output=True, text=True)
        output = result.stdout

        #获取ip地址
        hosts = []
        for line in output.split('\n'):
            ip_match = re.match(r'Nmap scan report for (.+?)( \(([\d\.]+)\))?$', line)
            if ip_match:
                ip = ip_match.group(3) if ip_match.group(3) else ip_match.group(1)
                hosts.append(ip)

        return jsonify({"success": True, "hosts": hosts})
    except Exception as e:
        print(f"扫描异常: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def servers_info():
    servers = request.get_json().get('servers', [])
    return servers

def ssh_client(hostname,username,password,port):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname,username=username,password=password,port=port)
    return ssh

@app.route('/api/yum/configure',methods=['POST'])
def configure_yum():
    servers = servers_info()
    results = []
    for server in servers:
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        stdin, stdout, stderr = ssh.exec_command("cat /etc/redhat-release")
        version_info = stdout.read().decode('utf-8').strip()
        if "8" in version_info:
            stdin,stdout,stderr = ssh.exec_command("rm -rf /etc/yum.repos.d/* && curl -o /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-8.repo")
            exit_code = stdout.channel.recv_exit_status()
            if exit_code == 0:
                ssh.exec_command("yum clean all && yum makecache")
        else:
            stdin,stdout,stderr = ssh.exec_command("rm -rf /etc/yum.repos.d/* && curl -o /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo")
            exit_code = stdout.channel.recv_exit_status()
            if exit_code == 0:
                ssh.exec_command("yum clean all && yum makecache")
        ssh.close()
        results.append({
            "hostname": server['hostname'],
            "host": server['hostname'],
            "success": True,
            "status": "success"
        })
    return jsonify({"status": "completed", "results": results})

def set_hostname(servers):

    server_count = 0
    for server in servers:
        server_count += 1
        if server_count <= 1:
            hostname = 'master'
        elif server_count <= len(servers):
            hostname = f'slave{server_count - 1}'
        
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        ssh.exec_command(f"hostnamectl set-hostname {hostname}")


def close_firewall(ssh):
    stdin,stdout,stderr = ssh.exec_command("systemctl stop firewalld && systemctl disable firewalld")
    stdout.channel.recv_exit_status()




@app.route('/api/deploy/auto/start', methods=['POST'])
def api_deploy_auto_start():
    with deploy_lock:
        if not request.json:
            return jsonify({'msg': '请求体为空或格式错误'}), 400
        config = request.json.get('config')
        # 兼容前端传递list、dict或str
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except Exception:
                return jsonify({'msg': 'config参数格式错误'}), 400
        if config is None:
            return jsonify({'msg': '缺少config参数'}), 400
        if auto_deploy_status['status'] == 'running':
            return jsonify({'msg': '已有部署在进行中'}), 400
        # 重置状态
        auto_deploy_status['status'] = 'idle'
        auto_deploy_status['step'] = 0
        auto_deploy_status['progress'] = 0
        auto_deploy_status['message'] = ''
        auto_deploy_status['log'] = []
        t = threading.Thread(target=auto_deploy_task, args=(config,))
        t.start()
    return jsonify({'msg': '部署已启动'})

@app.route('/api/deploy/semi-auto/start', methods=['POST'])
def api_deploy_semi_auto_start():
    with deploy_lock:
        if not request.json:
            return jsonify({'success': False, 'msg': '请求体为空或格式错误'}), 400
        config = request.json.get('config')
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except Exception:
                return jsonify({'success': False, 'msg': 'config参数格式错误'}), 400
        if config is None:
            return jsonify({'success': False, 'msg': '缺少config参数'}), 400
        if semi_auto_deploy_status['status'] == 'running':
            return jsonify({'success': False, 'msg': '已有部署在进行中'}), 400

        # 解析参数
        basic = config.get('basic', {})
        cluster = config.get('cluster', {})
        performance = config.get('performance', {})
        components = config.get('components', {})
        advanced = config.get('advanced', {})

        # 示例：获取具体字段
        hadoop_version = basic.get('hadoopVersion')
        java_version = basic.get('javaVersion')
        namenode_host = basic.get('namenodeHost')
        # ... 其他参数同理

        # print('Hadoop版本:', hadoop_version)
        # print('Java版本:', java_version)
        # print('主节点:', namenode_host)
        # print('DataDir:', basic.get('dataDir'))
        # print('Datanode数量:', cluster.get('datanodeCount'))
        # ... 其他参数打印

        # 重置状态
        semi_auto_deploy_status['status'] = 'idle'
        semi_auto_deploy_status['step'] = 0
        semi_auto_deploy_status['progress'] = 0
        semi_auto_deploy_status['message'] = ''
        semi_auto_deploy_status['log'] = []
        t = threading.Thread(target=semi_auto_deploy_task, args=(config,))
        t.start()
    return jsonify({'success': True, 'msg': '部署已启动'})


def generate_core_site(master_ip, hadoop_tmp_dir="/data/hadoop/tmp"):
    return f"""<?xml version="1.0"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://{master_ip}:9000</value>
    </property>
    <property>
        <name>hadoop.tmp.dir</name>
        <value>{hadoop_tmp_dir}</value>
        <description>Hadoop临时目录，所有节点（包括DataNode）都需要</description>
    </property>
    <!-- 可选：增加其他DataNode相关参数 -->
    <property>
        <name>io.file.buffer.size</name>
        <value>131072</value>
    </property>
    <property>
        <name>fs.trash.interval</name>
        <value>1440</value>
        <description>回收站保留时间（分钟）</description>
    </property>
</configuration>
"""

def generate_hdfs_site(replication=3, namenode_dir="/opt/hadoop/data/dfs/namenode", datanode_dir="/opt/hadoop/data/dfs/datanode"):
    return f"""<?xml version="1.0"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>{replication}</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>file:{namenode_dir}</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>file:{datanode_dir}</value>
    </property>
    <property>
        <name>dfs.webhdfs.enabled</name>
        <value>true</value>
    </property>
</configuration>
"""

def generate_yarn_site(resourcemanager_ip, yarn_memory=4096, yarn_cores=4):
    return f"""<?xml version="1.0"?>
<configuration>
    <property>
        <name>yarn.resourcemanager.hostname</name>
        <value>{resourcemanager_ip}</value>
    </property>
    <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle</value>
    </property>
    <property>
        <name>yarn.nodemanager.resource.memory-mb</name>
        <value>{yarn_memory}</value>
    </property>
    <property>
        <name>yarn.scheduler.maximum-allocation-mb</name>
        <value>{yarn_memory}</value>
    </property>
    <property>
        <name>yarn.nodemanager.resource.cpu-vcores</name>
        <value>{yarn_cores}</value>
    </property>
    <property>
        <name>yarn.scheduler.maximum-allocation-vcores</name>
        <value>{yarn_cores}</value>
    </property>
</configuration>
"""

def generate_mapred_site(map_memory=2048, map_cores=2):
    return f"""<?xml version="1.0"?>
<configuration>
    <property>
        <name>mapreduce.framework.name</name>
        <value>yarn</value>
    </property>
    <property>
        <name>mapreduce.map.memory.mb</name>
        <value>{map_memory}</value>
    </property>
    <property>
        <name>mapreduce.reduce.memory.mb</name>
        <value>{map_memory}</value>
    </property>
    <property>
        <name>mapreduce.map.cpu.vcores</name>
        <value>{map_cores}</value>
    </property>
    <property>
        <name>mapreduce.reduce.cpu.vcores</name>
        <value>{map_cores}</value>
    </property>
</configuration>
"""

def generate_workers(servers, datanodeCount=3):
    workers = []
    for server in servers:
        workers.append(server['hostname'])
    if len(workers) < datanodeCount:
        datanodeCount = len(workers)
    return workers

def get_node_color(server_index, total_servers):
    """为不同节点生成不同的颜色"""
    colors = [
        '#FF6B6B',  # 红色 - 主节点
        '#4ECDC4',  # 青色 - 从节点1
        '#45B7D1',  # 蓝色 - 从节点2
        '#96CEB4',  # 绿色 - 从节点3
        '#FFEAA7',  # 黄色 - 从节点4
        '#DDA0DD',  # 紫色 - 从节点5
        '#98D8C8',  # 薄荷绿 - 从节点6
        '#F7DC6F',  # 金黄色 - 从节点7
        '#BB8FCE',  # 淡紫色 - 从节点8
        '#85C1E9'   # 天蓝色 - 从节点9
    ]
    return colors[server_index % len(colors)]

def format_node_log(step, message, server_ip=None, server_index=None, total_servers=None):
    """格式化节点日志，为不同节点添加颜色"""
    if server_ip and server_index is not None and total_servers is not None:
        color = get_node_color(server_index, total_servers)
        return f"{step} <span style='color: {color}; font-weight: bold;'>{server_ip}</span> {message}"
    else:
        return f"{step} {message}"

def auto_deploy_task(config):
    auto_deploy_status['status'] = 'running'
    auto_deploy_status['log'] = []
    auto_deploy_status['steps'] = [
        {'name': '环境检测', 'status': 'pending'},
        {'name': '安装Java环境', 'status': 'pending'},
        {'name': '下载并解压Hadoop', 'status': 'pending'},
        {'name': '自动配置Hadoop核心参数', 'status': 'pending'},
        {'name': '启动Hadoop集群服务', 'status': 'pending'},
        {'name': '验证集群运行状态', 'status': 'pending'}
    ]
    if isinstance(config, str):
        config = ast.literal_eval(config)
    servers = config.get('servers', []) if isinstance(config, dict) else config
    auto_deploy_status['log'].append("--------------------------------全自动部署开始--------------------------------")
    auto_deploy_status['step'] = 1
    auto_deploy_status['progress'] = 10
    auto_deploy_status['log'].append("[1/6] 🚀 开始环境检测与SSH免密配置...")
    auto_deploy_status['steps'][0]['status'] = 'doing'

    set_hostname(servers)
    pubkey_list = []
    for i, server in enumerate(servers):
        ip = server['hostname']
        username = server['username']
        password = server['password']
        port = int(server.get('port', 22))
        auto_deploy_status['log'].append(format_node_log("[1/6] 🔗 正在连接节点", f"(用户: {username}, 端口: {port})...", ip, i, len(servers)))
        ssh = ssh_client(ip, username, password, port)
        auto_deploy_status['log'].append(format_node_log("[1/6] ✅ 节点", "SSH连接成功，开始配置SSH密钥...", ip, i, len(servers)))
        ssh.exec_command("ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa")
        #等待ssh-keygen生成公钥
        time.sleep(1)
        #获取公钥
        stdin, stdout, stderr = ssh.exec_command("cat ~/.ssh/id_rsa.pub")
        pubkey = stdout.read().decode().strip()
        #添加公钥到pubkey_list
        pubkey_list.append(pubkey)
        #添加ip映射到hosts
        server_count = 0
        for server2 in servers:
            server_count += 1
            if server_count <= 1:
                hostname = 'master'
            elif server_count <= len(servers):
                hostname = f'slave{server_count - 1}'
            ssh.exec_command(f"echo '{server2['hostname']}\t{hostname}' >> /etc/hosts")
            #关闭防火墙
            close_firewall(ssh)
        auto_deploy_status['log'].append(format_node_log("[1/6] 🔧 节点", "主机名映射和防火墙配置完成", ip, i, len(servers)))
    
    #添加公钥到authorized_keys
    auto_deploy_status['log'].append("[1/6] 🔑 正在配置SSH免密登录...")
    for server in servers:
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        for pubkey in pubkey_list:
            ssh.exec_command(f"echo '{pubkey}' >> ~/.ssh/authorized_keys")
        ssh.close()

    auto_deploy_status['log'].append(f"[1/6] ✅ 环境检测完成！共配置 {len(servers)} 个节点")
    auto_deploy_status['steps'][0]['status'] = 'done'

    
    auto_deploy_status['progress'] = 20
    auto_deploy_status['step'] = 2
    auto_deploy_status['steps'][1]['status'] = 'doing'
    auto_deploy_status['log'].append("[2/6] ☕ 开始安装Java运行环境...")
    
    for i, server in enumerate(servers):
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        auto_deploy_status['log'].append(format_node_log("[2/6] 🔍 检查节点", "的Java环境...", server['hostname'], i, len(servers)))
        stdin, stdout, stderr = ssh.exec_command("which java")
        java_path = stdout.read().decode().strip()
        if not java_path:
            auto_deploy_status['log'].append(format_node_log("[2/6] 📦 节点", "未检测到Java，开始安装OpenJDK 8...", server['hostname'], i, len(servers)))
            stdin, stdout, stderr = ssh.exec_command("yum install -y java-1.8.0-openjdk-devel", timeout=120)
            auto_deploy_status['log'].append(format_node_log("[2/6] ⏳ 节点", "正在安装Java，请稍候...", server['hostname'], i, len(servers)))
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                auto_deploy_status['log'].append(format_node_log("[2/6] ❌ 节点", "安装Java失败，请检查yum源和权限", server['hostname'], i, len(servers)))
                auto_deploy_status['steps'][1]['status'] = 'error'
                return
            auto_deploy_status['log'].append(format_node_log("[2/6] ✅ 节点", "Java安装成功", server['hostname'], i, len(servers)))
        else:
            auto_deploy_status['log'].append(format_node_log("[2/6] ✅ 节点", f"已存在Java环境: {java_path}", server['hostname'], i, len(servers)))
        ssh.close()
    
    auto_deploy_status['log'].append(f"[2/6] ✅ Java环境安装完成！共处理 {len(servers)} 个节点")
    auto_deploy_status['steps'][1]['status'] = 'done'
        
    auto_deploy_status['progress'] = 30
    auto_deploy_status['step'] = 3
    auto_deploy_status['steps'][2]['status'] = 'doing'
    auto_deploy_status['log'].append("[3/6] 📦 开始下载并安装Hadoop...")
    
    for i, server in enumerate(servers):
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        auto_deploy_status['log'].append(format_node_log("[3/6] 🔧 节点", "正在安装curl工具...", server['hostname'], i, len(servers)))
        hadoop_tar_path = "/opt/hadoop.tar.gz"
        stdin, stdout, stderr = ssh.exec_command("yum install -y curl",timeout=60)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            auto_deploy_status['log'].append(format_node_log("[3/6] ❌ 节点", "安装curl失败，请检查yum源和权限", server['hostname'], i, len(servers)))
            auto_deploy_status['steps'][2]['status'] = 'error'
            return
        
        auto_deploy_status['log'].append(format_node_log("[3/6] 🔍 节点", "检查Hadoop安装包完整性...", server['hostname'], i, len(servers)))
        stdin, stdout, stderr = ssh.exec_command("sha256sum /opt/hadoop.tar.gz")
        hadoop_tar_hash = stdout.read().decode().strip()
        if hadoop_tar_hash != "f5195059c0d4102adaa7fff17f7b2a85df906bcb6e19948716319f9978641a04  /opt/hadoop.tar.gz":
            auto_deploy_status['log'].append(format_node_log("[3/6] 📥 节点", "开始下载Hadoop 3.3.6...", server['hostname'], i, len(servers)))
            stdin, stdout, stderr = ssh.exec_command(f"curl -o {hadoop_tar_path} https://mirrors.aliyun.com/apache/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz",timeout=70)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                auto_deploy_status['log'].append(format_node_log("[3/6] ❌ 节点", "下载Hadoop失败，请检查网络连接", server['hostname'], i, len(servers)))
                auto_deploy_status['steps'][2]['status'] = 'error'
            else:
                auto_deploy_status['log'].append(format_node_log("[3/6] ✅ 节点", "Hadoop下载完成", server['hostname'], i, len(servers)))
        else:
            auto_deploy_status['log'].append(format_node_log("[3/6] ✅ 节点", "Hadoop安装包已存在且校验通过", server['hostname'], i, len(servers)))

        auto_deploy_status['log'].append(format_node_log("[3/6] 📂 节点", "开始解压Hadoop...", server['hostname'], i, len(servers)))
        #确保有tar命令
        ssh.exec_command("yum install -y tar && source /etc/profile")
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p /opt/hadoop/ && tar -xzf {hadoop_tar_path} -C /opt/")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            auto_deploy_status['log'].append(format_node_log("[3/6] ❌ 节点", "解压Hadoop失败，请检查磁盘空间", server['hostname'], i, len(servers)))
            auto_deploy_status['steps'][2]['status'] = 'error'
            continue
            
        ssh.exec_command(f"mv /opt/hadoop-3.3.6/* /opt/hadoop/ && rm -rf /opt/hadoop-3.3.6")
        auto_deploy_status['log'].append(format_node_log("[3/6] ✅ 节点", "Hadoop安装完成", server['hostname'], i, len(servers)))
        ssh.close()
    
    auto_deploy_status['log'].append(f"[3/6] ✅ Hadoop安装完成！共处理 {len(servers)} 个节点")
    auto_deploy_status['steps'][2]['status'] = 'done'
    auto_deploy_status['progress'] = 40
    auto_deploy_status['step'] = 4
    auto_deploy_status['steps'][3]['status'] = 'doing'
    auto_deploy_status['log'].append("[4/6] ⚙️ 开始配置Hadoop核心参数...")

    for i, server in enumerate(servers):
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        auto_deploy_status['log'].append(format_node_log("[4/6] 🔧 节点", "开始配置Hadoop参数...", server['hostname'], i, len(servers)))

        auto_deploy_status['log'].append(format_node_log("[4/6] 📄 节点", f"配置core-site.xml (主节点: {servers[0]['hostname']})", server['hostname'], i, len(servers)))
        ssh.exec_command(f"echo '{generate_core_site(servers[0]['hostname'])}' > /opt/hadoop/etc/hadoop/core-site.xml")

        auto_deploy_status['log'].append(format_node_log("[4/6] 📄 节点", f"配置hdfs-site.xml (副本数: {len(servers)})", server['hostname'], i, len(servers)))
        ssh.exec_command(f"echo '{generate_hdfs_site(len(servers))}' > /opt/hadoop/etc/hadoop/hdfs-site.xml")
        
        auto_deploy_status['log'].append(format_node_log("[4/6] 📄 节点", f"配置yarn-site.xml (资源管理器: {servers[0]['hostname']})", server['hostname'], i, len(servers)))
        ssh.exec_command(f"echo '{generate_yarn_site(servers[0]['hostname'])}' > /opt/hadoop/etc/hadoop/yarn-site.xml")

        auto_deploy_status['log'].append(format_node_log("[4/6] 📄 节点", "配置workers文件", server['hostname'], i, len(servers)))
        workers_content = ''.join([server + '\n' for server in generate_workers(servers)])
        ssh.exec_command(f"echo '{workers_content}' > /opt/hadoop/etc/hadoop/workers")

        auto_deploy_status['log'].append(format_node_log("[4/6] 📄 节点", "配置hadoop-env.sh", server['hostname'], i, len(servers)))
        stdin, stdout, stderr = ssh.exec_command(f"source ~/.hadoop_env && dirname $(dirname $(readlink -f $(which java)))")
        java_home = stdout.read().decode().strip()
        ssh.exec_command(f"echo 'export JAVA_HOME={java_home}' > /opt/hadoop/etc/hadoop/hadoop-env.sh")

        auto_deploy_status['log'].append(format_node_log("[4/6] 🔧 节点", "配置环境变量", server['hostname'], i, len(servers)))
        env_content = f"""
export JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk-1.8.0.312.b07-2.el8_5.x86_64
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
export HADOOP_OPTS=\"-Djava.library.path=$HADOOP_HOME/lib/native\"
export HDFS_NAMENODE_USER=root
export HDFS_DATANODE_USER=root
export HDFS_SECONDARYNAMENODE_USER=root
export YARN_RESOURCEMANAGER_USER=root
export YARN_NODEMANAGER_USER=root"""
        ssh.exec_command(f"echo '{env_content}' > ~/.hadoop_env && source ~/.hadoop_env")
        auto_deploy_status['log'].append(format_node_log("[4/6] ✅ 节点", "Hadoop配置完成", server['hostname'], i, len(servers)))
        ssh.close()
    
    auto_deploy_status['log'].append(f"[4/6] ✅ Hadoop配置完成！共配置 {len(servers)} 个节点")
    auto_deploy_status['steps'][3]['status'] = 'done'

    auto_deploy_status['progress'] = 60
    auto_deploy_status['step'] = 5
    auto_deploy_status['steps'][4]['status'] = 'doing'
    auto_deploy_status['log'].append("[5/6] 🚀 开始启动Hadoop集群服务...")
    
    # 在所有节点上检查并停止Hadoop服务
    auto_deploy_status['log'].append("[5/6] 🔍 检查所有节点上的Hadoop服务状态...")
    for i, server in enumerate(servers):
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        
        # 检查是否有Hadoop进程在运行
        auto_deploy_status['log'].append(format_node_log("[5/6] 🔍 检查节点", "上的Hadoop进程...", server['hostname'], i, len(servers)))
        stdin, stdout, stderr = ssh.exec_command("source ~/.hadoop_env && ps aux | grep -E '(hadoop|java.*hadoop)' | grep -v grep", timeout=30)
        running_processes = stdout.read().decode().strip()
        
        if running_processes:
            auto_deploy_status['log'].append(format_node_log("[5/6] ⏹️ 节点", "发现运行中的Hadoop进程，开始停止...", server['hostname'], i, len(servers)))
            # 正常停止服务
            ssh.exec_command("source ~/.hadoop_env && stop-all.sh 2>/dev/null || true", timeout=60)
            time.sleep(2)
            
            # 强制终止剩余进程
            ssh.exec_command("source ~/.hadoop_env && pkill -f hadoop 2>/dev/null || true", timeout=30)
            ssh.exec_command("source ~/.hadoop_env && pkill -f java.*hadoop 2>/dev/null || true", timeout=30)
            time.sleep(1)
            
            # 再次检查是否还有进程
            stdin, stdout, stderr = ssh.exec_command("source ~/.hadoop_env && ps aux | grep -E '(hadoop|java.*hadoop)' | grep -v grep", timeout=30)
            remaining_processes = stdout.read().decode().strip()
            
            if remaining_processes:
                auto_deploy_status['log'].append(format_node_log("[5/6] ⚡ 节点", "仍有Hadoop进程运行，强制终止...", server['hostname'], i, len(servers)))
                ssh.exec_command("source ~/.hadoop_env && pkill -9 -f hadoop 2>/dev/null || true", timeout=30)
                ssh.exec_command("source ~/.hadoop_env && pkill -9 -f java.*hadoop 2>/dev/null || true", timeout=30)
            else:
                auto_deploy_status['log'].append(format_node_log("[5/6] ✅ 节点", "的Hadoop服务已成功停止", server['hostname'], i, len(servers)))
        else:
            auto_deploy_status['log'].append(format_node_log("[5/6] ✅ 节点", "没有运行中的Hadoop进程", server['hostname'], i, len(servers)))
        
        ssh.close()
    
    time.sleep(3)  # 等待所有节点服务完全停止
    
    # 在主节点上进行namenode操作
    ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
    
    # 检查namenode是否已经初始化
    auto_deploy_status['log'].append(f"[5/6] 🔍 检查主节点 {servers[0]['hostname']} 的namenode状态...")
    
    # 首先创建必要的目录
    ssh.exec_command("source ~/.hadoop_env && mkdir -p /opt/hadoop/data/dfs/namenode")
    ssh.exec_command("source ~/.hadoop_env && mkdir -p /opt/hadoop/data/dfs/datanode")

    stdin, stdout, stderr = ssh.exec_command(
        "source ~/.hadoop_env && (test -f /opt/hadoop/data/dfs/namenode/current/VERSION || test -f /data/hadoop/data/dfs/namenode/current/VERSION) && echo 'EXIST' || echo 'NOT_EXIST'",
        timeout=30
    )
    namenode_exists = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if err:
        auto_deploy_status['log'].append(f"[调试] 检查VERSION文件时stderr: {err}")
    
    if namenode_exists == "EXIST":
        auto_deploy_status['log'].append(f"[6/7] ✅ 主节点 {servers[0]['hostname']} namenode已初始化，跳过格式化步骤")
    else:
        # 进行格式化
        auto_deploy_status['log'].append(f"[6/7] 🔧 主节点 {servers[0]['hostname']} namenode未初始化，开始格式化...")
        stdin, stdout, stderr = ssh.exec_command("source ~/.hadoop_env && hadoop namenode -format", timeout=120)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            auto_deploy_status['log'].append(f"[6/7] ❌ 主节点 {servers[0]['hostname']} namenode格式化失败")
            auto_deploy_status['steps'][4]['status'] = 'error'
            return
        auto_deploy_status['log'].append(f"[6/7] ✅ 主节点 {servers[0]['hostname']} namenode格式化完成")
    
    # 启动Hadoop集群服务
    ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
    auto_deploy_status['log'].append(f"[5/6] 🚀 从主节点 {servers[0]['hostname']} 启动Hadoop集群服务...")
    stdin,stdout,stderr = ssh.exec_command("source ~/.hadoop_env && /opt/hadoop/sbin/start-all.sh")
    stdout.channel.recv_exit_status()
    auto_deploy_status['log'].append(f"[5/6] ✅ Hadoop集群服务启动完成")
    auto_deploy_status['steps'][4]['status'] = 'done'
    auto_deploy_status['progress'] = 80
    auto_deploy_status['step'] = 6
    auto_deploy_status['steps'][5]['status'] = 'doing'
    auto_deploy_status['log'].append("[6/6] 🔍 开始验证Hadoop集群运行状态...")
    auto_deploy_status['log'].append(f"[6/6] 🔍 测试HDFS文件系统访问 (主节点: {servers[0]['hostname']})...")
    stdin,stdout,stderr = ssh.exec_command("source ~/.hadoop_env && hdfs dfs -ls /",timeout=120)
    ssh.exec_command("source ~/.hadoop_env && hdfs dfs -chmod -R 777 /")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        auto_deploy_status['log'].append(f"[6/6] ❌ HDFS文件系统验证失败，请检查集群状态")
        auto_deploy_status['steps'][5]['status'] = 'error'
        return
    
    auto_deploy_status['log'].append(f"[6/6] ✅ HDFS文件系统验证成功")
    auto_deploy_status['log'].append(f"[6/6] 🎉 Hadoop集群部署完成！共 {len(servers)} 个节点")
    auto_deploy_status['progress'] = 100
    auto_deploy_status['status'] = 'done'
    auto_deploy_status['steps'][5]['status'] = 'done'

    nn_url = f'http://{servers[0]["hostname"]}:9870'
    rm_url = f'http://{servers[0]["hostname"]}:8088'
    auto_deploy_status['cluster_links'] = {
        'NameNode': nn_url,
        'ResourceManager': rm_url
    }
    auto_deploy_status['log'].append(f"[6/6] 🌐 集群Web UI已就绪，主节点: {servers[0]['hostname']}")



@app.route('/api/upload/java', methods=['POST'])
def upload_java_package():
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        # 获取配置信息
        config = request.form.get('config')
        if not config:
            return jsonify({'success': False, 'error': '缺少配置信息'}), 400
        
        if isinstance(config, str):
            config = ast.literal_eval(config)
        
        # 检查文件类型（修正：支持多后缀）
        allowed_extensions = ('.tar', '.tar.gz', '.tgz', '.zip', '.rpm', '.deb')
        filename = file.filename or 'unknown'
        if not filename.lower().endswith(allowed_extensions):
            return jsonify({'success': False, 'error': f'不支持的文件类型: {filename.split(".")[-1]}'}), 400
        
        # 保存文件到临时目录
        import tempfile
        import os
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, filename)
        file.save(temp_file_path)
        file_size = os.path.getsize(temp_file_path)
        
        # 只返回本地文件信息，不做远程上传
        return jsonify({
            'success': True,
            'filename': filename,
            'temp_path': temp_file_path,
            'size': file_size,
            'config': config
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'上传过程中发生错误: {str(e)}'}), 500


@app.route('/api/upload/hadoop', methods=['POST'])
def upload_hadoop_package():
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
        
        # 获取配置信息
        config = request.form.get('config')
        if not config:
            return jsonify({'success': False, 'error': '缺少配置信息'}), 400
        
        if isinstance(config, str):
            config = ast.literal_eval(config)
        
        # 检查文件类型（修正：支持多后缀）
        allowed_extensions = ('.tar', '.tar.gz', '.tgz', '.zip', '.rpm', '.deb')
        filename = file.filename or 'unknown'
        if not filename.lower().endswith(allowed_extensions):
            return jsonify({'success': False, 'error': f'不支持的文件类型: {filename.split(".")[-1]}'}), 400
        
        # 保存文件到临时目录
        import tempfile
        import os
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, filename)
        file.save(temp_file_path)
        file_size = os.path.getsize(temp_file_path)
        
        # 只返回本地文件信息，不做远程上传
        return jsonify({
            'success': True,
            'filename': filename,
            'temp_path': temp_file_path,
            'size': file_size,
            'config': config
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'上传过程中发生错误: {str(e)}'}), 500


def semi_auto_deploy_task(config):
    semi_auto_deploy_status['status'] = 'running'
    semi_auto_deploy_status['log'] = []
    semi_auto_deploy_status['steps'] = [
        {'name': '环境检测', 'status': 'pending'},
        {'name': '安装Java环境', 'status': 'pending'},
        {'name': '下载并解压Hadoop', 'status': 'pending'},
        {'name': '自动配置Hadoop核心参数', 'status': 'pending'},
        {'name': '安装组件', 'status': 'pending'},
        {'name': '启动Hadoop集群服务', 'status': 'pending'},
        {'name': '验证集群运行状态', 'status': 'pending'}
    ]
    if isinstance(config, str):
        config = ast.literal_eval(config)
    # 关键修正
    servers = config.get('servers', []) if isinstance(config, dict) else config
    basic = config.get('basic', {})
    cluster = config.get('cluster', {})
    components = config.get('components', {})
    advanced = config.get('advanced', {})
    performance = config.get('performance', {})

    semi_auto_deploy_status['step'] = 1
    semi_auto_deploy_status['progress'] = 10
    semi_auto_deploy_status['log'].append("--------------------------------半自动部署开始--------------------------------")
    semi_auto_deploy_status['log'].append("[1/7] 🚀 开始环境检测与SSH免密配置...")
    semi_auto_deploy_status['steps'][0]['status'] = 'doing'

    set_hostname(servers)
    pubkey_list = []
    for i, server in enumerate(servers):
        ip = server['hostname']
        username = server['username']
        password = server['password']
        port = int(server.get('port', 22))
        semi_auto_deploy_status['log'].append(format_node_log("[1/7] 🔗 正在连接节点", f"(用户: {username}, 端口: {port})...", ip, i, len(servers)))
        ssh = ssh_client(ip, username, password, port)
        semi_auto_deploy_status['log'].append(format_node_log("[1/7] ✅ 节点", "SSH连接成功，开始配置SSH密钥...", ip, i, len(servers)))
        ssh.exec_command("ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa")
        #等待ssh-keygen生成公钥
        time.sleep(1)
        #获取公钥
        stdin, stdout, stderr = ssh.exec_command("cat ~/.ssh/id_rsa.pub")
        pubkey = stdout.read().decode().strip()
        #添加公钥到pubkey_list
        pubkey_list.append(pubkey)
        #添加ip映射到hosts
        server_count = 0
        for server2 in servers:
            server_count += 1
            if server_count <= 1:
                hostname = 'master'
            elif server_count <= len(servers):
                hostname = f'slave{server_count - 1}'
            ssh.exec_command(f"echo '{server2['hostname']}\t{hostname}' >> /etc/hosts")
            #关闭防火墙
            close_firewall(ssh)
        semi_auto_deploy_status['log'].append(format_node_log("[1/7] 🔧 节点", "主机名映射和防火墙配置完成", ip, i, len(servers)))
    
    #添加公钥到authorized_keys
    semi_auto_deploy_status['log'].append("[1/7] 🔑 正在配置SSH免密登录...")
    for server in servers:
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        for pubkey in pubkey_list:
            ssh.exec_command(f"echo '{pubkey}' >> ~/.ssh/authorized_keys")
        ssh.close()

    semi_auto_deploy_status['log'].append(f"[1/7] ✅ 环境检测完成！共配置 {len(servers)} 个节点")
    semi_auto_deploy_status['steps'][0]['status'] = 'done'

    
    semi_auto_deploy_status['progress'] = 20
    semi_auto_deploy_status['step'] = 2
    semi_auto_deploy_status['steps'][1]['status'] = 'doing'
    semi_auto_deploy_status['log'].append("[2/7] ☕ 开始安装Java运行环境...")
    
    for i, server in enumerate(servers):
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))

        #清空配置文件
        ssh.exec_command("rm -rf ~/.hadoop_env")

        semi_auto_deploy_status['log'].append(format_node_log("[2/7] 🔍 检查节点", "的Java环境...", server['hostname'], i, len(servers)))
        stdin, stdout, stderr = ssh.exec_command("which java")
        java_path = stdout.read().decode().strip()
        if not java_path:
            # 优先使用自定义上传的Java包
            java_temp_path = None
            if isinstance(config, dict):
                java_temp_path = config.get('javaTempPath') or config.get('java_temp_path')
            if java_temp_path and os.path.exists(java_temp_path):
                try:
                    semi_auto_deploy_status['log'].append(format_node_log("[2/7] 📦 节点", f"检测到自定义Java包，上传并解压: {java_temp_path}", server['hostname'], i, len(servers)))
                    sftp = ssh.open_sftp()
                    remote_path = f"/opt/{os.path.basename(java_temp_path)}"
                    sftp.put(java_temp_path, remote_path)
                    ssh.exec_command("mkdir -p /opt/java")
                    sftp.close()
                    # 解压（支持tar.gz/tgz/zip）
                    javaHome = "/opt/java"
                    if remote_path.endswith('.zip'):
                        ssh.exec_command(f"unzip -o {remote_path} -d {javaHome} --strip-components=1")
                    else:
                        ssh.exec_command(f"tar -xzf {remote_path} -C {javaHome} --strip-components=1")
                    ssh.exec_command(f"echo 'export JAVA_HOME={javaHome}' >> ~/.hadoop_env")
                    ssh.exec_command(f"echo 'export PATH=$PATH:$JAVA_HOME/bin' >> ~/.hadoop_env")
                    ssh.exec_command(f"echo 'export CLASSPATH=$JAVA_HOME/lib/tools.jar:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/jce.jar' >> ~/.hadoop_env")
                    ssh.exec_command(f"echo 'export JRE_HOME=$JAVA_HOME/jre' >> ~/.hadoop_env")
                    ssh.exec_command(f"echo 'export PATH=$PATH:$JRE_HOME/bin' >> ~/.hadoop_env")
                    ssh.exec_command(f"echo 'export PATH=$PATH:$JAVA_HOME/bin:$JRE_HOME/bin' >> ~/.hadoop_env")
                    ssh.exec_command(f"echo 'export PATH=$PATH:$JAVA_HOME/bin:$JRE_HOME/bin' >> ~/.hadoop_env")
                    ssh.exec_command(f"source ~/.hadoop_env")
                    #删除自定义包
                    os.remove(java_temp_path)
                    semi_auto_deploy_status['log'].append(format_node_log("[2/7] ✅ 节点", f"已用自定义包安装Java: {remote_path}", server['hostname'], i, len(servers)))
                except Exception as e:
                    semi_auto_deploy_status['log'].append(format_node_log("[2/7] ❌ 节点", f"自定义Java包安装失败: {e}", server['hostname'], i, len(servers)))
                    semi_auto_deploy_status['steps'][1]['status'] = 'error'
                    return
            else:
                java_version = basic.get('javaVersion')
                semi_auto_deploy_status['log'].append(format_node_log("[2/7] 📦 节点", f"未检测到Java，开始安装OpenJDK{java_version}...", server['hostname'], i, len(servers)))
                if java_version == '8':
                    stdin, stdout, stderr = ssh.exec_command("yum install -y java-1.8.0-openjdk-devel")
                    javaHome = "/usr/lib/jvm/java-1.8.0-openjdk-1.8.0.312.b07-2.el8_5.x86_64"
                elif java_version == '11':
                    stdin, stdout, stderr = ssh.exec_command("yum install -y java-11-openjdk-devel")
                    javaHome = "/usr/lib/jvm/java-11-openjdk-11.0.13.0.8-4.el8_8.x86_64"
                elif java_version == '17':
                    stdin, stdout, stderr = ssh.exec_command("yum install -y java-17-openjdk-devel")
                    javaHome = "/usr/lib/jvm/java-17-openjdk-17.0.11.0.8-2.el8_8.x86_64"
                semi_auto_deploy_status['log'].append(format_node_log("[2/7] ⏳ 节点", f"正在安装Java{java_version}，请稍候...", server['hostname'], i, len(servers)))
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    semi_auto_deploy_status['log'].append(format_node_log("[2/7] ❌ 节点", f"安装Java{java_version}失败，请检查yum源和权限", server['hostname'], i, len(servers)))
                    semi_auto_deploy_status['steps'][1]['status'] = 'error'
                    return
                semi_auto_deploy_status['log'].append(format_node_log("[2/7] ✅ 节点", f"Java{java_version}安装成功", server['hostname'], i, len(servers)))
        else:
            semi_auto_deploy_status['log'].append(format_node_log("[2/7] ✅ 节点", f"已存在Java环境: {java_path}", server['hostname'], i, len(servers)))

    stdin, stdout, stderr = ssh.exec_command(f"dirname $(dirname $(readlink -f {java_path}))")
    javaHome = stdout.read().decode().strip()

    semi_auto_deploy_status['log'].append(f"[2/7] ✅ Java环境安装完成！共处理 {len(servers)} 个节点")
    semi_auto_deploy_status['steps'][1]['status'] = 'done'
        
    semi_auto_deploy_status['progress'] = 30
    semi_auto_deploy_status['step'] = 3
    semi_auto_deploy_status['steps'][2]['status'] = 'doing'
    semi_auto_deploy_status['log'].append("[3/7] 📦 开始下载并安装Hadoop...")
    
    for i, server in enumerate(servers):
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        # 优先使用自定义上传的Hadoop包
        hadoop_temp_path = None
        if isinstance(config, dict):
            hadoop_temp_path = config.get('hadoopTempPath') or config.get('hadoop_temp_path')
        if hadoop_temp_path and os.path.exists(hadoop_temp_path):
            try:
                semi_auto_deploy_status['log'].append(format_node_log("[3/7] 📦 节点", f"检测到自定义Hadoop包，上传并解压: {hadoop_temp_path}", server['hostname'], i, len(servers)))
                sftp = ssh.open_sftp()
                remote_path = f"/opt/{os.path.basename(hadoop_temp_path)}"
                sftp.put(hadoop_temp_path, remote_path)
                sftp.close()
                ssh.exec_command("yum install -y tar && source /etc/profile")
                ssh.exec_command(f"rm -rf /opt/hadoop && mkdir -p /opt/hadoop")
                stdin, stdout, stderr = ssh.exec_command(f"tar -xzf {remote_path} -C /opt/hadoop --strip-components=1")
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    semi_auto_deploy_status['log'].append(format_node_log("[3/6] ❌ 节点", "解压Hadoop失败，请检查磁盘空间", server['hostname'], i, len(servers)))
                    semi_auto_deploy_status['steps'][2]['status'] = 'error'
                    ssh.close()
                    continue
                #删除自定义包
                os.remove(hadoop_temp_path)
                semi_auto_deploy_status['log'].append(format_node_log("[3/7] ✅ 节点", f"已用自定义包安装Hadoop: {remote_path}", server['hostname'], i, len(servers)))
            except Exception as e:
                semi_auto_deploy_status['log'].append(format_node_log("[3/7] ❌ 节点", f"自定义Hadoop包安装失败: {e}", server['hostname'], i, len(servers)))
                semi_auto_deploy_status['steps'][2]['status'] = 'error'
                ssh.close()
                continue
        else:
            hadoop_version = basic.get('hadoopVersion')
            hadoopHome = basic.get('hadoopHome')
            semi_auto_deploy_status['log'].append(format_node_log("[3/7] 🔍 节点", "检查Hadoop安装包完整性...", server['hostname'], i, len(servers)))
            stdin, stdout, stderr = ssh.exec_command(f"sha256sum {hadoopHome}.tar.gz")
            hadoop_tar_hash = stdout.read().decode().strip()
            if hadoop_tar_hash != f"f5195059c0d4102adaa7fff17f7b2a85df906bcb6e19948716319f9978641a04  {hadoopHome}.tar.gz":
                semi_auto_deploy_status['log'].append(format_node_log("[3/7] ❌ 节点", "Hadoop安装包校验失败", server['hostname'], i, len(servers)))
                ssh.exec_command(f"rm -rf {hadoopHome}.tar.gz")
                semi_auto_deploy_status['log'].append(format_node_log("[3/7] 📥 节点", f"开始下载Hadoop {hadoop_version}...", server['hostname'], i, len(servers)))
                stdin, stdout, stderr = ssh.exec_command(f"curl -o {hadoopHome}.tar.gz https://mirrors.aliyun.com/apache/hadoop/common/hadoop-{hadoop_version}/hadoop-{hadoop_version}.tar.gz",timeout=70)
                exit_code = stdout.channel.recv_exit_status()
                if exit_code != 0:
                    semi_auto_deploy_status['log'].append(format_node_log("[3/7] ❌ 节点", "下载Hadoop失败，请检查网络连接", server['hostname'], i, len(servers)))
                    semi_auto_deploy_status['steps'][2]['status'] = 'error'
                else:
                    semi_auto_deploy_status['log'].append(format_node_log("[3/7] ✅ 节点", "Hadoop下载完成", server['hostname'], i, len(servers)))
            else:
                ssh.exec_command(f"rm -rf {hadoopHome}")
                semi_auto_deploy_status['log'].append(format_node_log("[3/7] ✅ 节点", f"Hadoop安装包{hadoop_version}已存在且校验通过", server['hostname'], i, len(servers)))
            semi_auto_deploy_status['log'].append(format_node_log("[3/7] 📂 节点", "开始解压Hadoop...", server['hostname'], i, len(servers)))
            ssh.exec_command("yum install -y tar && source /etc/profile")
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {hadoopHome} && tar -xzf {hadoopHome}.tar.gz -C {hadoopHome} --strip-components=1")
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                semi_auto_deploy_status['log'].append(format_node_log("[3/7] ❌ 节点", "解压Hadoop失败，请检查磁盘空间", server['hostname'], i, len(servers)))
                semi_auto_deploy_status['steps'][2]['status'] = 'error'
                ssh.close()
                continue
            # ssh.exec_command(f"mv /opt/hadoop-3.3.6/* /opt/hadoop/ && rm -rf /opt/hadoop-3.3.6")
            auto_deploy_status['log'].append(format_node_log("[3/7] ✅ 节点", "Hadoop安装完成", server['hostname'], i, len(servers)))
        ssh.close()
    
    semi_auto_deploy_status['log'].append(f"[3/7] ✅ Hadoop安装完成！共处理 {len(servers)} 个节点")
    semi_auto_deploy_status['steps'][2]['status'] = 'done'
    semi_auto_deploy_status['progress'] = 40
    semi_auto_deploy_status['step'] = 4
    semi_auto_deploy_status['steps'][3]['status'] = 'doing'
    semi_auto_deploy_status['log'].append("[4/7] ⚙️ 开始配置Hadoop核心参数...")

    for i, server in enumerate(servers):
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        semi_auto_deploy_status['log'].append(format_node_log("[4/7] 🔧 节点", "开始配置Hadoop参数...", server['hostname'], i, len(servers)))

        namenodeHost = basic.get('namenodeHost')
        dataDir = basic.get('dataDir')
        ssh.exec_command(f"rm -rf {dataDir} && mkdir -p {dataDir}")
        semi_auto_deploy_status['log'].append(format_node_log("[4/7] 📄 节点", f"配置core-site.xml (主节点: {namenodeHost})", server['hostname'], i, len(servers)))
        ssh.exec_command(f"echo '{generate_core_site(namenodeHost, dataDir)}' > {hadoopHome}/etc/hadoop/core-site.xml")

        replicationFactor = cluster.get('replicationFactor')
        namenodeDir = dataDir + "/data/dfs/namenode"
        datanodeDir = dataDir + "/data/dfs/datanode"
        semi_auto_deploy_status['log'].append(format_node_log("[4/7] 📄 节点", f"配置hdfs-site.xml (副本数: {replicationFactor})", server['hostname'], i, len(servers)))
        ssh.exec_command(f"echo '{generate_hdfs_site(replicationFactor, namenodeDir, datanodeDir)}' > {hadoopHome}/etc/hadoop/hdfs-site.xml")
        
        mapReduceMemory = cluster.get('mapReduceMemory')
        mapReduceCores = cluster.get('mapReduceCores')
        semi_auto_deploy_status['log'].append(format_node_log("[4/7] 📄 节点", f"配置mapred-site.xml (MapReduce内存: {mapReduceMemory}MB, 核心数: {mapReduceCores})", server['hostname'], i, len(servers)))
        ssh.exec_command(f"echo '{generate_mapred_site(mapReduceMemory, mapReduceCores)}' > {hadoopHome}/etc/hadoop/mapred-site.xml")

        yarnMemory = cluster.get('yarnMemory')
        yarnCores = cluster.get('yarnCores')
        semi_auto_deploy_status['log'].append(format_node_log("[4/7] 📄 节点", f"配置yarn-site.xml (资源管理器: {yarnMemory}MB, 核心数: {yarnCores})", server['hostname'], i, len(servers)))
        ssh.exec_command(f"echo '{generate_yarn_site(namenodeHost, yarnMemory, yarnCores)}' > {hadoopHome}/etc/hadoop/yarn-site.xml")

        datanodeCount = cluster.get('datanodeCount')
        datanodeCount = int(datanodeCount)
        semi_auto_deploy_status['log'].append(format_node_log("[4/7] 📄 节点", f"配置workers文件 (DataNode数量: {datanodeCount})", server['hostname'], i, len(servers)))
        workers_content = ''.join([server + '\n' for server in generate_workers(servers, datanodeCount)])
        ssh.exec_command(f"echo '{workers_content}' > {hadoopHome}/etc/hadoop/workers")

        semi_auto_deploy_status['log'].append(format_node_log("[4/7] 📄 节点", "配置hadoop-env.sh", server['hostname'], i, len(servers)))
        ssh.exec_command(f"echo 'export JAVA_HOME={javaHome}' > {hadoopHome}/etc/hadoop/hadoop-env.sh")

        semi_auto_deploy_status['log'].append(format_node_log("[4/7] 🔧 节点", "配置环境变量", server['hostname'], i, len(servers)))
        env_content = f"""
export JAVA_HOME={javaHome}
export HADOOP_HOME={hadoopHome}
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
export HADOOP_OPTS=\"-Djava.library.path=$HADOOP_HOME/lib/native\"
export HDFS_NAMENODE_USER=root
export HDFS_DATANODE_USER=root
export HDFS_SECONDARYNAMENODE_USER=root
export YARN_RESOURCEMANAGER_USER=root
export YARN_NODEMANAGER_USER=root"""
        ssh.exec_command(f"echo '{env_content}' > ~/.hadoop_env && source ~/.hadoop_env")
        auto_deploy_status['log'].append(format_node_log("[4/7] ✅ 节点", "Hadoop配置完成", server['hostname'], i, len(servers)))
        ssh.close()
    
    semi_auto_deploy_status['log'].append(f"[4/6] ✅ Hadoop配置完成！共配置 {datanodeCount} 个DataNode")
    semi_auto_deploy_status['steps'][3]['status'] = 'done'

    semi_auto_deploy_status['progress'] = 50
    semi_auto_deploy_status['step'] = 5
    semi_auto_deploy_status['steps'][4]['status'] = 'doing'
    installHive = components.get('installHive')
    installHBase = components.get('installHBase')
    installSpark = components.get('installSpark')
    installZooKeeper = components.get('installZooKeeper')
    installKafka = components.get('installKafka')
    installPig = components.get('installPig')
    
    installItems = []
    if installHive:
        installItems.append('Hive')
        semi_auto_deploy_status['log'].append(f"[5/7] 🔍 节点 {servers[0]['hostname']} 开始安装Hive...")
        ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
        stdin, stdout, stderr = ssh.exec_command(f"curl -o /opt/hive.tar.gz https://mirrors.aliyun.com/apache/hive/hive-4.0.1/apache-hive-4.0.1-bin.tar.gz")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            semi_auto_deploy_status['log'].append(format_node_log("[5/7] ❌ 节点", "Hive下载失败，请检查网络", server['hostname'], i, len(servers)))
            semi_auto_deploy_status['steps'][4]['status'] = 'error'
            return
        ssh.exec_command(f"mkdir -p /opt/hive && tar -xzf /opt/hive.tar.gz -C /opt/hive --strip-components=1")
        ssh.exec_command(f"echo 'export HIVE_HOME=/opt/hive' >> ~/.hadoop_env")
        ssh.exec_command(f"echo 'export PATH=$PATH:$HIVE_HOME/bin' >> ~/.hadoop_env")
        ssh.exec_command(f"source ~/.hadoop_env")
        ssh.close()
        semi_auto_deploy_status['log'].append(f"[5/7] ✅ 节点 {servers[0]['hostname']} Hive安装完成")

    if installHBase:
        installItems.append('HBase')
        semi_auto_deploy_status['log'].append(f"[5/7] 🔍 节点 {servers[0]['hostname']} 开始安装HBase...")
        ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
        stdin, stdout, stderr = ssh.exec_command(f"curl -o /opt/hbase.tar.gz https://mirrors.aliyun.com/apache/hbase/2.6.2/hbase-2.6.2-hadoop3-bin.tar.gz")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            semi_auto_deploy_status['log'].append(format_node_log("[5/7] ❌ 节点", "HBase下载失败，请检查网络", server['hostname'], i, len(servers)))
            semi_auto_deploy_status['steps'][4]['status'] = 'error'
            return
        ssh.exec_command(f"mkdir -p /opt/hbase && tar -xzf /opt/hbase.tar.gz -C /opt/hbase --strip-components=1")
        ssh.exec_command(f"echo 'export HBASE_HOME=/opt/hbase' >> ~/.hadoop_env")
        ssh.exec_command(f"echo 'export PATH=$PATH:$HBASE_HOME/bin' >> ~/.hadoop_env")
        ssh.exec_command(f"source ~/.hadoop_env")
        ssh.close()
        semi_auto_deploy_status['log'].append(f"[5/7] ✅ 节点 {servers[0]['hostname']} HBase安装完成")

    if installSpark:
        installItems.append('Spark')
        semi_auto_deploy_status['log'].append(f"[5/7] 🔍 节点 {servers[0]['hostname']} 开始安装Spark...")
        ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
        stdin, stdout, stderr = ssh.exec_command(f"curl -o /opt/spark.tar.gz https://mirrors.aliyun.com/apache/spark/spark-4.0.0/spark-4.0.0-bin-hadoop3.tgz")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            semi_auto_deploy_status['log'].append(format_node_log("[5/7] ❌ 节点", "Spark下载失败，请检查网络", server['hostname'], i, len(servers)))
            semi_auto_deploy_status['steps'][4]['status'] = 'error'
            return
        ssh.exec_command(f"mkdir -p /opt/spark && tar -xzf /opt/spark.tar.gz -C /opt/spark --strip-components=1")
        ssh.exec_command(f"echo 'export SPARK_HOME=/opt/spark' >> ~/.hadoop_env")
        ssh.exec_command(f"echo 'export PATH=$PATH:$SPARK_HOME/bin' >> ~/.hadoop_env")
        ssh.exec_command(f"source ~/.hadoop_env")
        ssh.close()
        semi_auto_deploy_status['log'].append(f"[5/7] ✅ 节点 {servers[0]['hostname']} Spark安装完成")

    if installZooKeeper:
        installItems.append('ZooKeeper')
        semi_auto_deploy_status['log'].append(f"[5/7] 🔍 节点 {servers[0]['hostname']} 开始安装ZooKeeper...")
        ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
        stdin, stdout, stderr = ssh.exec_command(f"curl -o /opt/zookeeper.tar.gz https://mirrors.aliyun.com/apache/zookeeper/zookeeper-3.7.2/apache-zookeeper-3.7.2-bin.tar.gz")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            semi_auto_deploy_status['log'].append(format_node_log("[5/7] ❌ 节点", "ZooKeeper下载失败，请检查网络", server['hostname'], i, len(servers)))
            semi_auto_deploy_status['steps'][4]['status'] = 'error'
            return
        ssh.exec_command(f"mkdir -p /opt/zookeeper && tar -xzf /opt/zookeeper.tar.gz -C /opt/zookeeper --strip-components=1")
        ssh.exec_command(f"echo 'export ZOOKEEPER_HOME=/opt/zookeeper' >> ~/.hadoop_env")
        ssh.exec_command(f"echo 'export PATH=$PATH:$ZOOKEEPER_HOME/bin' >> ~/.hadoop_env")
        ssh.exec_command(f"source ~/.hadoop_env")
        ssh.close()
        semi_auto_deploy_status['log'].append(f"[5/7] ✅ 节点 {servers[0]['hostname']} ZooKeeper安装完成")

    if installKafka:
        installItems.append('Kafka')
        semi_auto_deploy_status['log'].append(f"[5/7] 🔍 节点 {servers[0]['hostname']} 开始安装Kafka...")
        ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
        stdin, stdout, stderr = ssh.exec_command(f"curl -o /opt/kafka.tar.gz https://mirrors.aliyun.com/apache/kafka/3.9.0/kafka_2.13-3.9.0.tgz")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            semi_auto_deploy_status['log'].append(format_node_log("[5/7] ❌ 节点", "Kafka下载失败，请检查网络", server['hostname'], i, len(servers)))
            semi_auto_deploy_status['steps'][4]['status'] = 'error'
            return
        ssh.exec_command(f"mkdir -p /opt/kafka && tar -xzf /opt/kafka.tar.gz -C /opt/kafka --strip-components=1")
        ssh.exec_command(f"echo 'export KAFKA_HOME=/opt/kafka' >> ~/.hadoop_env")
        ssh.exec_command(f"echo 'export PATH=$PATH:$KAFKA_HOME/bin' >> ~/.hadoop_env")
        ssh.exec_command(f"source ~/.hadoop_env")
        ssh.close()
        semi_auto_deploy_status['log'].append(f"[5/7] ✅ 节点 {servers[0]['hostname']} Kafka安装完成")
        
    if installPig:
        installItems.append('Pig')
        semi_auto_deploy_status['log'].append(f"[5/7] 🔍 节点 {servers[0]['hostname']} 开始安装Pig...")
        ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
        stdin, stdout, stderr = ssh.exec_command(f"curl -o /opt/pig.tar.gz https://mirrors.aliyun.com/apache/pig/pig-0.17.0/pig-0.17.0.tar.gz")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            semi_auto_deploy_status['log'].append(format_node_log("[5/7] ❌ 节点", "Pig下载失败，请检查网络", server['hostname'], i, len(servers)))
            semi_auto_deploy_status['steps'][4]['status'] = 'error'
            return
        ssh.exec_command(f"mkdir -p /opt/pig && tar -xzf /opt/pig.tar.gz -C /opt/pig --strip-components=1")
        ssh.exec_command(f"echo 'export PIG_HOME=/opt/pig' >> ~/.hadoop_env")
        ssh.exec_command(f"echo 'export PATH=$PATH:$PIG_HOME/bin' >> ~/.hadoop_env")
        ssh.exec_command(f"source ~/.hadoop_env")
        ssh.close()
        semi_auto_deploy_status['log'].append(f"[5/7] ✅ 节点 {servers[0]['hostname']} Pig安装完成")

    if installItems:
        semi_auto_deploy_status['log'].append(f"[5/7] ✅ 节点 {servers[0]['hostname']} 安装{', '.join(installItems)}完成")
    else:  
        semi_auto_deploy_status['log'].append(f"[5/7] ✅ 节点 {servers[0]['hostname']} 未安装任何组件")
        
    semi_auto_deploy_status['steps'][4]['status'] = 'done'

    semi_auto_deploy_status['progress'] = 60
    semi_auto_deploy_status['step'] = 6
    semi_auto_deploy_status['steps'][5]['status'] = 'doing'
    semi_auto_deploy_status['log'].append("[6/7] 🚀 开始启动Hadoop集群服务...")
    
    # 在所有节点上检查并停止Hadoop服务
    semi_auto_deploy_status['log'].append("[6/7] 🔍 检查所有节点上的Hadoop服务状态...")
    for i, server in enumerate(servers):
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        
        # 检查是否有Hadoop进程在运行
        semi_auto_deploy_status['log'].append(format_node_log("[6/7] 🔍 检查节点", "上的Hadoop进程...", server['hostname'], i, len(servers)))
        stdin, stdout, stderr = ssh.exec_command("source ~/.hadoop_env && ps aux | grep -E '(hadoop|java.*hadoop)' | grep -v grep", timeout=30)
        running_processes = stdout.read().decode().strip()
        
        if running_processes:
            semi_auto_deploy_status['log'].append(format_node_log("[6/7] ⏹️ 节点", "发现运行中的Hadoop进程，开始停止...", server['hostname'], i, len(servers)))
            # 正常停止服务
            stdin,stdout,stderr = ssh.exec_command(f"source ~/.hadoop_env && {hadoopHome}/sbin/stop-all.sh", timeout=60)
            stdout.channel.recv_exit_status()
            time.sleep(2)
            
            # 强制终止剩余进程
            ssh.exec_command("source ~/.hadoop_env && pkill -f hadoop 2>/dev/null || true", timeout=30)
            ssh.exec_command("source ~/.hadoop_env && pkill -f java.*hadoop 2>/dev/null || true", timeout=30)
            time.sleep(1)
            
            # 再次检查是否还有进程
            stdin, stdout, stderr = ssh.exec_command("source ~/.hadoop_env && ps aux | grep -E '(hadoop|java.*hadoop)' | grep -v grep", timeout=30)
            remaining_processes = stdout.read().decode().strip()
            
            if remaining_processes:
                semi_auto_deploy_status['log'].append(format_node_log("[6/7] ⚡ 节点", "仍有Hadoop进程运行，强制终止...", server['hostname'], i, len(servers)))
                ssh.exec_command("source ~/.hadoop_env && pkill -9 -f hadoop 2>/dev/null || true", timeout=30)
                ssh.exec_command("source ~/.hadoop_env && pkill -9 -f java.*hadoop 2>/dev/null || true", timeout=30)
            else:
                semi_auto_deploy_status['log'].append(format_node_log("[6/7] ✅ 节点", "的Hadoop服务已成功停止", server['hostname'], i, len(servers)))
        else:
            semi_auto_deploy_status['log'].append(format_node_log("[6/7] ✅ 节点", "没有运行中的Hadoop进程", server['hostname'], i, len(servers)))
        
        ssh.close()
    
    time.sleep(3)  # 等待所有节点服务完全停止
    
    # 在主节点上进行namenode操作
    ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
    
    # 检查namenode是否已经初始化
    semi_auto_deploy_status['log'].append(f"[6/7] 🔍 检查主节点 {servers[0]['hostname']} 的namenode状态...")
    
    # 首先创建必要的目录
    ssh.exec_command(f"source ~/.hadoop_env && mkdir -p {hadoopHome}/data/dfs/namenode")
    ssh.exec_command(f"source ~/.hadoop_env && mkdir -p {hadoopHome}/data/dfs/datanode")
    
    # 检查VERSION文件是否存在
    stdin, stdout, stderr = ssh.exec_command(
        f"source ~/.hadoop_env && (test -f {hadoopHome}/data/dfs/namenode/current/VERSION && echo 'EXIST' || echo 'NOT_EXIST'",
        timeout=30
    )
    namenode_exists = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if err:
        semi_auto_deploy_status['log'].append(f"[调试] 检查VERSION文件时错误: {err}")

    if namenode_exists == "EXIST":
        semi_auto_deploy_status['log'].append(f"[6/7] ✅ 主节点 {servers[0]['hostname']} namenode已初始化，跳过格式化步骤")
    else:
        # 进行格式化
        semi_auto_deploy_status['log'].append(f"[6/7] 🔧 主节点 {servers[0]['hostname']} namenode未初始化，开始格式化...")
        stdin, stdout, stderr = ssh.exec_command("source ~/.hadoop_env && hadoop namenode -format", timeout=120)
        err_msg = stderr.read().decode().strip()
        # 等待namenode初始化完成
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            semi_auto_deploy_status['log'].append(f"[6/7] ❌ 主节点 {servers[0]['hostname']} namenode格式化失败: {err_msg}")
            semi_auto_deploy_status['steps'][5]['status'] = 'error'
            return
        semi_auto_deploy_status['log'].append(f"[6/7] ✅ 主节点 {servers[0]['hostname']} namenode格式化完成")
    
    # 启动Hadoop集群服务
    ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
    semi_auto_deploy_status['log'].append(f"[6/7] 🚀 从主节点 {servers[0]['hostname']} 启动Hadoop集群服务...")
    stdin,stdout,stderr = ssh.exec_command("source ~/.hadoop_env && start-all.sh")
    stdout.channel.recv_exit_status()
    semi_auto_deploy_status['log'].append(f"[6/7] ✅ Hadoop集群服务启动完成")
    semi_auto_deploy_status['steps'][5]['status'] = 'done'
    semi_auto_deploy_status['progress'] = 80
    semi_auto_deploy_status['step'] = 7
    semi_auto_deploy_status['steps'][6]['status'] = 'doing'
    semi_auto_deploy_status['log'].append("[7/7] 🔍 开始验证Hadoop集群运行状态...")
    semi_auto_deploy_status['log'].append(f"[7/7] 🔍 测试HDFS文件系统访问 (主节点: {servers[0]['hostname']})...")
    ssh.exec_command(f"source ~/.hadoop_env && hdfs dfs -chmod -R 777 /")
    stdin,stdout,stderr = ssh.exec_command("source ~/.hadoop_env && hdfs dfs -ls /",timeout=120)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        semi_auto_deploy_status['log'].append(f"[7/7] ❌ HDFS文件系统验证失败，请检查集群状态")
        semi_auto_deploy_status['steps'][6]['status'] = 'error'
        return
    
    semi_auto_deploy_status['log'].append(f"[7/7] ✅ HDFS文件系统验证成功")
    semi_auto_deploy_status['log'].append(f"[7/7] 🎉 Hadoop集群部署完成！共 {len(servers)} 个节点")
    semi_auto_deploy_status['log'].append(f"[7/7]  已安装的组件: {', '.join(installItems)}均位于/opt目录下")
    semi_auto_deploy_status['log'].append(f"[7/7]  请在主节点{servers[0]['hostname']}上执行source ~/.hadoop_env命令，使环境变量生效")
    semi_auto_deploy_status['progress'] = 100
    semi_auto_deploy_status['status'] = 'done'
    semi_auto_deploy_status['steps'][6]['status'] = 'done'
    
    # 生成集群访问链接
    nn_url = f'http://{servers[0]["hostname"]}:9870'
    rm_url = f'http://{servers[0]["hostname"]}:8088'
    semi_auto_deploy_status['cluster_links'] = {
        'NameNode': nn_url,
        'ResourceManager': rm_url
    }
    semi_auto_deploy_status['log'].append(f"[6/6] 🌐 集群Web UI已就绪，主节点: {servers[0]['hostname']}")
        
@app.route('/api/log', methods=['GET', 'POST'])
def get_log():
    logs = auto_deploy_status['log'] if isinstance(auto_deploy_status, dict) and 'log' in auto_deploy_status else []
    log_content = '\n'.join(logs)
    return Response(log_content, mimetype='text/plain')

@app.route('/api/deploy/auto/status', methods=['GET', 'POST'])
def api_deploy_auto_status():
    return jsonify(auto_deploy_status)

@app.route('/api/deploy/semi-auto/status')
def api_deploy_semi_auto_status():
    return jsonify(semi_auto_deploy_status)

@app.route('/api/deploy/auto/clear-logs', methods=['POST'])
def api_deploy_auto_clear_logs():
    """清空部署日志"""
    try:
        auto_deploy_status['log'] = []
        return jsonify({'success': True, 'message': '日志已清空'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def get_webhdfs_url(path, namenode_host=None):
    host = namenode_host or 'localhost'
    if host.startswith('http://'):
        host = host[len('http://'):]
    elif host.startswith('https://'):
        host = host[len('https://'):]
    
    # 确保路径格式正确，避免双斜杠
    if path.startswith('/'):
        path = path[1:]  # 移除开头的斜杠
    return f'http://{host}/webhdfs/v1/{path}'

@app.route('/api/hdfs/list')
def hdfs_list():
    path = request.args.get('path', '/')
    namenode_host = request.args.get('namenodeHost')
    url = get_webhdfs_url(path, namenode_host) + f'?op=LISTSTATUS&user.name=hadoop'
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return jsonify({'success': True, 'files': data['FileStatuses']['FileStatus']})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

def replace_master_with_ip(url, ip):
    # 替换URL中的主机名为IP
    if url.find('master') != -1:
        return re.sub(r'//master(:\d+)?', f'//{ip}\\1', url)
    else:
        return re.sub(r'//slave(:\d+)?', f'//{ip}\\1', url)

@app.route('/api/hdfs/upload', methods=['POST'])
def hdfs_upload():
    file = request.files.get('file')
    hdfs_path = request.form.get('path', '/')
    namenode_host = request.form.get('namenodeHost')
    if not file:
        return jsonify({'success': False, 'msg': '请选择文件'})
    # 正确处理路径拼接，避免双斜杠
    if hdfs_path == '/':
        full_path = f'/{file.filename}'
    else:
        full_path = f'{hdfs_path}/{file.filename}'
    url = get_webhdfs_url(full_path, namenode_host) + f'?op=CREATE&overwrite=true&user.name=hadoop'
    if namenode_host:
        url = replace_master_with_ip(url, namenode_host.split(':')[0])
    try:
        resp = requests.put(url, allow_redirects=False)
        if resp.status_code in (307, 201):
            upload_url = resp.headers['Location'] if 'Location' in resp.headers else url
            # 对跳转地址也做主机名替换
            if namenode_host:
                upload_url = replace_master_with_ip(upload_url, namenode_host.split(':')[0])
            resp2 = requests.put(upload_url, data=file.stream, headers={'Content-Type': 'application/octet-stream'})
            resp2.raise_for_status()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'msg': resp.text})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/hdfs/download')
def hdfs_download():
    hdfs_path = request.args.get('path', '/')
    namenode_host = request.args.get('namenodeHost')
    url = get_webhdfs_url(hdfs_path, namenode_host) + f'?op=OPEN&user.name=hadoop'
    if namenode_host:
        url = replace_master_with_ip(url, namenode_host.split(':')[0])
    try:
        resp = requests.get(url, allow_redirects=False, stream=True)
        # 检查是否需要跳转
        if resp.status_code == 307 and 'Location' in resp.headers:
            download_url = resp.headers['Location']
            if namenode_host:
                download_url = replace_master_with_ip(download_url, namenode_host.split(':')[0])
            resp2 = requests.get(download_url, stream=True)
            resp2.raise_for_status()
            file_data = BytesIO(resp2.content)
        else:
            resp.raise_for_status()
            file_data = BytesIO(resp.content)
        return send_file(file_data, download_name=hdfs_path.split('/')[-1], as_attachment=True)
    except Exception as e:
        return f'下载失败: {e}', 500

@app.route('/api/hdfs/delete', methods=['POST'])
def hdfs_delete():
    data = request.get_json()
    path = data.get('path')
    recursive = data.get('recursive', False)
    namenode_host = data.get('namenodeHost')
    if not path:
        return jsonify({'success': False, 'msg': '参数错误'})
    url = get_webhdfs_url(path, namenode_host) + f'?op=DELETE&recursive={'true' if recursive else 'false'}&user.name=hadoop'
    try:
        resp = requests.delete(url)
        resp.raise_for_status()
        result = resp.json()
        if result.get('boolean'):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'msg': '删除失败'})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/hdfs/create', methods=['POST'])
def hdfs_create():
    data = request.get_json()
    path = data.get('path')
    namenode_host = data.get('namenodeHost')
    type_ = data.get('type', 'file')
    if not path or not namenode_host:
        return jsonify({'success': False, 'msg': '参数错误'})
    if type_ == 'directory':
        url = get_webhdfs_url(path, namenode_host) + f'?op=MKDIRS&user.name=hadoop'
        try:
            resp = requests.put(url)
            resp.raise_for_status()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'msg': str(e)})
    else:  # 新建空文件
        url = get_webhdfs_url(path, namenode_host) + f'?op=CREATE&overwrite=false&user.name=hadoop'
        if namenode_host:
            url = replace_master_with_ip(url, namenode_host.split(':')[0])
        try:
            resp = requests.put(url, allow_redirects=False)
            if resp.status_code in (307, 201):
                upload_url = resp.headers['Location'] if 'Location' in resp.headers else url
                # 对跳转地址也做主机名替换
                if namenode_host:
                    upload_url = replace_master_with_ip(upload_url, namenode_host.split(':')[0])
                resp2 = requests.put(upload_url, data=b'', headers={'Content-Type': 'application/octet-stream'})
                resp2.raise_for_status()
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'msg': resp.text})
        except Exception as e:
            return jsonify({'success': False, 'msg': str(e)})

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=5000)
