from flask import Flask, render_template, request, flash, jsonify, send_from_directory, abort, Response
import paramiko
import os
import subprocess
import platform
from io import StringIO
import threading
import time
import json
from jinja2 import TemplateNotFound
import ast
import re
from threading import Thread
import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'tar.gz', 'tgz'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 2)[-2:] in (['tar', 'gz'], ['tgz'])

# 全自动部署进度状态
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

# 半自动部署状态
semi_auto_deploy_status = {
    'status': 'idle',
    'step': 0,
    'progress': 0,
    'log': [],
    'steps': [],
    'cluster_links': {},
}

def execute_ssh_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.read().decode(), stderr.read().decode()

def execute_local_command(command, timeout=30):
    """执行本地命令并返回结果"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)

def check_system_environment():
    """检查系统环境"""
    auto_deploy_status['log'].append("开始检查系统环境...")
    
    # 检查操作系统
    system = platform.system()
    auto_deploy_status['log'].append(f"操作系统: {system}")
    
    # 检查Java
    code, stdout, stderr = execute_local_command("java -version")
    if code == 0:
        auto_deploy_status['log'].append("Java已安装")
        java_version = stdout.split('\n')[0] if stdout else "未知版本"
        auto_deploy_status['log'].append(f"Java版本: {java_version}")
    else:
        auto_deploy_status['log'].append("Java未安装，需要安装Java")
        return False
    
    # 检查内存
    if system == "Windows":
        code, stdout, stderr = execute_local_command("wmic computersystem get TotalPhysicalMemory")
        if code == 0:
            memory_mb = int(stdout.split('\n')[1]) // (1024 * 1024)
            auto_deploy_status['log'].append(f"系统内存: {memory_mb} MB")
    else:
        code, stdout, stderr = execute_local_command("free -m | grep Mem")
        if code == 0:
            memory_mb = int(stdout.split()[1])
            auto_deploy_status['log'].append(f"系统内存: {memory_mb} MB")
    
    # 检查磁盘空间
    if system == "Windows":
        code, stdout, stderr = execute_local_command("wmic logicaldisk get size,freespace,caption")
        if code == 0:
            auto_deploy_status['log'].append("磁盘空间检查完成")
    else:
        code, stdout, stderr = execute_local_command("df -h")
        if code == 0:
            auto_deploy_status['log'].append("磁盘空间检查完成")
    
    return True

def install_java():
    """安装Java环境"""
    auto_deploy_status['log'].append("开始安装Java环境...")
    system = platform.system()
    # 检查Java是否已安装
    code, stdout, stderr = execute_local_command("java -version")
    if code == 0:
        auto_deploy_status['log'].append("Java已安装，跳过安装步骤")
        return True
    # 未安装则自动安装
    auto_deploy_status['log'].append("未检测到Java，尝试自动安装...")
    if system == "Windows":
        auto_deploy_status['log'].append("请手动安装Java 8或更高版本（暂不支持自动安装）")
        return False
    else:
        # Linux下尝试安装OpenJDK
        auto_deploy_status['log'].append("尝试安装OpenJDK...")
        # 检测包管理器
        code, stdout, stderr = execute_local_command("which apt-get")
        if code == 0:
            # Ubuntu/Debian
            code, stdout, stderr = execute_local_command("sudo apt-get update && sudo apt-get install -y openjdk-8-jdk", timeout=300)
        else:
            code, stdout, stderr = execute_local_command("which yum")
            if code == 0:
                # CentOS/RHEL
                code, stdout, stderr = execute_local_command("sudo yum install -y java-1.8.0-openjdk java-1.8.0-openjdk-devel", timeout=300)
            else:
                auto_deploy_status['log'].append("未检测到支持的包管理器，请手动安装Java")
                return False
        if code == 0:
            auto_deploy_status['log'].append("Java安装成功")
            return True
        else:
            auto_deploy_status['log'].append(f"Java安装失败: {stderr}")
            return False

def download_hadoop():
    """下载Hadoop"""
    auto_deploy_status['log'].append("开始下载Hadoop...")
    hadoop_version = "3.3.6"
    # 优先使用用户上传的安装包
    uploaded_file = os.path.join(os.getcwd(), 'uploads', 'hadoop-uploaded.tar.gz')
    if os.path.exists(uploaded_file):
        auto_deploy_status['log'].append('检测到用户上传的Hadoop安装包，直接使用')
        return uploaded_file
    
    # 创建下载目录
    download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    # 检查是否已下载
    hadoop_file = os.path.join(download_dir, f"hadoop-{hadoop_version}.tar.gz")
    if os.path.exists(hadoop_file):
        auto_deploy_status['log'].append("Hadoop已下载，跳过下载步骤")
        return hadoop_file
    
    # 定义下载源列表（按优先级排序）
    download_sources = [
        f"https://archive.apache.org/dist/hadoop/common/hadoop-{hadoop_version}/hadoop-{hadoop_version}.tar.gz",
        f"https://mirrors.tuna.tsinghua.edu.cn/apache/hadoop/common/hadoop-{hadoop_version}/hadoop-{hadoop_version}.tar.gz",
        f"https://mirrors.aliyun.com/apache/hadoop/common/hadoop-{hadoop_version}/hadoop-{hadoop_version}.tar.gz",
        f"https://mirrors.huaweicloud.com/apache/hadoop/common/hadoop-{hadoop_version}/hadoop-{hadoop_version}.tar.gz",
        f"https://mirror.bit.edu.cn/apache/hadoop/common/hadoop-{hadoop_version}/hadoop-{hadoop_version}.tar.gz"
    ]
    
    # 尝试从不同源下载
    for source_url in download_sources:
        auto_deploy_status['log'].append(f"尝试从源下载: {source_url}")
        
        try:
            # 检查网络连接
            if platform.system() == "Windows":
                # Windows检查连接
                check_cmd = f'powershell -Command "(Invoke-WebRequest -Uri \'{source_url}\' -UseBasicParsing -Method Head).StatusCode"'
                code, stdout, stderr = execute_local_command(check_cmd, timeout=10)
                if code == 0 and stdout.strip() == "200":
                    auto_deploy_status['log'].append("源可用，开始下载...")
                    
                    # 下载文件
                    download_cmd = f'powershell -Command "Invoke-WebRequest -Uri \'{source_url}\' -OutFile \'{hadoop_file}\' -UseBasicParsing"'
                    code, stdout, stderr = execute_local_command(download_cmd, timeout=300)
                    
                    if code == 0 and os.path.exists(hadoop_file):
                        file_size = os.path.getsize(hadoop_file)
                        if file_size > 100 * 1024 * 1024:  # 检查文件大小是否合理（>100MB）
                            auto_deploy_status['log'].append(f"Hadoop下载成功 (源: {source_url})")
                            # 自动解压步骤
                            # 使用绝对路径解压
                            abs_hadoop_file = os.path.abspath(hadoop_file)
                            abs_download_dir = os.path.abspath(download_dir)
                            extract_cmd = f"tar -xzf '{abs_hadoop_file}' -C '{abs_download_dir}'"
                            code2, stdout2, stderr2 = execute_local_command(extract_cmd, timeout=120)
                            if code2 == 0:
                                auto_deploy_status['log'].append(f"自动解压完成: {abs_download_dir}")
                            else:
                                auto_deploy_status['log'].append(f"自动解压失败: {stderr2}")
                            return hadoop_file
                        else:
                            auto_deploy_status['log'].append("下载的文件大小异常，可能下载失败")
                            os.remove(hadoop_file)
                    else:
                        auto_deploy_status['log'].append(f"从 {source_url} 下载失败")
                        if os.path.exists(hadoop_file):
                            os.remove(hadoop_file)
                else:
                    auto_deploy_status['log'].append(f"源不可用: {source_url}")
            else:
                # Linux检查连接
                check_cmd = f"curl -s --head '{source_url}' | head -n 1 | grep 'HTTP/1.[01] [23]..'"
                code, stdout, stderr = execute_local_command(check_cmd, timeout=10)
                if code == 0:
                    auto_deploy_status['log'].append("源可用，开始下载...")
                    
                    # 下载文件
                    download_cmd = f"wget -O '{hadoop_file}' '{source_url}'"
                    code, stdout, stderr = execute_local_command(download_cmd, timeout=300)
                    
                    if code == 0 and os.path.exists(hadoop_file):
                        file_size = os.path.getsize(hadoop_file)
                        if file_size > 100 * 1024 * 1024:  # 检查文件大小是否合理（>100MB）
                            auto_deploy_status['log'].append(f"Hadoop下载成功 (源: {source_url})")
                            # 自动解压步骤
                            # 使用绝对路径解压
                            abs_hadoop_file = os.path.abspath(hadoop_file)
                            abs_download_dir = os.path.abspath(download_dir)
                            extract_cmd = f"tar -xzf '{abs_hadoop_file}' -C '{abs_download_dir}'"
                            code2, stdout2, stderr2 = execute_local_command(extract_cmd, timeout=120)
                            if code2 == 0:
                                auto_deploy_status['log'].append(f"自动解压完成: {abs_download_dir}")
                            else:
                                auto_deploy_status['log'].append(f"自动解压失败: {stderr2}")
                            return hadoop_file
                        else:
                            auto_deploy_status['log'].append("下载的文件大小异常，可能下载失败")
                            os.remove(hadoop_file)
                    else:
                        auto_deploy_status['log'].append(f"从 {source_url} 下载失败")
                        if os.path.exists(hadoop_file):
                            os.remove(hadoop_file)
                else:
                    auto_deploy_status['log'].append(f"源不可用: {source_url}")
                    
        except Exception as e:
            auto_deploy_status['log'].append(f"从 {source_url} 下载异常: {str(e)}")
            if os.path.exists(hadoop_file):
                os.remove(hadoop_file)
    
    auto_deploy_status['log'].append("所有下载源都失败，无法下载Hadoop")
    return None

def log_append(status_obj, msg, level="INFO"):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_obj['log'].append(f"[{ts}][{level}] {msg}")

def execute_ssh_command_with_log(ssh, command, log_prefix=None, status_obj=None, level="INFO", timeout=60):
    try:
        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        exit_code = stdout.channel.recv_exit_status()
        if status_obj is not None:
            if out.strip():
                log_append(status_obj, f"{log_prefix} {out.strip()}", level)
            if err.strip():
                log_append(status_obj, f"{log_prefix} [错误] {err.strip()}", "ERROR")
        return out, err, exit_code
    except Exception as e:
        if status_obj is not None:
            log_append(status_obj, f"{log_prefix} 命令异常: {e}", "ERROR")
        return "", str(e), -1

def execute_ssh_command_stream_log(ssh, command, log_prefix=None, status_obj=None, timeout=600):
    try:
        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True, timeout=timeout)
        out_lines, err_lines = [], []
        for line in iter(lambda: stdout.readline(2048), ""):
            if line:
                msg = f"{log_prefix} {line.rstrip()}" if log_prefix else line.rstrip()
                if status_obj is not None:
                    log_append(status_obj, msg, "INFO")
                out_lines.append(line.rstrip())
            else:
                break
        for line in iter(lambda: stderr.readline(2048), ""):
            if line:
                msg = f"{log_prefix} [错误] {line.rstrip()}" if log_prefix else f"[错误] {line.rstrip()}"
                if status_obj is not None:
                    log_append(status_obj, msg, "ERROR")
                err_lines.append(line.rstrip())
            else:
                break
        exit_code = stdout.channel.recv_exit_status()
        return '\n'.join(out_lines), '\n'.join(err_lines), exit_code
    except Exception as e:
        if status_obj is not None:
            log_append(status_obj, f"{log_prefix} 命令异常: {e}", "ERROR")
        return "", str(e), -1

def configure_hadoop_remote(ssh, hadoop_file_path, install_dir="/opt/hadoop", hadoop_version="3.3.6", master_ip="localhost", resourcemanager_ip="localhost", servers=None, replication=2, java_version='8', status_obj=None):
    auto_deploy_status['log'].append(f"[远程] 开始配置Hadoop...（安装路径：{install_dir}）")
    # 创建安装目录
    execute_ssh_command_with_log(ssh, f"mkdir -p {install_dir}", "[远程] 创建目录", auto_deploy_status)
    # 解压Hadoop
    cmd = f"tar -xzf {hadoop_file_path} -C {install_dir}"
    out, err, exit_code = execute_ssh_command_with_log(ssh, cmd, "[远程] 解压Hadoop", auto_deploy_status)
    if exit_code != 0:
        auto_deploy_status['log'].append(f"[远程] Hadoop解压失败: {err}")
        return False
    # 创建符号链接
    hadoop_home = f"{install_dir}/hadoop-{hadoop_version}"
    execute_ssh_command_with_log(ssh, f"ln -sf {hadoop_home} {install_dir}/current", "[远程] 创建符号链接", auto_deploy_status)
    # 动态查找Java路径
    if java_version == '8':
        java_home_cmd = "ls -d /usr/lib/jvm/java-1.8.0-openjdk* 2>/dev/null | head -1"
    elif java_version == '11':
        java_home_cmd = "ls -d /usr/lib/jvm/java-11-openjdk* 2>/dev/null | head -1"
    elif java_version == '17':
        java_home_cmd = "ls -d /usr/lib/jvm/java-17-openjdk* 2>/dev/null | head -1"
    else:
        java_home_cmd = "ls -d /usr/lib/jvm/java-1.8.0-openjdk* 2>/dev/null | head -1"
    out, err, exit_code = execute_ssh_command_with_log(ssh, java_home_cmd, "[远程] 检查Java安装路径", auto_deploy_status)
    java_home = out.strip() if out.strip() else f"/usr/lib/jvm/java-{java_version}-openjdk"
    # 写入环境变量
    env_content = f"""export JAVA_HOME={java_home}
export HADOOP_HOME={hadoop_home}
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
export HADOOP_OPTS=\"-Djava.library.path=$HADOOP_HOME/lib/native\"\n"""
    execute_ssh_command_with_log(ssh, f"echo '{env_content}' > ~/.hadoop_env", "[远程] 写入环境变量", auto_deploy_status)
    # 生成并写入关键配置文件
    hadoop_conf_dir = f"{hadoop_home}/etc/hadoop"
    core_site = generate_core_site(master_ip)
    hdfs_site = generate_hdfs_site(replication)
    yarn_site = generate_yarn_site(resourcemanager_ip)
    workers_txt = generate_workers(servers or [])
    write_remote_file(ssh, f"{hadoop_conf_dir}/core-site.xml", core_site)
    write_remote_file(ssh, f"{hadoop_conf_dir}/hdfs-site.xml", hdfs_site)
    write_remote_file(ssh, f"{hadoop_conf_dir}/yarn-site.xml", yarn_site)
    write_remote_file(ssh, f"{hadoop_conf_dir}/workers", workers_txt)
    auto_deploy_status['log'].append(f"[远程] 已写入关键配置文件到: {hadoop_conf_dir}")
    # 配置 JAVA_HOME 到 hadoop-env.sh 和 yarn-env.sh
    for env_file in [f'{hadoop_home}/etc/hadoop/hadoop-env.sh', f'{hadoop_home}/etc/hadoop/yarn-env.sh']:
        java_home_line = f'export JAVA_HOME={java_home}'
        cmd = f"grep -q '^export JAVA_HOME=' {env_file} && sed -i 's|^export JAVA_HOME=.*|{java_home_line}|' {env_file} || echo '{java_home_line}' >> {env_file}"
        execute_ssh_command_with_log(ssh, cmd, f"[远程] 配置JAVA_HOME到{os.path.basename(env_file)}", auto_deploy_status)
    # Java 17兼容性参数补丁（强制写入，不判断是否已存在）
    if java_version == '17':
        for env_file in [f'{hadoop_home}/etc/hadoop/hadoop-env.sh', f'{hadoop_home}/etc/hadoop/yarn-env.sh']:
            # 写入前确保有写权限
            cmd_chmod_before = f"chmod 666 {env_file}"
            execute_ssh_command_with_log(ssh, cmd_chmod_before, f"[远程] 修改{os.path.basename(env_file)}权限(写入前)", auto_deploy_status)
            for opt in [
                'export YARN_OPTS="--add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.nio=ALL-UNNAMED"',
                'export HADOOP_OPTS="--add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.nio=ALL-UNNAMED"'
            ]:
                # 先删除已存在的同名行，再追加
                cmd_rm = f"sed -i '/^{opt.split('=')[0]}/d' {env_file}"
                execute_ssh_command_with_log(ssh, cmd_rm, f"[远程] 移除旧Java 17兼容参数({opt.split('=')[0]})", auto_deploy_status)
                cmd_add = f"echo '{opt}' >> {env_file}"
                execute_ssh_command_with_log(ssh, cmd_add, f"[远程] 强制写入Java 17兼容参数到{os.path.basename(env_file)}", auto_deploy_status)
            # 写入后再次cat内容到日志
            cmd_cat = f"cat {env_file}"
            out_cat, err_cat, exit_code_cat = execute_ssh_command_with_log(ssh, cmd_cat, f"[远程] {os.path.basename(env_file)}内容(写入后)", auto_deploy_status)
            # 写入后恢复权限为644
            cmd_chmod_after = f"chmod 644 {env_file}"
            execute_ssh_command_with_log(ssh, cmd_chmod_after, f"[远程] 修改{os.path.basename(env_file)}权限(写入后)", auto_deploy_status)
    # 允许root用户启动Hadoop服务（仅测试环境建议）
    for env_file in [f'{hadoop_home}/etc/hadoop/hadoop-env.sh', f'{hadoop_home}/etc/hadoop/yarn-env.sh']:
        for var in [
            'export HDFS_NAMENODE_USER=root',
            'export HDFS_DATANODE_USER=root',
            'export HDFS_SECONDARYNAMENODE_USER=root',
            'export YARN_RESOURCEMANAGER_USER=root',
            'export YARN_NODEMANAGER_USER=root'
        ]:
            cmd = f"grep -q \"^{var}\" {env_file} || echo '{var}' >> {env_file}"
            execute_ssh_command_with_log(ssh, cmd, f"[远程] 配置{var}到{os.path.basename(env_file)}", auto_deploy_status)
    auto_deploy_status['log'].append("[远程] Hadoop配置完成")
    return True

def generate_core_site(master_ip):
    return f"""<?xml version=\"1.0\"?>\n<configuration>\n    <property>\n        <name>fs.defaultFS</name>\n        <value>hdfs://{master_ip}:9000</value>\n    </property>\n</configuration>\n"""

def generate_hdfs_site(replication=2):
    return f"""<?xml version=\"1.0\"?>\n<configuration>\n    <property>\n        <name>dfs.replication</name>\n        <value>{replication}</value>\n    </property>\n    <property>\n        <name>dfs.namenode.name.dir</name>\n        <value>file:/opt/hadoop/data/dfs/namenode</value>\n    </property>\n    <property>\n        <name>dfs.datanode.data.dir</name>\n        <value>file:/opt/hadoop/data/dfs/datanode</value>\n    </property>\n</configuration>\n"""

def generate_yarn_site(resourcemanager_ip):
    return f"""<?xml version=\"1.0\"?>\n<configuration>\n    <property>\n        <name>yarn.resourcemanager.hostname</name>\n        <value>{resourcemanager_ip}</value>\n    </property>\n    <property>\n        <name>yarn.nodemanager.aux-services</name>\n        <value>mapreduce_shuffle</value>\n    </property>\n</configuration>\n"""

def generate_workers(servers):
    return '\n'.join([s['hostname'] for s in servers]) + '\n'

def write_remote_file(ssh, remote_path, content):
    sftp = ssh.open_sftp()
    with sftp.file(remote_path, 'w') as f:
        f.write(content)
    sftp.close()

def setup_ssh_key_auth(ssh, servers, username):
    # 1. 检查并生成密钥对
    execute_ssh_command_with_log(ssh, "test -f ~/.ssh/id_rsa || ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa", "[远程] 检查/生成SSH密钥对", auto_deploy_status)
    # 2. 读取公钥
    stdin, stdout, stderr = ssh.exec_command("cat ~/.ssh/id_rsa.pub")
    pubkey = stdout.read().decode().strip()
    # 3. 分发公钥到所有节点
    for server in servers:
        host = server['hostname']
        user = server['username']
        pwd = server['password']
        port = server.get('port', '22')
        connection_type = server.get('connectionType', 'local')
        
        if host == ssh.get_transport().getpeername()[0] and user == username:
            # 本机直接追加
            execute_ssh_command_with_log(ssh, f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '{pubkey}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys", f"[远程] 配置本机免密", auto_deploy_status)
        else:
            try:
                # 只用内网IP分发免密
                ssh2 = create_ssh_connection(
                    hostname=host,
                    username=user,
                    password=pwd,
                    port=port,
                    connection_type='local',
                    public_ip=None
                )
                execute_ssh_command_with_log(ssh2, f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '{pubkey}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys", f"[远程] 配置{host}免密", auto_deploy_status)
                ssh2.close()
            except Exception as e:
                auto_deploy_status['log'].append(f"[免密] 配置{host}失败: {e}")
                continue

# 上传本地文件到远程服务器

def upload_file_to_remote(ssh, local_path, remote_path):
    try:
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        return True, ''
    except Exception as e:
        return False, str(e)

def auto_deploy_task(config):
    import time
    try:
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
        servers = config if isinstance(config, list) else [config]
        master_ip = servers[0]['hostname']
        resourcemanager_ip = master_ip  # 强制用内网IP
        replication = 2
        install_dir = "/opt/hadoop"
        hadoop_version = "3.3.6"
        hadoop_home = f"{install_dir}/hadoop-{hadoop_version}"
        auto_deploy_status['total_steps'] = 6
        # 步骤1：环境检测
        auto_deploy_status['step'] = 1
        auto_deploy_status['progress'] = 10
        auto_deploy_status['log'].append("[1/6] 开始环境检测...")
        auto_deploy_status['steps'][0]['status'] = 'doing'
        
        # 获取主节点的连接信息
        master_server = servers[0]
        master_ip = master_server['hostname']
        resourcemanager_ip = master_ip  # 强制用内网IP
        master_username = master_server['username']
        master_password = master_server['password']
        master_port = master_server.get('port', '22')
        master_connection_type = master_server.get('connectionType', 'local')
        master_public_ip = master_server.get('public_ip', '')
        
        auto_deploy_status['log'].append(f"[1/6] 尝试SSH连接主节点 {master_ip} 用户:{master_username} 连接方式:{master_connection_type}")
        
        try:
            # 使用新的SSH连接函数
            ssh = create_ssh_connection(
                hostname=master_ip,
                username=master_username,
                password=master_password,
                port=master_port,
                connection_type=master_connection_type,
                public_ip=master_public_ip
            )
            auto_deploy_status['log'].append("[1/6] SSH连接成功")
            
            # 自动配置免密
            try:
                setup_ssh_key_auth(ssh, servers, master_username)
                auto_deploy_status['log'].append('[免密] 已自动配置所有节点SSH免密登录')
            except Exception as e:
                auto_deploy_status['log'].append(f'[免密] 配置失败: {e}')
                auto_deploy_status['steps'][0]['status'] = 'error'
                auto_deploy_status['status'] = 'error'
                ssh.close()
                return
        except Exception as e:
            auto_deploy_status['log'].append(f"[1/6] SSH连接失败: {e}")
            auto_deploy_status['steps'][0]['status'] = 'error'
            auto_deploy_status['status'] = 'error'
            return
        auto_deploy_status['log'].append("[1/6] 正在关闭防火墙...")
        t0 = time.time()
        stdin, stdout, stderr = ssh.exec_command('systemctl stop firewalld && systemctl disable firewalld')
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        t1 = time.time()
        if exit_code == 0:
            auto_deploy_status['log'].append(f"[1/6] 防火墙关闭成功: {out.strip() or '无输出'} (耗时{t1-t0:.1f}s)")
        else:
            auto_deploy_status['log'].append(f"[1/6] 防火墙关闭失败: {err.strip() or out.strip() or '未知错误'} (耗时{t1-t0:.1f}s)")
        auto_deploy_status['steps'][0]['status'] = 'done'
        # 步骤2：安装Java环境
        auto_deploy_status['step'] = 2
        auto_deploy_status['progress'] = 25
        auto_deploy_status['log'].append("[2/6] 开始安装Java环境...")
        auto_deploy_status['steps'][1]['status'] = 'doing'
        auto_deploy_status['log'].append("[2/6] 检查Java是否已安装...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, 'java -version', None, auto_deploy_status)
        t1 = time.time()
        java_output = (out or '') + (err or '')
        auto_deploy_status['log'].append(f"[2/6] java -version 输出: {java_output.strip()} (耗时{t1-t0:.1f}s)")
        if 'version' in java_output:
            auto_deploy_status['log'].append("[2/6] 目标服务器已安装Java，跳过安装步骤")
        else:
            auto_deploy_status['log'].append("[2/6] 检查包管理器类型...")
            out, err, exit_code = execute_ssh_command_with_log(ssh, 'which yum', None, auto_deploy_status)
            auto_deploy_status['log'].append(f"[2/6] which yum 输出: {out.strip()} 错误: {err.strip()}")
            if out.strip():
                auto_deploy_status['log'].append("[2/6] 使用yum安装Java...")
                t0 = time.time()
                out3, err3, exit_code3 = execute_ssh_command_with_log(ssh, 'yum install -y java-1.8.0-openjdk*', None, auto_deploy_status)
                t1 = time.time()
                java_install_output = (out3 or '') + (err3 or '')
                auto_deploy_status['log'].append(f"[2/6] yum install 输出: {java_install_output.strip()} (耗时{t1-t0:.1f}s)")
                out_check, err_check, exit_code_check = execute_ssh_command_with_log(ssh, 'java -version', None, auto_deploy_status)
                java_check_output = (out_check or '') + (err_check or '')
                auto_deploy_status['log'].append(f"[2/6] java -version(安装后) 输出: {java_check_output.strip()}")
                if 'version' not in java_check_output:
                    auto_deploy_status['steps'][1]['status'] = 'error'
                    auto_deploy_status['status'] = 'error'
                    auto_deploy_status['log'].append(f"[2/6] Java安装失败: {java_install_output.strip()}")
                    ssh.close()
                    return
            else:
                out, err, exit_code = execute_ssh_command_with_log(ssh, 'which apt-get', None, auto_deploy_status)
                auto_deploy_status['log'].append(f"[2/6] which apt-get 输出: {out.strip()} 错误: {err.strip()}")
                if out.strip():
                    auto_deploy_status['log'].append("[2/6] 使用apt-get安装Java...")
                    t0 = time.time()
                    out3, err3, exit_code3 = execute_ssh_command_with_log(ssh, 'apt-get install -y openjdk-8-jdk', None, auto_deploy_status)
                    t1 = time.time()
                    java_install_output = (out3 or '') + (err3 or '')
                    auto_deploy_status['log'].append(f"[2/6] apt-get install 输出: {java_install_output.strip()} (耗时{t1-t0:.1f}s)")
                    out_check, err_check, exit_code_check = execute_ssh_command_with_log(ssh, 'java -version', None, auto_deploy_status)
                    java_check_output = (out_check or '') + (err_check or '')
                    auto_deploy_status['log'].append(f"[2/6] java -version(安装后) 输出: {java_check_output.strip()}")
                    if 'version' not in java_check_output:
                        auto_deploy_status['steps'][1]['status'] = 'error'
                        auto_deploy_status['status'] = 'error'
                        auto_deploy_status['log'].append(f"[2/6] Java安装失败: {java_install_output.strip()}")
                        ssh.close()
                        return
                else:
                    auto_deploy_status['steps'][1]['status'] = 'error'
                    auto_deploy_status['status'] = 'error'
                    auto_deploy_status['log'].append("[2/6] 未检测到支持的包管理器，请手动安装Java")
                    ssh.close()
                    return
        auto_deploy_status['steps'][1]['status'] = 'done'
        # 步骤3：下载Hadoop
        auto_deploy_status['step'] = 3
        auto_deploy_status['progress'] = 40
        auto_deploy_status['log'].append("[3/6] 开始下载并解压Hadoop...")
        auto_deploy_status['steps'][2]['status'] = 'doing'
        ali_url = f"https://mirrors.aliyun.com/apache/hadoop/common/hadoop-{hadoop_version}/hadoop-{hadoop_version}.tar.gz"
        remote_tar = f"/tmp/hadoop-{hadoop_version}.tar.gz"
        max_retry = 3
        for attempt in range(1, max_retry+1):
            auto_deploy_status['log'].append(f"[3/6] 第{attempt}次尝试下载Hadoop...")
            out, err, exit_code = execute_ssh_command_with_log(ssh, "which wget", None, auto_deploy_status)
            if exit_code == 0 and out.strip():
                download_cmd = f"wget -c -O {remote_tar} {ali_url}"
            else:
                out2, err2, exit_code2 = execute_ssh_command_with_log(ssh, "which curl", None, auto_deploy_status)
                if exit_code2 == 0 and out2.strip():
                    download_cmd = f"curl -C - -L -o {remote_tar} {ali_url}"
                else:
                    auto_deploy_status['log'].append("[3/6] 未检测到wget或curl，无法下载Hadoop")
                    auto_deploy_status['status'] = 'error'
                    auto_deploy_status['steps'][2]['status'] = 'error'
                    return
            t0 = time.time()
            out3, err3, _ = execute_ssh_command_with_log(ssh, download_cmd, None, auto_deploy_status)
            t1 = time.time()
            auto_deploy_status['log'].append(f"[3/6] 下载输出: {(out3 or '') + (err3 or '')} (耗时{t1-t0:.1f}s)")
            # 校验文件大小
            size_cmd = f"stat -c %s {remote_tar}"
            out_size, err_size, _ = execute_ssh_command_with_log(ssh, size_cmd, None, auto_deploy_status)
            try:
                file_size = int(out_size.strip())
            except Exception:
                file_size = 0
            if file_size < 100*1024*1024:
                auto_deploy_status['log'].append(f"[3/6] 下载文件过小({file_size}字节)，重试...")
                execute_ssh_command_with_log(ssh, f"rm -f {remote_tar}", None, auto_deploy_status)
                time.sleep(2)
                continue
            # tar -tzf校验包完整性
            check_cmd = f"tar -tzf {remote_tar} > /dev/null"
            _, err_check, exit_code_check = execute_ssh_command_with_log(ssh, check_cmd, None, auto_deploy_status)
            if exit_code_check == 0:
                auto_deploy_status['log'].append(f"[3/6] Hadoop包校验通过，开始解压...")
                break
            else:
                auto_deploy_status['log'].append(f"[3/6] Hadoop包校验失败: {err_check.strip()}，重试...")
                execute_ssh_command_with_log(ssh, f"rm -f {remote_tar}", None, auto_deploy_status)
                time.sleep(2)
        else:
            auto_deploy_status['log'].append('[3/6] 多次下载均失败，Hadoop包不完整，终止部署')
            auto_deploy_status['status'] = 'error'
            auto_deploy_status['steps'][2]['status'] = 'error'
            return
        auto_deploy_status['log'].append(f"[3/6] 开始远程解压Hadoop包...")
        if not configure_hadoop_remote(ssh, remote_tar, install_dir, hadoop_version, master_ip, resourcemanager_ip, servers, replication):
            auto_deploy_status['status'] = 'error'
            auto_deploy_status['steps'][2]['status'] = 'error'
            auto_deploy_status['log'].append('[3/6] Hadoop配置失败')
            return
        auto_deploy_status['steps'][2]['status'] = 'done'
        # 步骤4：配置Hadoop
        auto_deploy_status['step'] = 4
        auto_deploy_status['progress'] = 60
        auto_deploy_status['log'].append("[4/6] 正在自动配置Hadoop核心参数...")
        auto_deploy_status['steps'][3]['status'] = 'doing'
        auto_deploy_status['log'].append(f"[4/6] 格式化NameNode...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/bin/hdfs namenode -format -force', None, auto_deploy_status)
        t1 = time.time()
        auto_deploy_status['log'].append(f"[4/6] 格式化NameNode 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        auto_deploy_status['steps'][3]['status'] = 'done'
        # 步骤5：启动集群
        auto_deploy_status['step'] = 5
        auto_deploy_status['progress'] = 80
        auto_deploy_status['log'].append("[5/6] 正在启动Hadoop集群服务...")
        auto_deploy_status['steps'][4]['status'] = 'doing'
        # 新增：清理残留YARN进程和pid文件
        execute_ssh_command_with_log(ssh, "pkill -f ResourceManager; pkill -f NodeManager; rm -f /tmp/hadoop-root-*.pid", "[5/6] 清理YARN残留进程", auto_deploy_status)
        auto_deploy_status['log'].append(f"[5/6] 启动HDFS服务...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/sbin/start-dfs.sh', None, auto_deploy_status)
        t1 = time.time()
        auto_deploy_status['log'].append(f"[5/6] start-dfs.sh 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        # 新增：单独拉起ResourceManager并输出日志
        auto_deploy_status['log'].append(f"[5/6] 单独尝试启动ResourceManager...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/bin/yarn --daemon start resourcemanager', None, auto_deploy_status)
        t1 = time.time()
        auto_deploy_status['log'].append(f"[5/6] yarn --daemon start resourcemanager 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        # 输出ResourceManager日志最后30行
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'cat {hadoop_home}/logs/yarn-*-resourcemanager-*.log | tail -30', None, auto_deploy_status)
        auto_deploy_status['log'].append(f"[5/6] ResourceManager日志(最近30行):\n{out.strip()}\n{err.strip()}")
        # 继续原有流程
        auto_deploy_status['log'].append(f"[5/6] 启动YARN服务...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/sbin/start-yarn.sh', None, auto_deploy_status)
        t1 = time.time()
        auto_deploy_status['log'].append(f"[5/6] start-yarn.sh 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        # 再次输出ResourceManager日志最后30行
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'cat {hadoop_home}/logs/yarn-*-resourcemanager-*.log | tail -30', None, auto_deploy_status)
        auto_deploy_status['log'].append(f"[5/6] ResourceManager日志(最近30行):\n{out.strip()}\n{err.strip()}")
        auto_deploy_status['steps'][4]['status'] = 'done'
        # 步骤6：验证部署
        auto_deploy_status['step'] = 6
        auto_deploy_status['progress'] = 100
        auto_deploy_status['log'].append("[6/6] 正在验证集群运行状态...")
        auto_deploy_status['steps'][5]['status'] = 'doing'
        auto_deploy_status['log'].append(f"[6/6] 检查HDFS节点状态...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/bin/hdfs dfsadmin -report', None, auto_deploy_status)
        t1 = time.time()
        auto_deploy_status['log'].append(f"[6/6] hdfs dfsadmin -report 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        auto_deploy_status['log'].append(f"[6/6] 检查YARN节点状态...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/bin/yarn node -list', None, auto_deploy_status)
        t1 = time.time()
        auto_deploy_status['log'].append(f"[6/6] yarn node -list 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        auto_deploy_status['steps'][5]['status'] = 'done'
        auto_deploy_status['status'] = 'done'
        auto_deploy_status['log'].append('[完成] 部署完成')
        nn_url = f'http://{master_ip}:9870'
        rm_url = f'http://{master_ip}:8088'
        auto_deploy_status['cluster_links'] = {
            'NameNode': nn_url,
            'ResourceManager': rm_url
        }
        ssh.close()
        # 步骤4.5：自动写入/etc/hosts，确保主机名解析为内网IP
        hostname_cmd = 'hostname'
        out, err, exit_code = execute_ssh_command_with_log(ssh, hostname_cmd, '[4.5/6] 获取主机名', auto_deploy_status)
        real_hostname = out.strip() if out.strip() else 'localhost'
        hosts_line = f'{master_ip} {real_hostname}'
        add_hosts_cmd = f"grep -q '{hosts_line}' /etc/hosts || echo '{hosts_line}' >> /etc/hosts"
        execute_ssh_command_with_log(ssh, add_hosts_cmd, '[4.5/6] 写入/etc/hosts', auto_deploy_status)
    except Exception as e:
        auto_deploy_status['status'] = 'error'
        auto_deploy_status['log'].append(f'错误: {str(e)}')

def semi_auto_deploy_task(config):
    import time
    try:
        semi_auto_deploy_status['status'] = 'running'
        semi_auto_deploy_status['log'] = []
        semi_auto_deploy_status['steps'] = [
            {'name': '验证配置', 'status': 'pending'},
            {'name': '环境准备', 'status': 'pending'},
            {'name': '安装组件', 'status': 'pending'},
            {'name': '应用配置', 'status': 'pending'},
            {'name': '启动服务', 'status': 'pending'},
            {'name': '验证部署', 'status': 'pending'}
        ]
        # 修正：config为None时直接返回
        if not config or not isinstance(config, dict):
            log_append(semi_auto_deploy_status, '未获取到部署配置', "ERROR")
            semi_auto_deploy_status['status'] = 'error'
            return
        basic = config.get('basic', {}) if isinstance(config.get('basic', {}), dict) else {}
        namenode_host = basic.get('namenodeHost', 'localhost')
        master_user = 'root'
        master_pwd = ''
        master_port = '22'
        master_connection_type = 'local'
        servers = config.get('servers', []) if isinstance(config.get('servers', []), list) else []
        master_server = None
        for s in servers:
            if s.get('hostname') == namenode_host:
                master_user = s.get('username', 'root')
                master_pwd = s.get('password', '')
                master_port = s.get('port', '22')
                master_connection_type = s.get('connectionType', 'local')
                master_server = s
                break
        hadoop_version = basic.get('hadoopVersion', '3.3.6')
        java_version = basic.get('javaVersion', '8')
        install_dir = "/opt/hadoop"
        hadoop_home = f"{install_dir}/hadoop-{hadoop_version}"
        semi_auto_deploy_status['step'] = 1
        semi_auto_deploy_status['progress'] = 10
        semi_auto_deploy_status['steps'][0]['status'] = 'doing'
        log_append(semi_auto_deploy_status, f"[1/6] 尝试SSH连接主节点 {namenode_host} 用户:{master_user} 连接方式:{master_connection_type}")
        
        try:
            # 使用新的SSH连接函数
            master_public_ip = master_server.get('public_ip', '') if master_server else ''
            ssh = create_ssh_connection(
                hostname=namenode_host,
                username=master_user,
                password=master_pwd,
                port=int(master_port),
                connection_type=master_connection_type,
                public_ip=master_public_ip
            )
            log_append(semi_auto_deploy_status, "[1/6] SSH连接成功")
            try:
                setup_ssh_key_auth(ssh, config['servers'], master_user)
                log_append(semi_auto_deploy_status, '[免密] 已自动配置所有节点SSH免密登录')
            except Exception as e:
                log_append(semi_auto_deploy_status, f'[免密] 配置失败: {e}', "ERROR")
                semi_auto_deploy_status['steps'][0]['status'] = 'error'
                semi_auto_deploy_status['status'] = 'error'
                ssh.close()
                return
        except Exception as e:
            log_append(semi_auto_deploy_status, f"[1/6] SSH连接失败: {e}", "ERROR")
            semi_auto_deploy_status['steps'][0]['status'] = 'error'
            semi_auto_deploy_status['status'] = 'error'
            return
        log_append(semi_auto_deploy_status, "[1/6] 正在关闭防火墙...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, 'systemctl stop firewalld && systemctl disable firewalld', "[1/6] 防火墙", semi_auto_deploy_status)
        t1 = time.time()
        if exit_code == 0:
            log_append(semi_auto_deploy_status, f"[1/6] 防火墙关闭成功: {out.strip() or '无输出'} (耗时{t1-t0:.1f}s)")
        else:
            log_append(semi_auto_deploy_status, f"[1/6] 防火墙关闭失败: {err.strip() or out.strip() or '未知错误'} (耗时{t1-t0:.1f}s)", "ERROR")
        semi_auto_deploy_status['steps'][0]['status'] = 'done'
        # 步骤2：安装Java环境
        semi_auto_deploy_status['step'] = 2
        semi_auto_deploy_status['progress'] = 25
        semi_auto_deploy_status['steps'][1]['status'] = 'doing'
        log_append(semi_auto_deploy_status, "[2/6] 开始安装Java环境...")
        log_append(semi_auto_deploy_status, "[2/6] 检查Java是否已安装...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, 'java -version', "[2/6] java -version", semi_auto_deploy_status)
        t1 = time.time()
        java_output = (out or '') + (err or '')
        log_append(semi_auto_deploy_status, f"[2/6] java -version 输出: {java_output.strip()} (耗时{t1-t0:.1f}s)")
        expected_version = '1.8' if java_version == '8' else java_version
        if expected_version in java_output:
            log_append(semi_auto_deploy_status, f"[2/6] 目标服务器已安装Java {java_version}，跳过安装步骤")
        else:
            log_append(semi_auto_deploy_status, "[2/6] 检查包管理器类型...")
            out, err, exit_code = execute_ssh_command_with_log(ssh, 'which yum', "[2/6] which yum", semi_auto_deploy_status)
            if out.strip():
                log_append(semi_auto_deploy_status, f"[2/6] 使用yum安装Java {java_version}...")
                t0 = time.time()
                if java_version == '8':
                    install_cmd = 'yum install -y java-1.8.0-openjdk*'
                elif java_version == '11':
                    install_cmd = 'yum install -y java-11-openjdk*'
                elif java_version == '17':
                    install_cmd = 'yum install -y java-17-openjdk*'
                else:
                    install_cmd = 'yum install -y java-1.8.0-openjdk*'
                out3, err3, exit_code3 = execute_ssh_command_with_log(ssh, install_cmd, "[2/6] yum install", semi_auto_deploy_status)
                t1 = time.time()
                java_install_output = (out3 or '') + (err3 or '')
                log_append(semi_auto_deploy_status, f"[2/6] yum install 输出: {java_install_output.strip()} (耗时{t1-t0:.1f}s)")
                execute_ssh_command_with_log(ssh, 'update-alternatives --set java $(update-alternatives --list java | grep openjdk)', "[2/6] update-alternatives", semi_auto_deploy_status)
                out_check, err_check, exit_code_check = execute_ssh_command_with_log(ssh, 'java -version', "[2/6] java -version(安装后)", semi_auto_deploy_status)
                java_check_output = (out_check or '') + (err_check or '')
                log_append(semi_auto_deploy_status, f"[2/6] java -version(安装后) 输出: {java_check_output.strip()}")
                if expected_version not in java_check_output:
                    semi_auto_deploy_status['steps'][1]['status'] = 'error'
                    semi_auto_deploy_status['status'] = 'error'
                    log_append(semi_auto_deploy_status, f"[2/6] Java安装失败: {java_install_output.strip()}", "ERROR")
                    ssh.close()
                    return
            else:
                out, err, exit_code = execute_ssh_command_with_log(ssh, 'which apt-get', "[2/6] which apt-get", semi_auto_deploy_status)
                if out.strip():
                    log_append(semi_auto_deploy_status, f"[2/6] 使用apt-get安装Java {java_version}...")
                    t0 = time.time()
                    if java_version == '8':
                        install_cmd = 'apt-get install -y openjdk-8-jdk'
                    elif java_version == '11':
                        install_cmd = 'apt-get install -y openjdk-11-jdk'
                    elif java_version == '17':
                        install_cmd = 'apt-get install -y openjdk-17-jdk'
                    else:
                        install_cmd = 'apt-get install -y openjdk-8-jdk'
                    out3, err3, exit_code3 = execute_ssh_command_with_log(ssh, install_cmd, "[2/6] apt-get install", semi_auto_deploy_status)
                    t1 = time.time()
                    java_install_output = (out3 or '') + (err3 or '')
                    log_append(semi_auto_deploy_status, f"[2/6] apt-get install 输出: {java_install_output.strip()} (耗时{t1-t0:.1f}s)")
                    execute_ssh_command_with_log(ssh, 'update-alternatives --set java $(update-alternatives --list java | grep openjdk)', "[2/6] update-alternatives", semi_auto_deploy_status)
                    out_check, err_check, exit_code_check = execute_ssh_command_with_log(ssh, 'java -version', "[2/6] java -version(安装后)", semi_auto_deploy_status)
                    java_check_output = (out_check or '') + (err_check or '')
                    log_append(semi_auto_deploy_status, f"[2/6] java -version(安装后) 输出: {java_check_output.strip()}")
                    if expected_version not in java_check_output:
                        semi_auto_deploy_status['steps'][1]['status'] = 'error'
                        semi_auto_deploy_status['status'] = 'error'
                        log_append(semi_auto_deploy_status, f"[2/6] Java安装失败: {java_install_output.strip()}", "ERROR")
                        ssh.close()
                        return
                else:
                    semi_auto_deploy_status['steps'][1]['status'] = 'error'
                    semi_auto_deploy_status['status'] = 'error'
                    log_append(semi_auto_deploy_status, "[2/6] 未检测到支持的包管理器，请手动安装Java", "ERROR")
                    ssh.close()
                    return
        semi_auto_deploy_status['steps'][1]['status'] = 'done'
        # 步骤3：下载Hadoop（流式日志）
        semi_auto_deploy_status['step'] = 3
        semi_auto_deploy_status['progress'] = 40
        semi_auto_deploy_status['steps'][2]['status'] = 'doing'
        ali_url = f"https://mirrors.aliyun.com/apache/hadoop/common/hadoop-{hadoop_version}/hadoop-{hadoop_version}.tar.gz"
        log_append(semi_auto_deploy_status, f"[3/6] 检查wget: which wget")
        out, err, exit_code = execute_ssh_command_with_log(ssh, "which wget", "[3/6] which wget", semi_auto_deploy_status)
        if exit_code == 0 and out.strip():
            log_append(semi_auto_deploy_status, f"[3/6] which wget 输出: {out.strip()}")
        elif err.strip():
            log_append(semi_auto_deploy_status, f"[3/6] which wget 错误: {err.strip()}", "ERROR")
        else:
            log_append(semi_auto_deploy_status, f"[3/6] which wget 未检测到wget", "ERROR")
        if exit_code == 0 and out.strip():
            log_append(semi_auto_deploy_status, f"[3/6] 使用wget下载Hadoop...")
            t0 = time.time()
            out2, err2, exit_code2 = execute_ssh_command_stream_log(ssh, f"wget -O /tmp/hadoop-{hadoop_version}.tar.gz {ali_url}", "[3/6] wget", semi_auto_deploy_status)
            t1 = time.time()
            wget_output = (out2 or '') + (err2 or '')
            log_append(semi_auto_deploy_status, f"[3/6] wget 输出: {wget_output.strip()} (耗时{t1-t0:.1f}s)")
        else:
            out2, err2, exit_code2 = execute_ssh_command_with_log(ssh, "which curl", "[3/6] which curl", semi_auto_deploy_status)
            if exit_code2 == 0 and out2.strip():
                log_append(semi_auto_deploy_status, f"[3/6] which curl 输出: {out2.strip()}")
            elif err2.strip():
                log_append(semi_auto_deploy_status, f"[3/6] which curl 错误: {err2.strip()}", "ERROR")
            else:
                log_append(semi_auto_deploy_status, f"[3/6] which curl 未检测到curl", "ERROR")
            if exit_code2 == 0 and out2.strip():
                out_ver, err_ver, exit_code_ver = execute_ssh_command_with_log(ssh, "curl --version", "[3/6] curl --version", semi_auto_deploy_status)
                if exit_code_ver == 0 and out_ver.strip():
                    log_append(semi_auto_deploy_status, f"[3/6] curl --version 输出: {out_ver.strip()}")
                elif err_ver.strip():
                    log_append(semi_auto_deploy_status, f"[3/6] curl --version 错误: {err_ver.strip()}", "ERROR")
                else:
                    log_append(semi_auto_deploy_status, f"[3/6] curl --version 未检测到curl", "ERROR")
                log_append(semi_auto_deploy_status, f"[3/6] 使用curl下载Hadoop...")
                import threading
                import time as _time
                progress_log = f"/tmp/hadoop_curl_progress_{int(time.time())}.log"
                download_cmd = f"curl -L --progress-bar -o /tmp/hadoop-{hadoop_version}.tar.gz {ali_url} 2>{progress_log}"
                download_done = {'flag': False}
                def monitor_progress():
                    last_line = ""
                    while not download_done['flag']:
                        try:
                            sftp = ssh.open_sftp()
                            try:
                                with sftp.file(progress_log, 'r') as f:
                                    lines = f.readlines()
                                    if lines:
                                        last_line = lines[-1].strip()
                                        if last_line:
                                            log_append(semi_auto_deploy_status, f'[3/6] 下载进度: {last_line}')
                            finally:
                                sftp.close()
                        except Exception:
                            pass
                        _time.sleep(1)
                progress_thread = threading.Thread(target=monitor_progress)
                progress_thread.daemon = True
                progress_thread.start()
                t0 = time.time()
                out3, err3, exit_code3 = execute_ssh_command_stream_log(ssh, download_cmd, "[3/6] curl", semi_auto_deploy_status)
                t1 = time.time()
                download_done['flag'] = True
                progress_thread.join(timeout=2)
                try:
                    ssh.exec_command(f'rm -f {progress_log}')
                except Exception:
                    pass
                curl_output = (out3 or '') + (err3 or '')
                log_append(semi_auto_deploy_status, f"[3/6] curl 输出: {curl_output.strip()} (耗时{t1-t0:.1f}s)")
            else:
                log_append(semi_auto_deploy_status, f"[3/6] 未检测到wget或curl，无法下载Hadoop", "ERROR")
        log_append(semi_auto_deploy_status, f"[3/6] 开始远程解压Hadoop包...")
        # 配置Hadoop并解压（流式日志）
        if not configure_hadoop_remote(ssh, f"/tmp/hadoop-{hadoop_version}.tar.gz", install_dir, hadoop_version, namenode_host, namenode_host, config['servers'], 2, java_version=java_version, status_obj=semi_auto_deploy_status):
            semi_auto_deploy_status['status'] = 'error'
            semi_auto_deploy_status['steps'][2]['status'] = 'error'
            log_append(semi_auto_deploy_status, '[3/6] Hadoop配置失败', "ERROR")
            return
        semi_auto_deploy_status['steps'][2]['status'] = 'done'
        # 步骤4：配置Hadoop（格式化NameNode流式日志）
        semi_auto_deploy_status['step'] = 4
        semi_auto_deploy_status['progress'] = 60
        semi_auto_deploy_status['steps'][3]['status'] = 'doing'
        log_append(semi_auto_deploy_status, "[4/6] 正在自动配置Hadoop核心参数...")
        log_append(semi_auto_deploy_status, f"[4/6] 格式化NameNode...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_stream_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/bin/hdfs namenode -format -force', "[4/6] 格式化NameNode", semi_auto_deploy_status)
        t1 = time.time()
        log_append(semi_auto_deploy_status, f"[4/6] 格式化NameNode 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        semi_auto_deploy_status['steps'][3]['status'] = 'done'
        # 步骤5：启动集群
        semi_auto_deploy_status['step'] = 5
        semi_auto_deploy_status['progress'] = 80
        semi_auto_deploy_status['steps'][4]['status'] = 'doing'
        # 新增：清理残留YARN进程和pid文件
        execute_ssh_command_with_log(ssh, "pkill -f ResourceManager; pkill -f NodeManager; rm -f /tmp/hadoop-root-*.pid", "[5/6] 清理YARN残留进程", semi_auto_deploy_status)
        log_append(semi_auto_deploy_status, "[5/6] 正在启动Hadoop集群服务...")
        log_append(semi_auto_deploy_status, f"[5/6] 启动HDFS服务...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/sbin/start-dfs.sh', "[5/6] start-dfs.sh", semi_auto_deploy_status)
        t1 = time.time()
        log_append(semi_auto_deploy_status, f"[5/6] start-dfs.sh 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        log_append(semi_auto_deploy_status, f"[5/6] 启动YARN服务...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/sbin/start-yarn.sh', "[5/6] start-yarn.sh", semi_auto_deploy_status)
        t1 = time.time()
        log_append(semi_auto_deploy_status, f"[5/6] start-yarn.sh 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        semi_auto_deploy_status['steps'][4]['status'] = 'done'
        # 步骤6：验证部署
        semi_auto_deploy_status['step'] = 6
        semi_auto_deploy_status['progress'] = 100
        semi_auto_deploy_status['steps'][5]['status'] = 'doing'
        log_append(semi_auto_deploy_status, "[6/6] 正在验证集群运行状态...")
        log_append(semi_auto_deploy_status, f"[6/6] 检查HDFS节点状态...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/bin/hdfs dfsadmin -report', "[6/6] hdfs dfsadmin -report", semi_auto_deploy_status)
        t1 = time.time()
        log_append(semi_auto_deploy_status, f"[6/6] hdfs dfsadmin -report 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        log_append(semi_auto_deploy_status, f"[6/6] 检查YARN节点状态...")
        t0 = time.time()
        out, err, exit_code = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/bin/yarn node -list', "[6/6] yarn node -list", semi_auto_deploy_status)
        t1 = time.time()
        log_append(semi_auto_deploy_status, f"[6/6] yarn node -list 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        semi_auto_deploy_status['steps'][5]['status'] = 'done'
        semi_auto_deploy_status['status'] = 'done'
        log_append(semi_auto_deploy_status, '[完成] 部署完成')
        nn_url = f'http://{namenode_host}:9870'
        rm_url = f'http://{namenode_host}:8088'
        semi_auto_deploy_status['cluster_links'] = {
            'NameNode': nn_url,
            'ResourceManager': rm_url
        }
        ssh.close()
        # 步骤4.5：自动写入/etc/hosts，确保主机名解析为内网IP
        hostname_cmd = 'hostname'
        out, err, exit_code = execute_ssh_command_with_log(ssh, hostname_cmd, '[4.5/6] 获取主机名', semi_auto_deploy_status)
        real_hostname = out.strip() if out.strip() else 'localhost'
        hosts_line = f'{namenode_host} {real_hostname}'
        add_hosts_cmd = f"grep -q '{hosts_line}' /etc/hosts || echo '{hosts_line}' >> /etc/hosts"
        execute_ssh_command_with_log(ssh, add_hosts_cmd, '[4.5/6] 写入/etc/hosts', semi_auto_deploy_status)
    except Exception as e:
        semi_auto_deploy_status['status'] = 'error'
        step_idx = semi_auto_deploy_status.get('step', 1) - 1
        if 'steps' in semi_auto_deploy_status and 0 <= step_idx < len(semi_auto_deploy_status['steps']):
            semi_auto_deploy_status['steps'][step_idx]['status'] = 'error'
        log_append(semi_auto_deploy_status, f'错误: {str(e)}', "ERROR")

def create_ssh_connection(hostname, username, password, port=22, connection_type='local', public_ip=None):
    """
    创建SSH连接，支持内网和公网连接
    
    Args:
        hostname: 服务器内网地址
        username: 用户名
        password: 密码
        port: 端口号（默认22，公网连接时使用frp映射的端口）
        connection_type: 连接类型（'local' 或 'public'）
        public_ip: 公网IP地址（公网连接时使用）
    
    Returns:
        paramiko.SSHClient: SSH客户端对象
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # 根据连接类型选择连接地址
        if connection_type == 'public' and public_ip:
            # 公网连接使用公网IP和指定的端口
            connect_host = public_ip
            connect_port = int(port)
        else:
            # 内网连接使用内网IP和默认端口22
            connect_host = hostname
            connect_port = 22
        
        ssh.connect(connect_host, port=connect_port, username=username, password=password, timeout=30)
        return ssh
    except Exception as e:
        ssh.close()
        raise e

@app.route('/api/deploy/auto/start', methods=['POST'])
def api_deploy_auto_start():
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
    t.daemon = True  # 设置为守护线程
    t.start()
    return jsonify({'msg': '部署已启动'})

@app.route('/api/deploy/auto/status')
def api_deploy_auto_status():
    return jsonify(auto_deploy_status)

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/deploy/start")
def start():
    return render_template('start.html')

@app.route('/deploy/method')
def deploy_method():
    app.logger.info('访问部署方法页面')
    """部署方法页面"""
    return render_template('components/deploy-method.html')


@app.route('/deploy/auto')
def deploy_auto():
    """全自动部署页面"""
    app.logger.info('访问全自动部署页面')
    return render_template('components/deploy-auto.html')


@app.route('/deploy/semiAutoConfig')
def deploy_semi_auto():
    """半自动配置页面"""
    app.logger.info('访问半自动配置页面')
    return render_template('components/deploy-semi-auto.html')


@app.route('/deploy/semi-auto/progress')
def deploy_semi_auto_progress():
    """半自动部署进度页面"""
    app.logger.info('访问半自动部署进度页面')
    return render_template('components/deploy-semi-auto-progress.html')


@app.route('/deploy/manualConfig')
def deploy_manual():
    """手动配置页面"""
    app.logger.info('访问手动配置页面')
    return render_template('components/deploy-manual.html')


@app.route('/deploy/manual/progress')
def deploy_manual_progress():
    """手动部署进度页面"""
    app.logger.info('访问手动部署进度页面')
    return render_template('components/deploy-manual-progress.html')


@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy-policy.html')

@app.route('/terms-of-service') 
def terms_of_service():
    return render_template('terms-of-service.html')

@app.route('/documentation')
def documentation():
    """文档中心主页面"""
    try:
        return render_template('documentation.html')
    except TemplateNotFound:
        abort(404)
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/api/upload/hadoop', methods=['POST'])
def upload_hadoop_package():
    if 'file' not in request.files:
        return jsonify({'success': False, 'msg': '未检测到文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'msg': '未选择文件'}), 400
    if file and allowed_file(file.filename):
        # 直接流式转发到远程服务器
        hostname = request.form.get('hostname')
        username = request.form.get('username')
        password = request.form.get('password')
        port = request.form.get('port', '22')
        connection_type = request.form.get('connection_type', 'local')
        public_ip = request.form.get('public_ip', '')
        
        if not (hostname and username and password):
            return jsonify({'success': False, 'msg': '缺少目标服务器信息'}), 400
        try:
            # 使用新的SSH连接函数
            ssh = create_ssh_connection(
                hostname=hostname,
                username=username,
                password=password,
                port=int(port),
                connection_type=connection_type,
                public_ip=public_ip
            )
            sftp = ssh.open_sftp()
            # 保证文件名和用户上传一致
            remote_path = f"/tmp/{file.filename}"
            with sftp.file(remote_path, 'wb') as f_remote:
                while True:
                    chunk = file.stream.read(4096)
                    if not chunk:
                        break
                    f_remote.write(chunk)
            sftp.close()
            ssh.close()
            return jsonify({'success': True, 'msg': '上传成功', 'remote_path': remote_path})
        except Exception as e:
            return jsonify({'success': False, 'msg': f'上传失败: {e}'}), 500
    else:
        return jsonify({'success': False, 'msg': '文件格式不正确'}), 400

@app.route('/api/upload/java', methods=['POST'])
def upload_java_package():
    if 'file' not in request.files:
        return jsonify({'success': False, 'msg': '未检测到文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'msg': '未选择文件'}), 400
    allowed_extensions = {'.tar.gz', '.tgz', '.zip'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        return jsonify({'success': False, 'msg': '只支持.tar.gz、.tgz或.zip格式的文件'}), 400
    # 直接流式转发到远程服务器
    hostname = request.form.get('hostname')
    username = request.form.get('username')
    password = request.form.get('password')
    port = request.form.get('port', '22')
    connection_type = request.form.get('connection_type', 'local')
    public_ip = request.form.get('public_ip', '')
    
    if not (hostname and username and password):
        return jsonify({'success': False, 'msg': '缺少目标服务器信息'}), 400
    try:
        # 使用新的SSH连接函数
        ssh = create_ssh_connection(
            hostname=hostname,
            username=username,
            password=password,
            port=int(port),
            connection_type=connection_type,
            public_ip=public_ip
        )
        sftp = ssh.open_sftp()
        # 保证文件名和用户上传一致
        remote_path = f"/tmp/{file.filename}"
        with sftp.file(remote_path, 'wb') as f_remote:
            while True:
                chunk = file.stream.read(4096)
                if not chunk:
                    break
                f_remote.write(chunk)
        sftp.close()
        ssh.close()
        return jsonify({'success': True, 'msg': '上传成功', 'remote_path': remote_path})
    except Exception as e:
        return jsonify({'success': False, 'msg': f'上传失败: {e}'}), 500

@app.route('/api/scan_hosts', methods=['POST'])
def scan_hosts():
    import os
    # 修复环境变量，确保常用命令可用
    os.environ['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin:' + os.environ.get('PATH', '')
    data = request.get_json()
    subnet = data.get('subnet')
    if not subnet:
        return jsonify({'success': False, 'msg': '缺少网段参数'}), 400
    try:
        # 扫描主机，-n加速
        cmd = f"nmap -sn {subnet}"
        code, stdout, stderr = execute_local_command(cmd, timeout=30)
        if code != 0:
            return jsonify({'success': False, 'msg': 'nmap 执行失败', 'stderr': stderr}), 500
        # 解析nmap输出，只提取IP地址
        hosts = []
        for line in stdout.splitlines():
            if line.startswith('Nmap scan report for '):
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)$', line)
                if match:
                    hosts.append(match.group(1))
        return jsonify({'success': True, 'hosts': hosts})
    except Exception as e:
        import traceback
        return jsonify({'success': False, 'msg': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/api/deploy/semi-auto/start', methods=['POST'])
def api_deploy_semi_auto_start():
    config = request.json.get('config')
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except Exception:
            return jsonify({'msg': 'config参数格式错误'}), 400
    if config is None:
        return jsonify({'msg': '缺少config参数'}), 400
    if semi_auto_deploy_status['status'] == 'running':
        return jsonify({'msg': '已有半自动部署在进行中'}), 400
    # 重置状态
    semi_auto_deploy_status['status'] = 'idle'
    semi_auto_deploy_status['step'] = 0
    semi_auto_deploy_status['progress'] = 0
    semi_auto_deploy_status['log'] = []
    semi_auto_deploy_status['steps'] = []
    semi_auto_deploy_status['cluster_links'] = {}
    t = Thread(target=semi_auto_deploy_task, args=(config,))
    t.daemon = True
    t.start()
    return jsonify({'msg': '半自动部署已启动'})

@app.route('/api/deploy/semi-auto/status')
def api_deploy_semi_auto_status():
    return jsonify(semi_auto_deploy_status)

@app.route('/api/yum/configure', methods=['POST'])
def api_configure_yum():
    data = request.json or {}
    servers = data.get('servers')
    if not servers or not isinstance(servers, list):
        return jsonify({'success': False, 'msg': '缺少服务器信息'}), 400
    results = []
    for s in servers:
        if not isinstance(s, dict):
            results.append({'host': '未知', 'success': False, 'msg': '服务器信息格式错误'})
            continue
        hostname = s.get('hostname')
        username = s.get('username')
        password = s.get('password')
        port = s.get('port', '22')
        connection_type = s.get('connectionType', 'local')
        public_ip = s.get('public_ip', '')
        if not (hostname and username and password):
            results.append({'host': hostname or '未知', 'success': False, 'msg': '信息不完整'})
            continue
        try:
            ssh = create_ssh_connection(
                hostname=hostname,
                username=username,
                password=password,
                port=int(port),
                connection_type=connection_type,
                public_ip=public_ip
            )
            stdin, stdout, stderr = ssh.exec_command("cat /etc/os-release")
            os_info = stdout.read().decode()
            if "CentOS Linux 7" in os_info or "centos:7" in os_info or "VERSION_ID=\"7\"" in os_info:
                repo_url = "http://mirrors.aliyun.com/repo/Centos-7.repo"
                repo_name = "CentOS-7"
            elif "CentOS Linux 8" in os_info or "centos:8" in os_info or "VERSION_ID=\"8\"" in os_info:
                repo_url = "http://mirrors.aliyun.com/repo/Centos-8.repo"
                repo_name = "CentOS-8"
            elif "Rocky Linux" in os_info and "VERSION_ID=\"8\"" in os_info:
                repo_url = "http://mirrors.aliyun.com/repo/Rocky-8.repo"
                repo_name = "Rocky-8"
            else:
                repo_url = "http://mirrors.aliyun.com/repo/Centos-7.repo"
                repo_name = "CentOS-7(默认)"
            rm_cmd = "rm -f /etc/yum.repos.d/*.repo"
            stdin, stdout, stderr = ssh.exec_command(rm_cmd)
            rm_out, rm_err = stdout.read().decode(), stderr.read().decode()
            curl_cmd = f"curl -s -o /etc/yum.repos.d/CentOS-Base.repo {repo_url}"
            stdin, stdout, stderr = ssh.exec_command(curl_cmd)
            exit_status = stdout.channel.recv_exit_status()
            curl_out, curl_err = stdout.read().decode(), stderr.read().decode()
            ssh.close()
            if rm_err:
                results.append({'host': hostname, 'success': False, 'msg': f'操作失败: {rm_err}'})
            elif exit_status != 0:
                results.append({'host': hostname, 'success': False, 'msg': f'操作失败: {curl_err or curl_out or "未知错误"}'})
            else:
                results.append({'host': hostname, 'success': True, 'msg': f'yum源已重置为阿里云{repo_name}源'})
        except Exception as e:
            results.append({'host': hostname, 'success': False, 'msg': f'操作异常: {e}'})
    all_success = all(r['success'] for r in results)
    return jsonify({'success': all_success, 'results': results, 'msg': 'yum源配置已批量完成' if all_success else '部分服务器配置失败'})

@app.route('/api/log')
def get_log():
    # 返回全自动部署日志内容
    logs = auto_deploy_status['log'] if isinstance(auto_deploy_status, dict) and 'log' in auto_deploy_status else []
    log_content = '\n'.join(logs)
    return Response(log_content, mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=5000)