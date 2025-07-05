# KD-H

## HadoopDeploy_tool

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Flask Version](https://img.shields.io/badge/flask-2.3+-blue.svg)](https://flask.palletsprojects.com)
[![Responsive Design](https://img.shields.io/badge/responsive-design-green.svg)](https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design)
[![Mobile Friendly](https://img.shields.io/badge/mobile-friendly-blue.svg)](https://developers.google.com/search/mobile-sites)

> 一站式 Hadoop 集群自动部署与管理平台，支持全自动、半自动、手动三种模式，Web 可视化、SSH 免密、进度与日志实时同步，完美支持移动端访问。

## ✨ 主要特性

### 🚀 **核心功能**
- **全自动部署**：一键完成 Hadoop 集群环境搭建与配置
- **SSH 免密互信**：自动分发密钥，节点间无密码通信
- **Web 可视化**：全流程进度、日志、集群 Web UI 直达
- **多模式支持**：全自动、半自动、手动部署灵活切换
- **自定义包上传**：支持 Hadoop/Java 安装包自定义上传
- **实时监控**：部署步骤与日志同步，异常高亮提示
- **模块化设计**：易于扩展和二次开发
- **网段扫描**：集成nmap功能，支持网段主机自动发现

### 📱 **移动端优势**
- **完美响应式设计**：自适应各种屏幕尺寸，从手机到4K显示器
- **触摸优化界面**：针对移动设备优化的触摸操作体验
- **移动端专属功能**：汉堡菜单、卡片布局、大按钮设计
- **随时随地部署**：通过手机即可完成Hadoop集群部署和管理
- **实时进度监控**：部署过程中可随时查看进度和日志
- **集群Web UI直达**：部署完成后可直接访问Hadoop管理界面

### 🎨 **用户体验**
- **苹果级极简美学**：采用现代设计语言，界面简洁美观
- **流畅动画效果**：精心设计的交互动画，提升用户体验
- **智能表单验证**：实时输入验证，减少用户错误
- **直观操作流程**：步骤清晰，操作简单易懂
- **多语言支持**：支持中文界面，符合国内用户习惯

### 🔧 **技术特色**
- **跨平台兼容**：支持Windows、Linux、macOS三大操作系统
- **轻量级架构**：基于Flask框架，资源占用少，启动快速
- **安全可靠**：支持HTTPS、SSH密钥管理、访问控制
- **高性能优化**：异步处理、资源压缩、缓存机制
- **易于部署**：一键安装脚本，自动化环境配置

### 🌐 **网络特性**
- **本地部署优先**：推荐本地部署，体验最佳功能
- **公网部署支持**：支持端口映射，实现远程访问
- **网段自动发现**：智能扫描局域网内可用服务器
- **多节点管理**：支持单机到大规模集群部署
- **网络诊断工具**：内置网络连通性检测功能

### 📊 **监控管理**
- **实时部署监控**：可视化部署进度，实时状态更新
- **日志实时同步**：部署日志实时显示，支持滚动查看
- **资源使用监控**：系统资源使用情况实时监控
- **错误智能提示**：异常情况智能诊断和解决建议
- **性能优化建议**：基于部署结果提供优化建议

### 🛡️ **安全特性**
- **SSH密钥管理**：自动生成和管理SSH密钥对
- **访问权限控制**：支持用户认证和访问控制
- **数据传输加密**：支持HTTPS加密传输
- **敏感信息保护**：密码等敏感信息加密存储
- **操作日志记录**：完整的操作日志记录和审计

### 🔄 **部署模式**
- **全自动模式**：零配置一键部署，适合初学者
- **半自动模式**：自定义关键参数，平衡便利性和灵活性
- **手动模式**：完全自定义配置，适合高级用户
- **批量部署**：支持多服务器批量部署
- **增量部署**：支持已有集群的增量配置

### 📈 **扩展能力**
- **插件化架构**：支持功能插件扩展
- **API接口**：提供RESTful API接口
- **配置模板**：支持自定义配置模板
- **脚本集成**：支持自定义部署脚本
- **第三方集成**：支持与CI/CD工具集成

## 📋 目录

- [系统要求](#系统要求)
- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [部署方式指南](#部署方式指南)
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
- **nmap**：用于网段扫描功能（安装脚本会自动安装）

### 推荐配置
- **操作系统**：Ubuntu 20.04 LTS 或 Windows 11
- **Python版本**：Python 3.9+
- **内存**：8GB RAM 或更多
- **磁盘空间**：50GB 可用空间
- **网络**：高速互联网连接
- **nmap版本**：7.80 或更高版本

### 依赖软件
- **Java**：OpenJDK 8 或更高版本
- **SSH**：OpenSSH 客户端
- **nmap**：网络扫描工具（用于网段主机发现）

## 📦 安装指南

### 方法一：快速安装（推荐）

#### 使用一键部署脚本

```bash
# wget命令
wegt https://raw.githubusercontent.com/violet27-chf/DeployInstall/refs/heads/main/install.sh
# curl命令
curl -o install.sh https://raw.githubusercontent.com/violet27-chf/DeployInstall/refs/heads/main/install.sh
chmod +x install.sh
./install.sh
```
### 方法二：手动安装

#### 1. 克隆项目

```bash
# 克隆项目到本地
git clone https://github.com/violet27-chf/HadoopDeploy_tool.git
cd HadoopDeploy_tool
```

#### 2. 安装系统依赖

##### Windows 系统
```bash
# 安装nmap（使用chocolatey）
choco install nmap -y

# 或者手动下载安装
# 1. 访问 https://nmap.org/download.html
# 2. 下载Windows版本的nmap安装包
# 3. 运行安装程序
```

##### Linux/macOS 系统
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y nmap

# CentOS/RHEL
sudo yum install -y nmap

# macOS
brew install nmap
```

#### 3. 创建虚拟环境

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

#### 4. 安装依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 验证安装
python -c "import flask, paramiko; print('依赖安装成功！')"
```

#### 5. 验证nmap安装

```bash
# 检查nmap版本
nmap --version

# 测试nmap功能
nmap -sn 127.0.0.1
```

## 🚀 快速开始

### 方法一：手动启动

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

## 🌐 部署方式指南

### 💻 本地部署（推荐）

#### 优势特点
- ✅ 无需端口映射，直接访问
- ✅ 网络延迟低，响应速度快
- ✅ 功能完整，体验最佳
- ✅ 支持所有部署模式
- ✅ 实时日志和进度监控
- ✅ 集群Web UI直达
- ✅ **移动端完美适配**：支持手机、平板等移动设备访问

#### 适用场景
- 内网环境部署
- 开发测试环境
- 学习体验
- 生产环境部署
- **移动办公**：随时随地通过手机管理Hadoop集群

#### 快速开始
1. 在本地机器上安装并启动HadoopDeploy Tool
2. 确保目标服务器在同一网络环境
3. 直接填写服务器IP地址进行部署

#### 📱 移动端使用指南

##### 手机访问优势
- **随时随地部署**：无需守在电脑前，通过手机即可完成Hadoop集群部署
- **响应式设计**：完美适配各种屏幕尺寸，操作流畅自然
- **触摸优化**：针对触摸操作优化，按钮大小适中，易于点击
- **实时监控**：部署过程中可随时查看进度和日志
- **集群管理**：部署完成后可直接访问Hadoop Web UI

##### 手机访问步骤

###### 1. 启动本地服务
```bash
# 在本地电脑上启动服务
python app.py

# 或者使用启动脚本
# Windows: start.bat
# Linux/macOS: ./start.sh
```

###### 2. 获取本地IP地址
```bash
# Windows
ipconfig | findstr "IPv4"

# Linux/macOS
ifconfig | grep "inet "
# 或
ip addr show | grep "inet "
```

###### 3. 手机访问
- 确保手机与电脑在同一WiFi网络
- 打开手机浏览器
- 访问：`http://[电脑IP地址]:5000`
- 例如：`http://192.168.1.100:5000`

##### 移动端功能特性

###### 🎯 **完美适配的界面**
- **自适应布局**：根据屏幕尺寸自动调整布局
- **触摸友好**：按钮和控件大小适合手指操作
- **手势支持**：支持滑动、缩放等手势操作
- **快速响应**：优化的JavaScript确保流畅体验

###### 📱 **移动端专属优化**
- **汉堡菜单**：小屏设备自动显示折叠菜单
- **卡片布局**：信息以卡片形式展示，易于浏览
- **大按钮设计**：重要操作按钮尺寸适中，易于点击
- **简化表单**：移动端表单布局优化，减少输入难度

###### 🔄 **实时部署监控**
- **进度可视化**：部署进度以进度条形式展示
- **实时日志**：部署日志实时更新，支持滚动查看
- **状态指示**：每个部署步骤都有清晰的状态指示
- **错误提示**：异常情况会以醒目的方式提示

###### 🌐 **集群Web UI直达**
- **一键访问**：部署完成后可直接访问Hadoop Web UI
- **移动适配**：Hadoop原生界面也支持移动端访问
- **快速导航**：提供常用功能的快速入口

##### 移动端使用场景

###### 🏢 **企业环境**
- **运维人员**：外出时紧急处理集群问题
- **开发人员**：远程调试和部署测试环境
- **管理人员**：随时查看集群状态和性能

###### 🏫 **教育环境**
- **学生实验**：在实验室外继续Hadoop学习
- **教师演示**：在课堂上用手机演示部署过程
- **远程教学**：支持远程Hadoop课程教学

###### 🏠 **个人使用**
- **学习实践**：随时随地练习Hadoop部署
- **项目开发**：移动办公时管理开发环境
- **演示展示**：向客户或同事展示项目功能

##### 移动端最佳实践

###### 📶 **网络配置**
- 确保手机和电脑在同一局域网
- 检查防火墙设置，确保5000端口开放
- 建议使用5GHz WiFi以获得更好体验

###### 🔋 **设备优化**
- 保持手机电量充足
- 关闭不必要的后台应用
- 使用现代浏览器（Chrome、Safari、Firefox）

###### 🎮 **操作技巧**
- 横屏模式可获得更好的操作体验
- 使用手机浏览器的"添加到主屏幕"功能
- 开启浏览器的"桌面模式"获得更完整功能

##### 移动端特色功能

###### 📊 **网段扫描（仅本地部署）**
- 在手机上扫描局域网内的服务器
- 一键添加发现的服务器到部署列表
- 支持CIDR格式网段扫描

###### 📱 **响应式表单**
- 服务器配置表单完美适配手机屏幕
- 智能输入提示和验证
- 支持复制粘贴服务器信息

###### 🎯 **部署模式选择**
- 全自动模式：一键完成所有配置
- 半自动模式：自定义关键参数
- 手动模式：完全控制部署过程

###### 📈 **实时监控面板**
- 部署进度实时更新
- 系统资源使用情况监控
- 网络连接状态显示

##### 移动端安全考虑

###### 🔒 **网络安全**
- 仅在可信任的局域网内使用
- 避免在公共WiFi环境下使用
- 定期更新系统和浏览器

###### 👤 **访问控制**
- 考虑添加用户认证机制
- 限制访问IP范围
- 记录访问日志

###### 🔐 **数据传输**
- 所有数据传输使用HTTPS（如配置）
- 敏感信息加密存储
- 定期清理临时文件

##### 移动端故障排除

###### 📱 **常见问题**
- **无法访问**：检查IP地址和端口是否正确
- **界面异常**：刷新页面或清除浏览器缓存
- **操作卡顿**：关闭其他应用，释放内存
- **网络超时**：检查网络连接和防火墙设置

###### 🛠️ **解决方案**
- 重启HadoopDeploy Tool服务
- 检查电脑防火墙设置
- 确认手机和电脑在同一网络
- 尝试使用其他浏览器

##### 移动端性能优化

###### ⚡ **加载速度**
- 静态资源压缩和缓存
- 图片懒加载
- JavaScript代码优化

###### 📱 **内存使用**
- 及时清理不需要的数据
- 优化DOM操作
- 减少不必要的网络请求

###### 🔄 **响应速度**
- 异步处理耗时操作
- 使用WebSocket实时通信
- 优化数据库查询

### 🌐 公网部署

#### 特点说明
- 🔧 需要配置端口映射
- 🔧 网络延迟相对较高
- 🔧 功能可能受限
- 🔧 需要稳定的网络连接
- 🔧 依赖第三方服务
- 🔧 可能存在安全风险

#### 适用场景
- 远程部署
- 演示展示
- 临时使用

#### ChmlFrp端口映射配置

**推荐使用：** [ChmlFrp](https://www.chmlfrp.cn/) 进行端口映射配置

##### 配置步骤

1. **注册账号**
   - 访问 [ChmlFrp官网](https://www.chmlfrp.cn/) 并注册账号

2. **下载客户端**
   - 在"客户端下载"页面选择与您操作系统匹配的版本（Windows/Linux/Mac）

3. **创建隧道**
   - 登录管理面板，点击"添加隧道"
   - 填写配置参数：
     - 本地IP：虚拟机的内网IP地址
     - 本地端口：22（SSH端口）
     - 隧道类型：TCP
     - 远程端口：自动分配或自定义
     - 中转节点：选择延迟低的节点

4. **下载配置文件**
   - 在隧道详情页下载 `frpc.ini` 配置文件

5. **启动客户端**
   ```bash
   # 将 frpc.exe（或 frpc）与 frpc.ini 放在同一目录
   frpc.exe -c frpc.ini
   ```

6. **公网SSH连接**
   ```bash
   # 使用分配的公网IP和端口
   ssh 用户名@公网IP -p 分配端口
   ```

##### 高级配置
- 设置开机自启动
- 配置多个隧道
- 设置访问控制

##### 故障排查
- 检查防火墙设置
- 验证端口占用情况
- 确认网络连接状态
- 查看客户端日志

##### 注意事项
- 务必保证本地22端口未被占用，且虚拟机网络为桥接或能被宿主机访问
- 建议优先选择延迟低的中转节点，提升连接速度
- 如需映射Web端口（如5000），可新建隧道，端口填写5000
- 更多帮助请参考 [官方帮助文档](https://docs.chcat.cn/docs/chmlfrp/%E4%BD%BF%E7%94%A8%E6%96%87%E6%A1%A3/tutorial)

### 📊 部署方式对比

| 特性 | 本地部署 | 公网部署 |
|------|----------|----------|
| 端口映射 | ❌ 无需 | ✅ 需要 |
| 网络延迟 | ✅ 低 | 🔧 较高 |
| 功能完整性 | ✅ 完整 | 🔧 可能受限 |
| 安全性 | ✅ 高 | 🔧 相对较低 |
| 配置复杂度 | ✅ 简单 | 🔧 复杂 |
| 移动端支持 | ✅ 完美支持 | 🔧 功能受限 |
| 网段扫描 | ✅ 可用 | ❌ 不可用 |
| 实时监控 | ✅ 流畅 | 🔧 可能卡顿 |
| 适用场景 | 内网环境、开发测试、移动办公 | 远程部署、演示展示 |

**推荐建议：** 优先选择本地部署体验完整功能，公网部署适合远程场景。本地部署提供更稳定、更快速、更安全的部署体验，同时完美支持移动端访问。

### 📱 移动端部署体验对比

| 功能特性 | 本地部署 | 公网部署 |
|----------|----------|----------|
| 响应式界面 | ✅ 完美适配 | ✅ 基本适配 |
| 触摸操作 | ✅ 优化体验 | 🔧 一般体验 |
| 网段扫描 | ✅ 可用 | ❌ 不可用 |
| 实时进度 | ✅ 流畅更新 | 🔧 可能延迟 |
| 表单操作 | ✅ 智能验证 | 🔧 基础验证 |
| 集群管理 | ✅ 完整功能 | 🔧 部分功能 |
| 网络稳定性 | ✅ 稳定 | 🔧 依赖网络 |
| 安全性 | ✅ 高 | 🔧 中等 |

**移动端推荐：** 本地部署是移动端使用的最佳选择，提供完整的移动端功能和最佳的用户体验。

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

### 网段扫描功能

#### 🔍 功能说明
HadoopDeploy_tool集成了nmap网段扫描功能，可以帮助您快速发现网络中的可用主机，简化多节点集群的配置过程。

#### 📋 使用步骤
1. **打开网段扫描**
   - 在服务器配置页面点击"扫描网段主机"按钮
   - 系统会弹出扫描配置对话框

2. **配置扫描参数**
   - 输入要扫描的网段（如：192.168.1.0/24）
   - 点击"开始扫描"按钮

3. **查看扫描结果**
   - 系统会显示扫描到的主机列表
   - 包含IP地址、主机名、MAC地址等信息
   - 可以直接选择主机添加到服务器列表

#### ⚙️ 扫描参数说明
- **网段格式**：支持CIDR格式（如192.168.1.0/24）
- **扫描类型**：Ping扫描（-sn参数）
- **扫描范围**：支持/8到/30的网段范围
- **超时设置**：默认30秒超时

#### 🔧 高级用法
```bash
# 手动使用nmap扫描
nmap -sn 192.168.1.0/24

# 扫描特定端口
nmap -p 22 192.168.1.0/24

# 详细扫描
nmap -sS -sV -O 192.168.1.0/24
```

#### ⚠️ 注意事项
- 确保有足够的网络权限进行扫描
- 大型网段扫描可能需要较长时间
- 某些网络环境可能限制扫描功能
- 建议在测试环境中使用

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

#### 3. nmap安装失败

##### Windows系统
```bash
# 检查chocolatey是否安装
choco --version

# 如果未安装chocolatey，先安装
powershell -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"

# 安装nmap
choco install nmap -y
```

##### Linux系统
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y nmap

# CentOS/RHEL
sudo yum install -y nmap

# 验证安装
nmap --version
```

#### 4. nmap扫描功能异常

##### 权限问题
```bash
# Linux系统需要root权限
sudo nmap -sn 192.168.1.0/24

# 或者添加nmap到sudoers
sudo visudo
# 添加：username ALL=(ALL) NOPASSWD: /usr/bin/nmap
```

##### 网络问题
```bash
# 检查网络连接
ping 192.168.1.1

# 检查防火墙设置
sudo ufw status
sudo iptables -L

# 测试nmap基本功能
nmap -sn 127.0.0.1
```

##### 扫描超时
```bash
# 使用更短的超时时间
nmap -sn --max-retries 1 192.168.1.0/24

# 或者扫描更小的网段
nmap -sn 192.168.1.0/28
```

#### 5. 端口被占用
```bash
# 查看端口占用
netstat -ano | findstr :5000

# 修改端口（在app.py中）
app.run(debug=True, host='0.0.0.0', port=5001)
```

#### 6. 文件上传失败
- 检查文件格式是否正确
- 确认文件大小不超过限制
- 检查网络连接状态

#### 7. 部署失败
- 检查服务器连接
- 确认服务器权限
- 查看部署日志

#### 8. 公网部署连接失败
```bash
# 检查frp客户端状态
ps aux | grep frpc

# 查看frp客户端日志
tail -f frpc.log

# 检查防火墙设置
sudo ufw status
sudo iptables -L
```

#### 9. 端口映射配置问题
- 确认本地IP地址正确
- 检查本地端口是否被占用
- 验证隧道配置参数
- 确认中转节点选择合理

#### 10. SSH连接超时
```bash
# 测试网络连通性
ping 公网IP

# 测试端口连通性
telnet 公网IP 端口号

# 检查SSH服务状态
sudo systemctl status ssh
```

#### 11. 第三方服务相关问题
- 检查ChmlFrp服务状态
- 确认账号和配置信息正确
- 查看官方帮助文档
- 联系第三方服务技术支持

## 🤝 贡献指南

欢迎提交PR、Issue，或参与文档完善与功能建议。

## 📬 联系方式

- 项目主页：[https://github.com/violet27-chf/HadoopDeploy_tool](https://github.com/violet27-chf/HadoopDeploy_tool)
- 邮箱：violet@kami666.xyz

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

Copyright (c) 2024 violet27-chf

MIT许可证允许您自由使用、修改和分发本软件，但需要保留版权声明和许可证声明。详情请参阅 [LICENSE](LICENSE) 文件。

## 👥 合作者（Contributors）

<p align="center">
  <a href="https://github.com/violet27-chf" target="_blank">
    <img src="https://github.com/violet27-chf.png" width="60" style="border-radius:50%;margin:8px;" title="Mr.chen"/>
  </a>
</p>
<p align="center">
  <a href="https://github.com/tingyiT1" target="_blank">
    <img src="https://github.com/tingyiT1.png" width="60" style="border-radius:50%;margin:8px;" title="Caelan Hawke Frost"/>
  </a>
</p>

- [violet27-chf](https://github.com/violet27-chf)（Mr.chen）
- [tingyiT1](https://github.com/tingyiT1)（Caelan Hawke Frost）
