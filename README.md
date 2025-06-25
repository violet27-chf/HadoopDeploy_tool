# HadoopDeploy_tool

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Flask Version](https://img.shields.io/badge/flask-2.3+-blue.svg)](https://flask.palletsprojects.com)

> 一站式 Hadoop 集群自动部署与管理平台，支持全自动、半自动、手动三种模式，Web 可视化、SSH 免密、进度与日志实时同步。

## ✨ 主要特性

- 🚀 **全自动部署**：一键完成 Hadoop 集群环境搭建与配置
- 🔒 **SSH 免密互信**：自动分发密钥，节点间无密码通信
- 🌐 **Web 可视化**：全流程进度、日志、集群 Web UI 直达
- 🛠️ **多模式支持**：全自动、半自动、手动部署灵活切换
- 📦 **自定义包上传**：支持 Hadoop/Java 安装包自定义上传
- 📊 **实时监控**：部署步骤与日志同步，异常高亮提示
- 🧩 **模块化设计**：易于扩展和二次开发

## 📋 目录

- [系统要求](#系统要求)
- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [使用指南](#使用指南)
- [配置说明](#配置说明)
- [开发指南](#开发指南)
- [故障排除](#故障排除)
- [贡献指南](#贡献指南)

## 🖥️ 系统要求

### 最低要求
- **操作系统**：Windows 10/11 或 Linux (Ubuntu 18.04+, CentOS 7+)
- **Python版本**：Python 3.8 或更高版本
- **内存**：至少 4GB RAM
- **磁盘空间**：至少 10GB 可用空间
- **网络**：稳定的互联网连接

### 推荐配置
- **操作系统**：Ubuntu 20.04 LTS 或 Windows 11
- **Python版本**：Python 3.9+
- **内存**：8GB RAM 或更多
- **磁盘空间**：50GB 可用空间
- **网络**：高速互联网连接

## 📦 安装指南

### 方法一：快速安装（推荐）

#### Windows 系统
```bash
# 双击运行安装脚本
setup.bat

# 或者命令行运行
.\setup.bat
```

#### Linux/macOS 系统
```bash
# 给脚本添加执行权限
chmod +x setup.sh

# 运行安装脚本
./setup.sh
```

### 方法二：手动安装

#### 1. 克隆项目

```bash
# 克隆项目到本地
git clone https://github.com/violet27-chf/HadoopDeploy_tool.git
cd HadoopDeploy_tool
```

#### 2. 创建虚拟环境

#### Windows 系统
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 验证虚拟环境
python --version
pip --version
```

#### Linux/macOS 系统
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 验证虚拟环境
python --version
pip --version
```

#### 3. 安装依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 验证安装
python -c "import flask, paramiko; print('依赖安装成功！')"
```


## 🚀 快速开始

### 方法一：使用启动脚本（推荐）

#### Windows 系统
```bash
# 双击运行启动脚本
start.bat

# 或者命令行运行
.\start.bat
```

#### Linux/macOS 系统
```bash
# 给脚本添加执行权限
chmod +x start.sh

# 运行启动脚本
./start.sh
```

### 方法二：手动启动

#### 1. 启动服务

```bash
# 确保虚拟环境已激活
# Windows: venv\Scripts\activate
# Linux: source venv/bin/activate

# 启动Flask应用
python app.py
```

#### 2. 访问Web界面

打开浏览器访问：`http://localhost:5000`

#### 3. 开始部署

1. **选择部署模式**：全自动、半自动或手动
2. **配置服务器信息**：主机地址、用户名、密码
3. **选择软件版本**：Hadoop版本、Java版本
4. **上传自定义包**（可选）：上传自己的Hadoop或Java安装包
5. **开始部署**：系统将自动执行部署流程

## 📁 项目结构

```
HadoopDeploy_tool/
├── app.py                  # 主程序（Flask）
├── requirements.txt        # 依赖列表
├── README.md               # 项目说明文档
├── static/                 # 静态资源
│   ├── css/                # 样式文件
│   ├── js/                 # JS 文件
│   └── vendor/             # 第三方库
├── templates/              # HTML 模板
│   ├── components/         # 页面组件
│   ├── base.html           # 基础模板
│   ├── documentation.html  # 文档中心
│   └── about.html          # 关于页面


## 📖 使用指南

### 部署模式说明

#### 🔄 全自动模式
- **适用场景**：快速部署标准Hadoop集群
- **特点**：系统自动完成所有配置，无需人工干预
- **推荐用户**：初学者或需要快速部署的用户

#### ⚙️ 半自动模式
- **适用场景**：需要自定义部分配置的部署
- **特点**：系统完成基础配置，用户可自定义关键参数
- **推荐用户**：有一定经验的用户

#### 🛠️ 手动模式
- **适用场景**：完全自定义的部署需求
- **特点**：用户完全控制每个配置细节
- **推荐用户**：高级用户和特殊需求场景

### 文件上传功能

#### 支持的格式
- **Hadoop包**：`.tar.gz`, `.tgz`
- **Java包**：`.tar.gz`, `.tgz`, `.zip`

#### 上传步骤
1. 在版本选择下拉框中选择"自定义上传"
2. 点击"选择文件"按钮
3. 选择要上传的安装包文件
4. 点击"上传"按钮
5. 等待上传完成确认

#### 注意事项
- 文件大小建议不超过2GB
- 确保文件格式正确
- 上传成功后会在部署时优先使用

### 部署流程

1. **环境检测**：检查系统环境、网络连接
2. **依赖安装**：安装Java环境和其他依赖
3. **软件下载**：下载Hadoop（或使用上传的包）
4. **配置生成**：根据用户配置生成配置文件
5. **服务启动**：启动Hadoop集群服务
6. **验证测试**：验证集群运行状态

## ⚙️ 配置说明

### 核心配置项

| 配置项 | 描述 | 默认值 | 说明 |
|--------|------|--------|------|
| `hadoop.version` | Hadoop版本 | 3.3.6 | 支持的版本：2.10.2, 3.2.4, 3.3.5, 3.3.6 |
| `java.version` | Java版本 | 8 | 支持的版本：8, 11, 17 |
| `hdfs.replication` | HDFS副本数 | 3 | 建议设置为DataNode数量 |
| `yarn.resourcemanager.host` | ResourceManager主机 | localhost | 集群主节点地址 |

### 性能调优参数

```yaml
# MapReduce内存配置
mapreduce.map.memory.mb: 2048
mapreduce.reduce.memory.mb: 4096

# YARN内存配置
yarn.nodemanager.resource.memory-mb: 8192
yarn.scheduler.maximum-allocation-mb: 4096
```

## 🔧 开发指南

### 添加新功能
1. 在`app.py`中添加路由和API
2. 在`templates/`中添加对应的HTML模板
3. 在`static/js/`中添加JavaScript逻辑
4. 在`static/css/`中添加样式



### 添加新的依赖
1. 在`requirements.txt`中添加包名和版本
2. 更新安装脚本中的依赖检查
3. 测试安装流程
```

#### 调试模式
```bash
# 启动调试模式
python app.py --debug
```

### 生产环境部署
1. 修改`config.ini`中的配置
2. 使用生产级Web服务器（如Gunicorn）
3. 配置反向代理（如Nginx）
4. 设置SSL证书
```

## 🔧 故障排除

### 常见问题

#### 1. 虚拟环境激活失败
```bash
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

#### 2. 依赖安装失败
```bash
# 升级pip
pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

#### 3. 端口被占用
```bash
# 查看端口占用
netstat -ano | findstr :5000

# 修改端口（在app.py中）
app.run(debug=True, host='0.0.0.0', port=5001)
```

#### 4. 文件上传失败
- 检查文件格式是否正确
- 确认文件大小不超过限制
- 检查网络连接状态

#### 5. 部署失败
- 检查服务器连接
- 确认服务器权限
- 查看部署日志
```

## 🤝 贡献指南

欢迎提交PR、Issue，或参与文档完善与功能建议。

## 📬 联系方式

- 项目主页：[https://github.com/violet27-chf/HadoopDeploy_tool](https://github.com/violet27-chf/HadoopDeploy_tool)
- 邮箱：violet@kami666.xyz。