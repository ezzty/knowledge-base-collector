# 📚 知识库收藏 — Chrome Extension + Self-hosted Backend

一键保存网页为 Markdown 文档到你的本地知识库。浏览器端提取内容，绕过 WAF/反爬保护。

[![Chrome Web Store](https://img.shields.io/chrome-web-store/v/enjnfcibloffgkmbachgbpmkidjhapgm)](https://chrome.google.com/webstore/detail/enjnfcibloffgkmbachgbpmkidjhapgm)

## ✨ 功能特性

- 🔖 一键保存当前网页为 Markdown
- 🛡️ 浏览器端提取内容，绕过 WAF/反爬（Cloudflare、EdgeOne 等）
- 📁 支持自定义分类子文件夹
- 🏷️ 自动提取标题、作者、发布时间
- ⚙️ 可配置后端服务器地址
- 🐳 Docker 一键部署后端

## 🚀 快速开始

### 第 1 步：部署后端服务

**方式 A：Docker Compose（推荐）**

```bash
git clone https://github.com/ezzty/knowledge-base-collector.git
cd knowledge-base-collector/docker
docker compose up -d
```

服务默认运行在 `http://localhost:8396`，知识库保存在 `./data/knowledge-base/`。

**方式 B：直接运行**

```bash
pip install trafilatura markdownify readability-lxml requests
python3 server.py
```

**环境变量：**

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `KB_PORT` | `8396` | 服务端口 |
| `KB_DIR` | `./knowledge-base` | 知识库保存路径 |

### 第 2 步：安装 Chrome 插件

1. 从 [Chrome Web Store](https://chrome.google.com/webstore/detail/enjnfcibloffgkmbachgbpmkidjhapgm) 安装
2. 或者下载 `knowledge-base-extension.zip` 解压后手动加载：
   - 打开 Chrome → `chrome://extensions/`
   - 打开右上角「开发者模式」
   - 点「加载已解压的扩展程序」→ 选择解压后的文件夹

### 第 3 步：配置服务器地址

1. 点击插件图标 → 右上角 ⚙️ 设置
2. 填入后端服务地址，如 `http://192.168.1.100:8396`
3. 点「测试连接」确认正常
4. 保存设置

### 第 4 步：使用

1. 浏览到想收藏的网页
2. 点击插件图标
3. 可选填文件名、分类
4. 点「保存到知识库」

## 📁 项目结构

```
├── manifest.json          # Chrome 插件配置
├── popup.html/js          # 插件弹窗 UI
├── settings.html/js       # 插件设置页面
├── content.js             # 浏览器端内容提取
├── background.js          # Service Worker
├── server.py              # 后端服务（直接运行版）
├── docker/                # Docker 部署
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── server.py          # 后端服务（Docker 版）
│   └── requirements.txt
└── icon*.png              # 插件图标
```

## 🏗️ 技术栈

- **前端**: Chrome Extension Manifest V3, Chrome Storage API, Content Scripts
- **后端**: Python HTTP Server, trafilatura, readability-lxml, markdownify
- **部署**: Docker Compose

## 📝 License

MIT
