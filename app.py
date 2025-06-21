from flask import Flask, render_template, request, flash
import paramiko
import os
from io import StringIO

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def execute_ssh_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.read().decode(), stderr.read().decode()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/deploy', methods=['POST'])
def deploy():
    results = []
    hostnames = request.form.getlist('hostname[]')
    usernames = request.form.getlist('username[]')
    passwords = request.form.getlist('password[]')
    
    for i, (hostname, username, password) in enumerate(zip(hostnames, usernames, passwords), 1):
        try:
            # 建立SSH连接
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, username=username, password=password)
            
            # 上传部署脚本
            sftp = ssh.open_sftp()
            script_path = os.path.join('scripts', 'hadoop_deploy.sh')
            remote_path = f'/tmp/hadoop_deploy_{i}.sh'
            sftp.put(script_path, remote_path)
            sftp.close()
            
            # 设置执行权限并运行脚本
            command = f"chmod +x {remote_path} && {remote_path}"
            stdout, stderr = execute_ssh_command(ssh, command)
            
            ssh.close()
            
            # 记录结果
            result = {
                'server': f"服务器 #{i} ({hostname})",
                'status': '成功',
                'output': stdout,
                'error': stderr
            }
            results.append(result)
            
        except Exception as e:
            results.append({
                'server': f"服务器 #{i} ({hostname})",
                'status': '失败',
                'error': str(e)
            })
    
    # 生成结果报告
    report = ["部署结果汇总:"]
    for result in results:
        report.append(f"\n{result['server']} - {result['status']}")
        if result.get('output'):
            report.append(f"\n输出:\n{result['output']}")
        if result.get('error'):
            report.append(f"\n错误:\n{result['error']}")
    
    return "<pre>" + "\n".join(report) + "</pre>"

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

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0')