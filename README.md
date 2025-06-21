# Hadoop 部署工具

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://python.org)
[![Flask Version](https://img.shields.io/badge/flask-2.0+-blue.svg)](https://flask.palletsprojects.com)

> 简化Hadoop集群部署与管理的专业工具

## 特性

- 🚀 **一键部署**：快速搭建Hadoop集群环境
- ⚙️ **灵活配置**：支持多种配置方案
- 🔒 **安全可靠**：内置安全最佳实践
- 📊 **可视化监控**：实时查看集群状态

## 目录

- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [配置参考](#配置参考)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 安装指南

### 系统要求

- Linux 操作系统
- Python 3.6+
- 至少4GB内存

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/violet27-chf/Hadoop.git
cd hadoop-deployer

# 安装依赖
pip install -r requirements.txt

# 启动服务
flask run
```

## 快速开始

1. 访问Web界面：
   ```bash
   http://localhost:5000
   ```

2. 添加服务器节点：
   ```yaml
   nodes:
     - host: node1.example.com
       role: [namenode, datanode]
     - host: node2.example.com
       role: [datanode]
   ```

3. 开始部署：
   ```bash
   ./deploy.sh --config cluster-config.yaml
   ```

## 配置参考

### 核心配置项

| 配置项 | 描述 | 默认值 |
|--------|------|--------|
| `hadoop.version` | Hadoop版本 | 3.3.4 |
| `hdfs.replication` | 数据副本数 | 3 |
| `yarn.resourcemanager.host` | ResourceManager主机 | namenode |

## 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork项目仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交Pull Request

## 许可证

本项目采用 [MIT](LICENSE) 许可证。

---

📧 如有问题请联系：1494458927@qq.com