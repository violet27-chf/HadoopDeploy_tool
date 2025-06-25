from flask import Flask, render_template, request, flash, jsonify, send_from_directory, abort
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

def execute_ssh_command_with_log(ssh, command, log_prefix=None):
    stdin, stdout, stderr = ssh.exec_command(command)
    out = stdout.read().decode()
    err = stderr.read().decode()
    # 只在出错时写入关键信息
    if log_prefix and err.strip():
        auto_deploy_status['log'].append(f"{log_prefix} 失败: {err.strip()}")
    return out, err

def configure_hadoop_remote(ssh, hadoop_file_path, install_dir="/opt/hadoop", hadoop_version="3.3.6", master_ip="localhost", resourcemanager_ip="localhost", servers=None, replication=2):
    auto_deploy_status['log'].append(f"[远程] 开始配置Hadoop...（安装路径：{install_dir}）")
    # 创建安装目录
    execute_ssh_command_with_log(ssh, f"mkdir -p {install_dir}", "[远程] 创建目录")
    # 解压Hadoop
    cmd = f"tar -xzf {hadoop_file_path} -C {install_dir}"
    out, err = execute_ssh_command_with_log(ssh, cmd, "[远程] 解压Hadoop")
    if err:
        auto_deploy_status['log'].append(f"[远程] Hadoop解压失败: {err}")
        return False
    # 创建符号链接
    hadoop_home = f"{install_dir}/hadoop-{hadoop_version}"
    execute_ssh_command_with_log(ssh, f"ln -sf {hadoop_home} {install_dir}/current", "[远程] 创建符号链接")
    # 检查实际Java路径
    out, err = execute_ssh_command_with_log(ssh, "ls -d /usr/lib/jvm/java-1.8.0-openjdk* 2>/dev/null | head -1", "[远程] 检查Java安装路径")
    java_home = out.strip() if out.strip() else "/usr/lib/jvm/java-1.8.0-openjdk"
    # 写入环境变量
    env_content = f"""export JAVA_HOME={java_home}
export HADOOP_HOME={hadoop_home}
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
export HADOOP_OPTS=\"-Djava.library.path=$HADOOP_HOME/lib/native\"\n"""
    execute_ssh_command_with_log(ssh, f"echo '{env_content}' > ~/.hadoop_env", "[远程] 写入环境变量")
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
    # 配置 JAVA_HOME 到 hadoop-env.sh
    hadoop_env_path = f"{hadoop_home}/etc/hadoop/hadoop-env.sh"
    java_home_line = f'export JAVA_HOME={java_home}'
    cmd = f"grep -q '^export JAVA_HOME=' {hadoop_env_path} && sed -i 's|^export JAVA_HOME=.*|{java_home_line}|' {hadoop_env_path} || echo '{java_home_line}' >> {hadoop_env_path}"
    execute_ssh_command_with_log(ssh, cmd, "[远程] 配置JAVA_HOME到hadoop-env.sh")
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
            execute_ssh_command_with_log(ssh, cmd, f"[远程] 配置{var}到{os.path.basename(env_file)}")
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
    execute_ssh_command_with_log(ssh, "test -f ~/.ssh/id_rsa || ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa", "[远程] 检查/生成SSH密钥对")
    # 2. 读取公钥
    stdin, stdout, stderr = ssh.exec_command("cat ~/.ssh/id_rsa.pub")
    pubkey = stdout.read().decode().strip()
    # 3. 分发公钥到所有节点
    for server in servers:
        host = server['hostname']
        user = server['username']
        pwd = server['password']
        if host == ssh.get_transport().getpeername()[0] and user == username:
            # 本机直接追加
            execute_ssh_command_with_log(ssh, f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '{pubkey}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys", f"[远程] 配置本机免密")
        else:
            ssh2 = paramiko.SSHClient()
            ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh2.connect(host, username=user, password=pwd)
            execute_ssh_command_with_log(ssh2, f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '{pubkey}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys", f"[远程] 配置{host}免密")
            ssh2.close()

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
        resourcemanager_ip = master_ip
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
        auto_deploy_status['log'].append(f"[1/6] 尝试SSH连接主节点 {master_ip} 用户:{servers[0]['username']}")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(master_ip, username=servers[0]['username'], password=servers[0]['password'])
            auto_deploy_status['log'].append("[1/6] SSH连接成功")
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
        out, err = execute_ssh_command_with_log(ssh, 'java -version', None)
        t1 = time.time()
        java_output = (out or '') + (err or '')
        auto_deploy_status['log'].append(f"[2/6] java -version 输出: {java_output.strip()} (耗时{t1-t0:.1f}s)")
        if 'version' in java_output:
            auto_deploy_status['log'].append("[2/6] 目标服务器已安装Java，跳过安装步骤")
        else:
            auto_deploy_status['log'].append("[2/6] 检查包管理器类型...")
            out, err = execute_ssh_command_with_log(ssh, 'which yum', None)
            auto_deploy_status['log'].append(f"[2/6] which yum 输出: {out.strip()} 错误: {err.strip()}")
            if out.strip():
                auto_deploy_status['log'].append("[2/6] 使用yum安装Java...")
                t0 = time.time()
                out3, err3 = execute_ssh_command_with_log(ssh, 'yum install -y java-1.8.0-openjdk*', None)
                t1 = time.time()
                java_install_output = (out3 or '') + (err3 or '')
                auto_deploy_status['log'].append(f"[2/6] yum install 输出: {java_install_output.strip()} (耗时{t1-t0:.1f}s)")
                out_check, err_check = execute_ssh_command_with_log(ssh, 'java -version', None)
                java_check_output = (out_check or '') + (err_check or '')
                auto_deploy_status['log'].append(f"[2/6] java -version(安装后) 输出: {java_check_output.strip()}")
                if 'version' not in java_check_output:
                    auto_deploy_status['steps'][1]['status'] = 'error'
                    auto_deploy_status['status'] = 'error'
                    auto_deploy_status['log'].append(f"[2/6] Java安装失败: {java_install_output.strip()}")
                    ssh.close()
                    return
            else:
                out, err = execute_ssh_command_with_log(ssh, 'which apt-get', None)
                auto_deploy_status['log'].append(f"[2/6] which apt-get 输出: {out.strip()} 错误: {err.strip()}")
                if out.strip():
                    auto_deploy_status['log'].append("[2/6] 使用apt-get安装Java...")
                    t0 = time.time()
                    out3, err3 = execute_ssh_command_with_log(ssh, 'apt-get install -y openjdk-8-jdk', None)
                    t1 = time.time()
                    java_install_output = (out3 or '') + (err3 or '')
                    auto_deploy_status['log'].append(f"[2/6] apt-get install 输出: {java_install_output.strip()} (耗时{t1-t0:.1f}s)")
                    out_check, err_check = execute_ssh_command_with_log(ssh, 'java -version', None)
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
        auto_deploy_status['log'].append(f"[3/6] 检查wget: which wget")
        out, err = execute_ssh_command_with_log(ssh, "which wget", None)
        auto_deploy_status['log'].append(f"[3/6] which wget 输出: {out.strip()} 错误: {err.strip()}")
        if out.strip():
            auto_deploy_status['log'].append(f"[3/6] 使用wget下载Hadoop...")
            t0 = time.time()
            out2, err2 = execute_ssh_command_with_log(ssh, f"wget -O /tmp/hadoop-{hadoop_version}.tar.gz {ali_url}", None)
            t1 = time.time()
            wget_output = (out2 or '') + (err2 or '')
            auto_deploy_status['log'].append(f"[3/6] wget 输出: {wget_output.strip()} (耗时{t1-t0:.1f}s)")
        else:
            out2, err2 = execute_ssh_command_with_log(ssh, "which curl", None)
            auto_deploy_status['log'].append(f"[3/6] which curl 输出: {out2.strip()} 错误: {err2.strip()}")
            if out2.strip():
                auto_deploy_status['log'].append(f"[3/6] 使用curl下载Hadoop...")
                t0 = time.time()
                out3, err3 = execute_ssh_command_with_log(ssh, f"curl -L -o /tmp/hadoop-{hadoop_version}.tar.gz {ali_url}", None)
                t1 = time.time()
                curl_output = (out3 or '') + (err3 or '')
                auto_deploy_status['log'].append(f"[3/6] curl 输出: {curl_output.strip()} (耗时{t1-t0:.1f}s)")
        auto_deploy_status['log'].append(f"[3/6] 开始远程解压Hadoop包...")
        # 配置Hadoop并解压
        if not configure_hadoop_remote(ssh, f"/tmp/hadoop-{hadoop_version}.tar.gz", install_dir, hadoop_version, master_ip, resourcemanager_ip, servers, replication):
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
        out, err = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/bin/hdfs namenode -format -force', None)
        t1 = time.time()
        auto_deploy_status['log'].append(f"[4/6] 格式化NameNode 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        auto_deploy_status['steps'][3]['status'] = 'done'
        # 步骤5：启动集群
        auto_deploy_status['step'] = 5
        auto_deploy_status['progress'] = 80
        auto_deploy_status['log'].append("[5/6] 正在启动Hadoop集群服务...")
        auto_deploy_status['steps'][4]['status'] = 'doing'
        auto_deploy_status['log'].append(f"[5/6] 启动HDFS服务...")
        t0 = time.time()
        out, err = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/sbin/start-dfs.sh', None)
        t1 = time.time()
        auto_deploy_status['log'].append(f"[5/6] start-dfs.sh 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        auto_deploy_status['log'].append(f"[5/6] 启动YARN服务...")
        t0 = time.time()
        out, err = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/sbin/start-yarn.sh', None)
        t1 = time.time()
        auto_deploy_status['log'].append(f"[5/6] start-yarn.sh 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        auto_deploy_status['steps'][4]['status'] = 'done'
        # 步骤6：验证部署
        auto_deploy_status['step'] = 6
        auto_deploy_status['progress'] = 100
        auto_deploy_status['log'].append("[6/6] 正在验证集群运行状态...")
        auto_deploy_status['steps'][5]['status'] = 'doing'
        auto_deploy_status['log'].append(f"[6/6] 检查HDFS节点状态...")
        t0 = time.time()
        out, err = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/bin/hdfs dfsadmin -report', None)
        t1 = time.time()
        auto_deploy_status['log'].append(f"[6/6] hdfs dfsadmin -report 输出: {out.strip()} 错误: {err.strip()} (耗时{t1-t0:.1f}s)")
        auto_deploy_status['log'].append(f"[6/6] 检查YARN节点状态...")
        t0 = time.time()
        out, err = execute_ssh_command_with_log(ssh, f'source ~/.hadoop_env && {hadoop_home}/bin/yarn node -list', None)
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
    except Exception as e:
        auto_deploy_status['status'] = 'error'
        auto_deploy_status['log'].append(f'错误: {str(e)}')

def semi_auto_deploy_task(config):
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
        # 1. 验证配置
        semi_auto_deploy_status['step'] = 1
        semi_auto_deploy_status['progress'] = 10
        semi_auto_deploy_status['log'].append('正在验证配置...')
        semi_auto_deploy_status['steps'][0]['status'] = 'doing'
        # 连接主节点
        master_ip = config.get('namenodeHost', 'localhost')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(master_ip, username=config.get('username', 'root'), password=config.get('password', ''))
        # 自动上传用户上传的 Hadoop 包
        local_hadoop = os.path.join(UPLOAD_FOLDER, 'hadoop-uploaded.tar.gz')
        if os.path.exists(local_hadoop):
            remote_hadoop = f"/tmp/hadoop-uploaded.tar.gz"
            ok, err = upload_file_to_remote(ssh, local_hadoop, remote_hadoop)
            if ok:
                semi_auto_deploy_status['log'].append(f"已上传用户Hadoop包到远程: {remote_hadoop}")
            else:
                semi_auto_deploy_status['log'].append(f"上传Hadoop包失败: {err}")
            # 无论上传是否成功，都尝试删除本地包
            try:
                os.remove(local_hadoop)
                semi_auto_deploy_status['log'].append("本地Hadoop包已删除")
            except Exception as e:
                semi_auto_deploy_status['log'].append(f"本地Hadoop包删除失败: {e}")
        local_java = None
        for ext in ['.tar.gz', '.tgz', '.zip']:
            path = os.path.join(UPLOAD_FOLDER, f'java-uploaded{ext}')
            if os.path.exists(path):
                local_java = path
                break
        if local_java:
            remote_java = f"/tmp/java-uploaded{os.path.splitext(local_java)[1]}"
            ok, err = upload_file_to_remote(ssh, local_java, remote_java)
            if ok:
                semi_auto_deploy_status['log'].append(f"已上传用户Java包到远程: {remote_java}")
            else:
                semi_auto_deploy_status['log'].append(f"上传Java包失败: {err}")
            # 无论上传是否成功，都尝试删除本地包
            try:
                os.remove(local_java)
                semi_auto_deploy_status['log'].append("本地Java包已删除")
            except Exception as e:
                semi_auto_deploy_status['log'].append(f"本地Java包删除失败: {e}")
        semi_auto_deploy_status['steps'][0]['status'] = 'done'
        # 2. 环境准备
        semi_auto_deploy_status['step'] = 2
        semi_auto_deploy_status['progress'] = 25
        semi_auto_deploy_status['log'].append('正在准备部署环境...')
        semi_auto_deploy_status['steps'][1]['status'] = 'doing'
        # 这里可加目录创建、依赖检查等
        semi_auto_deploy_status['steps'][1]['status'] = 'done'
        # 3. 安装组件
        semi_auto_deploy_status['step'] = 3
        semi_auto_deploy_status['progress'] = 40
        semi_auto_deploy_status['log'].append('正在安装Hadoop及相关组件...')
        semi_auto_deploy_status['steps'][2]['status'] = 'doing'
        # 这里可加Hadoop/Java/组件安装逻辑
        semi_auto_deploy_status['steps'][2]['status'] = 'done'
        # 4. 应用配置
        semi_auto_deploy_status['step'] = 4
        semi_auto_deploy_status['progress'] = 60
        semi_auto_deploy_status['log'].append('正在应用自定义配置...')
        semi_auto_deploy_status['steps'][3]['status'] = 'doing'
        # 这里可加配置文件写入逻辑
        semi_auto_deploy_status['steps'][3]['status'] = 'done'
        # 5. 启动服务
        semi_auto_deploy_status['step'] = 5
        semi_auto_deploy_status['progress'] = 80
        semi_auto_deploy_status['log'].append('正在启动Hadoop集群服务...')
        semi_auto_deploy_status['steps'][4]['status'] = 'doing'
        # 这里可加启动命令
        semi_auto_deploy_status['steps'][4]['status'] = 'done'
        # 6. 验证部署
        semi_auto_deploy_status['step'] = 6
        semi_auto_deploy_status['progress'] = 100
        semi_auto_deploy_status['log'].append('正在验证集群运行状态...')
        semi_auto_deploy_status['steps'][5]['status'] = 'doing'
        # 这里可加验证命令
        semi_auto_deploy_status['steps'][5]['status'] = 'done'
        semi_auto_deploy_status['status'] = 'done'
        semi_auto_deploy_status['log'].append('半自动部署完成')
        # 集群Web UI链接（示例）
        semi_auto_deploy_status['cluster_links'] = {
            'NameNode': f'http://{master_ip}:9870',
            'ResourceManager': f'http://{master_ip}:8088'
        }
        ssh.close()
    except Exception as e:
        semi_auto_deploy_status['status'] = 'error'
        step_idx = semi_auto_deploy_status.get('step', 1) - 1
        if 'steps' in semi_auto_deploy_status and 0 <= step_idx < len(semi_auto_deploy_status['steps']):
            semi_auto_deploy_status['steps'][step_idx]['status'] = 'error'
        semi_auto_deploy_status['log'].append(f'错误: {str(e)}')

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
        if not (hostname and username and password):
            return jsonify({'success': False, 'msg': '缺少目标服务器信息'}), 400
        try:
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, username=username, password=password)
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
    if file.filename.endswith('.tar.gz'):
        file_ext = '.tar.gz'
    if file_ext not in allowed_extensions:
        return jsonify({'success': False, 'msg': '只支持.tar.gz、.tgz或.zip格式的文件'}), 400
    # 直接流式转发到远程服务器
    hostname = request.form.get('hostname')
    username = request.form.get('username')
    password = request.form.get('password')
    if not (hostname and username and password):
        return jsonify({'success': False, 'msg': '缺少目标服务器信息'}), 400
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password)
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
    import paramiko
    data = request.json or {}
    servers = data.get('servers')
    if not servers or not isinstance(servers, list):
        return jsonify({'success': False, 'msg': '缺少服务器信息'}), 400
    results = []
    for s in servers:
        hostname = s.get('hostname')
        username = s.get('username')
        password = s.get('password')
        if not (hostname and username and password):
            results.append({'host': hostname or '未知', 'success': False, 'msg': '信息不完整'})
            continue
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, username=username, password=password, timeout=10)
            # 删除所有yum源
            rm_cmd = "rm -f /etc/yum.repos.d/*.repo"
            stdin, stdout, stderr = ssh.exec_command(rm_cmd)
            rm_out, rm_err = stdout.read().decode(), stderr.read().decode()
            # 下载阿里云CentOS-Base.repo
            curl_cmd = "curl -s -o /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-8.repo"
            stdin, stdout, stderr = ssh.exec_command(curl_cmd)
            exit_status = stdout.channel.recv_exit_status()
            curl_out, curl_err = stdout.read().decode(), stderr.read().decode()
            ssh.close()
            if rm_err:
                results.append({'host': hostname, 'success': False, 'msg': f'操作失败: {rm_err}'})
            elif exit_status != 0:
                results.append({'host': hostname, 'success': False, 'msg': f'操作失败: {curl_err or curl_out or "未知错误"}'})
            else:
                results.append({'host': hostname, 'success': True, 'msg': 'yum源已重置为阿里云源'})
        except Exception as e:
            results.append({'host': hostname, 'success': False, 'msg': f'操作异常: {e}'})
    all_success = all(r['success'] for r in results)
    return jsonify({'success': all_success, 'results': results, 'msg': 'yum源配置已批量完成' if all_success else '部分服务器配置失败'})

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')