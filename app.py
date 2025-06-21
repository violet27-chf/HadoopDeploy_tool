from flask import Flask, render_template, request, flash, jsonify, send_from_directory
import paramiko
import os
import subprocess
import platform
from io import StringIO
import threading
import time
import json

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
    'log': []
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
    
    if system == "Windows":
        # Windows下检查Java是否已安装
        code, stdout, stderr = execute_local_command("java -version")
        if code == 0:
            auto_deploy_status['log'].append("Java已安装，跳过安装步骤")
            return True
        else:
            auto_deploy_status['log'].append("请手动安装Java 8或更高版本")
            return False
    else:
        # Linux下尝试安装OpenJDK
        auto_deploy_status['log'].append("尝试安装OpenJDK...")
        
        # 检测包管理器
        code, stdout, stderr = execute_local_command("which apt-get")
        if code == 0:
            # Ubuntu/Debian
            code, stdout, stderr = execute_local_command("sudo apt-get update && sudo apt-get install -y openjdk-8-jdk")
        else:
            code, stdout, stderr = execute_local_command("which yum")
            if code == 0:
                # CentOS/RHEL
                code, stdout, stderr = execute_local_command("sudo yum install -y java-1.8.0-openjdk java-1.8.0-openjdk-devel")
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

def configure_hadoop(hadoop_file):
    """配置Hadoop"""
    auto_deploy_status['log'].append("开始配置Hadoop...")
    
    # 解压Hadoop
    install_dir = "/opt/hadoop"
    if platform.system() == "Windows":
        install_dir = "C:\\hadoop"
    
    # 创建安装目录
    os.makedirs(install_dir, exist_ok=True)
    
    # 解压文件
    if platform.system() == "Windows":
        # Windows解压
        code, stdout, stderr = execute_local_command(f'tar -xzf "{hadoop_file}" -C "{install_dir}"')
    else:
        # Linux解压
        code, stdout, stderr = execute_local_command(f"sudo tar -xzf {hadoop_file} -C {install_dir}")
    
    if code != 0:
        auto_deploy_status['log'].append(f"Hadoop解压失败: {stderr}")
        return False
    
    # 创建符号链接
    hadoop_home = os.path.join(install_dir, f"hadoop-3.3.6")
    if platform.system() != "Windows":
        code, stdout, stderr = execute_local_command(f"sudo ln -sf {hadoop_home} {install_dir}/current")
    
    # 设置环境变量
    auto_deploy_status['log'].append("设置环境变量...")
    
    # 创建配置文件
    config_content = f"""export JAVA_HOME=/usr/lib/jvm/java-8-openjdk
export HADOOP_HOME={hadoop_home}
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
export HADOOP_OPTS="-Djava.library.path=$HADOOP_HOME/lib/native"
"""
    
    config_file = os.path.join(os.path.expanduser("~"), ".hadoop_env")
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    auto_deploy_status['log'].append("Hadoop配置完成")
    return True

def start_hadoop_cluster():
    """启动Hadoop集群"""
    auto_deploy_status['log'].append("启动Hadoop集群...")
    
    # 格式化NameNode
    auto_deploy_status['log'].append("格式化NameNode...")
    code, stdout, stderr = execute_local_command("hdfs namenode -format")
    if code != 0:
        auto_deploy_status['log'].append(f"NameNode格式化失败: {stderr}")
        return False
    
    # 启动HDFS
    auto_deploy_status['log'].append("启动HDFS...")
    code, stdout, stderr = execute_local_command("start-dfs.sh")
    if code != 0:
        auto_deploy_status['log'].append(f"HDFS启动失败: {stderr}")
        return False
    
    # 启动YARN
    auto_deploy_status['log'].append("启动YARN...")
    code, stdout, stderr = execute_local_command("start-yarn.sh")
    if code != 0:
        auto_deploy_status['log'].append(f"YARN启动失败: {stderr}")
        return False
    
    auto_deploy_status['log'].append("Hadoop集群启动成功")
    return True

def verify_deployment():
    """验证部署"""
    auto_deploy_status['log'].append("验证部署结果...")
    
    # 检查HDFS状态
    code, stdout, stderr = execute_local_command("hdfs dfsadmin -report")
    if code == 0:
        auto_deploy_status['log'].append("HDFS状态正常")
    else:
        auto_deploy_status['log'].append(f"HDFS状态异常: {stderr}")
        return False
    
    # 检查YARN状态
    code, stdout, stderr = execute_local_command("yarn node -list")
    if code == 0:
        auto_deploy_status['log'].append("YARN状态正常")
    else:
        auto_deploy_status['log'].append(f"YARN状态异常: {stderr}")
        return False
    
    # 测试HDFS写入
    test_file = "/test_hadoop_deployment.txt"
    code, stdout, stderr = execute_local_command(f"echo 'Hadoop部署测试' | hdfs dfs -put - {test_file}")
    if code == 0:
        auto_deploy_status['log'].append("HDFS写入测试成功")
        # 清理测试文件
        execute_local_command(f"hdfs dfs -rm {test_file}")
    else:
        auto_deploy_status['log'].append(f"HDFS写入测试失败: {stderr}")
        return False
    
    auto_deploy_status['log'].append("部署验证完成")
    return True

# 全自动部署任务线程
def auto_deploy_task(config):
    try:
        auto_deploy_status['status'] = 'running'
        auto_deploy_status['log'] = []
        
        # 检查是否有部署脚本
        if platform.system() == "Windows":
            script_path = os.path.join(os.getcwd(), 'scripts', 'hadoop_deploy.ps1')
            if os.path.exists(script_path):
                auto_deploy_status['log'].append("发现Windows部署脚本，使用PowerShell脚本部署")
                execute_powershell_deploy(script_path)
            else:
                auto_deploy_status['log'].append("未找到Windows部署脚本，使用Python部署")
                execute_python_deploy()
        else:
            script_path = os.path.join(os.getcwd(), 'scripts', 'hadoop_deploy.sh')
            if os.path.exists(script_path):
                auto_deploy_status['log'].append("发现Linux部署脚本，使用bash脚本部署")
                execute_script_deploy(script_path)
            else:
                auto_deploy_status['log'].append("未找到Linux部署脚本，使用Python部署")
                execute_python_deploy()
        
    except Exception as e:
        auto_deploy_status['status'] = 'error'
        auto_deploy_status['message'] = f'部署过程中发生错误: {str(e)}'
        auto_deploy_status['log'].append(f'错误: {str(e)}')

def execute_powershell_deploy(script_path):
    """执行PowerShell部署脚本"""
    auto_deploy_status['log'].append("开始执行PowerShell部署脚本...")
    
    # 执行PowerShell脚本
    command = f'powershell -ExecutionPolicy Bypass -File "{script_path}"'
    code, stdout, stderr = execute_local_command(command, timeout=300)
    
    if code == 0:
        auto_deploy_status['status'] = 'done'
        auto_deploy_status['progress'] = 100
        auto_deploy_status['message'] = '部署完成'
        auto_deploy_status['log'].append('PowerShell脚本部署成功！')
        auto_deploy_status['log'].append(stdout)
    else:
        auto_deploy_status['status'] = 'error'
        auto_deploy_status['message'] = 'PowerShell脚本部署失败'
        auto_deploy_status['log'].append(f'PowerShell脚本执行失败: {stderr}')

def execute_script_deploy(script_path):
    """执行bash部署脚本"""
    auto_deploy_status['log'].append("开始执行bash部署脚本...")
    
    # 设置脚本执行权限
    os.chmod(script_path, 0o755)
    
    # 执行脚本
    code, stdout, stderr = execute_local_command(f"sudo {script_path}", timeout=300)
    
    if code == 0:
        auto_deploy_status['status'] = 'done'
        auto_deploy_status['progress'] = 100
        auto_deploy_status['message'] = '部署完成'
        auto_deploy_status['log'].append('bash脚本部署成功！')
        auto_deploy_status['log'].append(stdout)
    else:
        auto_deploy_status['status'] = 'error'
        auto_deploy_status['message'] = 'bash脚本部署失败'
        auto_deploy_status['log'].append(f'bash脚本执行失败: {stderr}')

def execute_python_deploy():
    """使用Python执行部署步骤"""
    steps = [
        ('环境检测', check_system_environment),
        ('安装Java环境', install_java),
        ('下载Hadoop', download_hadoop),
        ('配置Hadoop', lambda: configure_hadoop(auto_deploy_status.get('hadoop_file'))),
        ('启动集群', start_hadoop_cluster),
        ('验证部署', verify_deployment)
    ]
    
    for i, (step_name, step_func) in enumerate(steps, 1):
        auto_deploy_status['step'] = i
        auto_deploy_status['progress'] = int(i / len(steps) * 100)
        auto_deploy_status['message'] = f'正在执行：{step_name}'
        auto_deploy_status['log'].append(f"开始执行步骤 {i}: {step_name}")
        
        # 执行实际步骤
        if step_name == '下载Hadoop':
            hadoop_file = step_func()
            if hadoop_file:
                auto_deploy_status['hadoop_file'] = hadoop_file
                auto_deploy_status['log'].append(f"步骤 {i} 完成: {step_name}")
            else:
                auto_deploy_status['status'] = 'error'
                auto_deploy_status['message'] = f'步骤 {i} 失败: {step_name}'
                auto_deploy_status['log'].append(f"步骤 {i} 失败: {step_name}")
                return
        else:
            if step_func():
                auto_deploy_status['log'].append(f"步骤 {i} 完成: {step_name}")
            else:
                auto_deploy_status['status'] = 'error'
                auto_deploy_status['message'] = f'步骤 {i} 失败: {step_name}'
                auto_deploy_status['log'].append(f"步骤 {i} 失败: {step_name}")
                return
        
        time.sleep(1)  # 短暂延迟，让前端有时间更新
    
    auto_deploy_status['status'] = 'done'
    auto_deploy_status['progress'] = 100
    auto_deploy_status['message'] = '部署完成'
    auto_deploy_status['log'].append('所有步骤执行完成，部署成功！')

@app.route('/api/deploy/auto/start', methods=['POST'])
def api_deploy_auto_start():
    config = request.json.get('config')
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
        save_path = os.path.join(UPLOAD_FOLDER, 'hadoop-uploaded.tar.gz')
        file.save(save_path)
        return jsonify({'success': True, 'msg': '上传成功', 'path': save_path})
    else:
        return jsonify({'success': False, 'msg': '文件格式不正确'}), 400

@app.route('/api/upload/java', methods=['POST'])
def upload_java_package():
    if 'file' not in request.files:
        return jsonify({'success': False, 'msg': '未检测到文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'msg': '未选择文件'}), 400
    
    # 检查文件格式
    allowed_extensions = {'.tar.gz', '.tgz', '.zip'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file.filename.endswith('.tar.gz'):
        file_ext = '.tar.gz'
    
    if file_ext not in allowed_extensions:
        return jsonify({'success': False, 'msg': '只支持.tar.gz、.tgz或.zip格式的文件'}), 400
    
    # 保存文件
    save_path = os.path.join(UPLOAD_FOLDER, f'java-uploaded{file_ext}')
    file.save(save_path)
    return jsonify({'success': True, 'msg': '上传成功', 'path': save_path})

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')