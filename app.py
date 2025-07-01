from flask import Flask, render_template, request, flash, jsonify, send_from_directory, abort, Response
from flask_cors import CORS
import paramiko
import subprocess
import re
import ast
from threading import Lock
import json
import threading
import time

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
def generate_core_site(master_ip):
    return f"""<?xml version=\"1.0\"?>\n<configuration>\n    <property>\n        <name>fs.defaultFS</name>\n        <value>hdfs://{master_ip}:9000</value>\n    </property>\n</configuration>\n"""

def generate_hdfs_site(replication=2):
    return f"""<?xml version=\"1.0\"?>\n<configuration>\n    <property>\n        <name>dfs.replication</name>\n        <value>{replication}</value>\n    </property>\n    <property>\n        <name>dfs.namenode.name.dir</name>\n        <value>file:/opt/hadoop/data/dfs/namenode</value>\n    </property>\n    <property>\n        <name>dfs.datanode.data.dir</name>\n        <value>file:/opt/hadoop/data/dfs/datanode</value>\n    </property>\n</configuration>\n"""

def generate_yarn_site(resourcemanager_ip):
    return f"""<?xml version=\"1.0\"?>\n<configuration>\n    <property>\n        <name>yarn.resourcemanager.hostname</name>\n        <value>{resourcemanager_ip}</value>\n    </property>\n    <property>\n        <name>yarn.nodemanager.aux-services</name>\n        <value>mapreduce_shuffle</value>\n    </property>\n</configuration>\n"""

def generate_workers(servers):
    workers = []
    for count in range(len(servers)):
        if count == 0:
            hostname = 'master'
            workers.append(hostname)
        elif count <= len(servers):
            hostname = f'slave{count}'
            workers.append(hostname)
    return workers

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
    servers = config if isinstance(config, list) else [config]
    auto_deploy_status['step'] = 1
    auto_deploy_status['progress'] = 10
    auto_deploy_status['log'].append("[1/6] 开始环境检测...")
    auto_deploy_status['steps'][0]['status'] = 'doing'

    set_hostname(servers)
    pubkey_list = []
    for server in servers:
        ip = server['hostname']
        username = server['username']
        password = server['password']
        port = int(server.get('port', 22))
        auto_deploy_status['log'].append(f"[1/6] 尝试SSH连接节点 {ip} 用户:{username} 密码:{password} 端口:{port}")
        ssh = ssh_client(ip, username, password, port)
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
    #添加公钥到authorized_keys
    for server in servers:
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        for pubkey in pubkey_list:
            ssh.exec_command(f"echo '{pubkey}' >> ~/.ssh/authorized_keys")
        ssh.close()

    auto_deploy_status['log'].append(f"[1/6] 免密配置成功")
    auto_deploy_status['steps'][0]['status'] = 'done'

    
    for server in servers:
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        auto_deploy_status['progress'] = 20
        auto_deploy_status['step'] = 2
        auto_deploy_status['steps'][1]['status'] = 'doing'
        stdin, stdout, stderr = ssh.exec_command("which java")
        java_path = stdout.read().decode().strip()
        if not java_path:
            stdin, stdout, stderr = ssh.exec_command("yum install -y java-1.8.0-openjdk-devel", timeout=120)
            auto_deploy_status['log'].append("[2/6] 等待java安装")
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                auto_deploy_status['log'].append("[2/6] 安装Java失败，请检查yum源和权限")
                auto_deploy_status['steps'][1]['status'] = 'error'
                return
        auto_deploy_status['log'].append(f"[2/6] 在{server['hostname']}安装Java完成")
        auto_deploy_status['steps'][1]['status'] = 'done'
        ssh.close()
        
    for server in servers:
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        auto_deploy_status['progress'] = 30
        auto_deploy_status['step'] = 3
        auto_deploy_status['steps'][2]['status'] = 'doing'
        auto_deploy_status['log'].append(f"[3/6] 在{server['hostname']}开始下载并解压Hadoop...")
        hadoop_tar_path = "/opt/hadoop.tar.gz"
        stdin, stdout, stderr = ssh.exec_command("yum install -y curl",timeout=60)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            auto_deploy_status['log'].append(f"[3/6] 安装curl失败，请检查yum源和权限")
            auto_deploy_status['steps'][2]['status'] = 'error'
            return
        stdin, stdout, stderr = ssh.exec_command("sha256sum /opt/hadoop.tar.gz")
        hadoop_tar_hash = stdout.read().decode().strip()
        if hadoop_tar_hash != "f5195059c0d4102adaa7fff17f7b2a85df906bcb6e19948716319f9978641a04  /opt/hadoop.tar.gz":
            auto_deploy_status['log'].append(f"[3/6] sha256sum 校验失败 开始下载Hadoop")
            stdin, stdout, stderr = ssh.exec_command(f"curl -o {hadoop_tar_path} https://mirrors.aliyun.com/apache/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz",timeout=70)
            exit_code = stdout.channel.recv_exit_status()
            if exit_code != 0:
                auto_deploy_status['log'].append(f"[3/6] 下载Hadoop失败，请检查网络连接")
                auto_deploy_status['steps'][2]['status'] = 'error'
            else:
                auto_deploy_status['log'].append(f"[3/6] 下载Hadoop完成")
        else:
            auto_deploy_status['log'].append(f"[3/6] hadoop已下载，sha256sum 校验成功")
        #确保有tar命令
        ssh.exec_command("yum install -y tar && source /etc/profile")
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p /opt/hadoop/ && tar -xzf {hadoop_tar_path} -C /opt/")
        auto_deploy_status['log'].append(f"[3/6] 解压Hadoop: {stdout.read().decode().strip()}")
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            auto_deploy_status['log'].append(f"[3/6] 解压Hadoop失败，请检查网络连接")
            auto_deploy_status['steps'][2]['status'] = 'error'
            continue
            
        ssh.exec_command(f"mv /opt/hadoop-3.3.6/* /opt/hadoop/ && rm -rf /opt/hadoop-3.3.6")
        auto_deploy_status['log'].append("[3/6] 解压Hadoop完成")
        auto_deploy_status['steps'][2]['status'] = 'done'
        ssh.close()
    for server in servers:
        ssh = ssh_client(server['hostname'], server['username'], server['password'], int(server.get('port', 22)))
        auto_deploy_status['progress'] = 40
        auto_deploy_status['step'] = 4
        auto_deploy_status['steps'][3]['status'] = 'doing'
        auto_deploy_status['log'].append("[4/6] 开始配置Hadoop核心参数...")

        auto_deploy_status['log'].append("[4/6] 开始配置core-site.xml")
        ssh.exec_command(f"echo '{generate_core_site(servers[0]['hostname'])}' > /opt/hadoop/etc/hadoop/core-site.xml")

        auto_deploy_status['log'].append("[4/6] 开始配置hdfs-site.xml")
        ssh.exec_command(f"echo '{generate_hdfs_site(len(servers))}' > /opt/hadoop/etc/hadoop/hdfs-site.xml")
        
        auto_deploy_status['log'].append("[4/6] 开始配置yarn-site.xml")
        ssh.exec_command(f"echo '{generate_yarn_site(servers[0]['hostname'])}' > /opt/hadoop/etc/hadoop/yarn-site.xml")

        auto_deploy_status['log'].append("[4/6] 开始配置workers")
        workers_content = ''.join([server + '\n' for server in generate_workers(servers)])
        ssh.exec_command(f"echo '{workers_content}' > /opt/hadoop/etc/hadoop/workers")

        auto_deploy_status['log'].append("[4/6] 配置hadoop-env.sh")
        ssh.exec_command(f"echo 'export JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk-1.8.0.312.b07-2.el8_5.x86_64' > /opt/hadoop/etc/hadoop/hadoop-env.sh")

        auto_deploy_status['log'].append("[4/6] 配置环境变量")
        env_content = f"""export JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk-1.8.0.312.b07-2.el8_5.x86_64
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
        auto_deploy_status['log'].append("[4/6] 配置环境变量完成")
        auto_deploy_status['steps'][3]['status'] = 'done'
        ssh.close()

    auto_deploy_status['progress'] = 60
    auto_deploy_status['step'] = 5
    auto_deploy_status['steps'][4]['status'] = 'doing'
    auto_deploy_status['log'].append("[5/6] 初始化Hadoop集群服务...")
    ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
    stdin,stdout,stderr =  ssh.exec_command("source ~/.hadoop_env && hadoop namenode -format",timeout=120)
    #等待namenode初始化完成
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        auto_deploy_status['log'].append("[5/6] 初始化Hadoop集群服务失败...")
    #启动Hadoop集群服务
    auto_deploy_status['log'].append("[5/6] 初始化namenode完成")
    ssh = ssh_client(servers[0]['hostname'], servers[0]['username'], servers[0]['password'], int(servers[0].get('port', 22)))
    auto_deploy_status['log'].append("[5/6] 启动Hadoop集群服务...")
    stdin,stdout,stderr = ssh.exec_command("source ~/.hadoop_env && start-all.sh")
    stdout.channel.recv_exit_status()
    auto_deploy_status['log'].append(f"[5/6] 启动Hadoop集群服务: {stdout.read().decode().strip()}")
    auto_deploy_status['log'].append("[5/6] 启动Hadoop集群服务完成")
    auto_deploy_status['steps'][4]['status'] = 'done'
    auto_deploy_status['progress'] = 80
    auto_deploy_status['step'] = 6
    auto_deploy_status['steps'][5]['status'] = 'doing'
    auto_deploy_status['log'].append("[6/6] 验证集群运行状态...")
    stdin,stdout,stderr = ssh.exec_command("source ~/.hadoop_env && hdfs dfs -ls /",timeout=120)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        auto_deploy_status['log'].append("[6/6] 验证集群运行状态失败...")
        auto_deploy_status['steps'][5]['status'] = 'error'
        return
    auto_deploy_status['log'].append("[6/6] 验证集群运行状态完成")
    auto_deploy_status['log'].append("[6/6] 集群运行状态: 成功")
    auto_deploy_status['progress'] = 100
    auto_deploy_status['status'] = 'done'
    auto_deploy_status['steps'][5]['status'] = 'done'
    nn_url = f'http://{servers[0]['hostname']}:9870'
    rm_url = f'http://{servers[0]['hostname']}:8088'
    auto_deploy_status['cluster_links'] = {
        'NameNode': nn_url,
        'ResourceManager': rm_url
    }
        
@app.route('/api/log', methods=['GET', 'POST'])
def get_log():
    logs = auto_deploy_status['log'] if isinstance(auto_deploy_status, dict) and 'log' in auto_deploy_status else []
    log_content = '\n'.join(logs)
    return Response(log_content, mimetype='text/plain')

@app.route('/api/deploy/auto/status', methods=['GET', 'POST'])
def api_deploy_auto_status():
    return jsonify(auto_deploy_status)


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=8000)