# Save Page to Markdown

Save any web page as clean Markdown with one click. Self-hosted backend, no third-party data collection.

[![Chrome Web Store](https://img.shields.io/chrome-web-store/v/enjnfcibloffgkmbachgbpmkidjhapgm)](https://chrome.google.com/webstore/detail/enjnfcibloffgkmbachgbpmkidjhapgm)

## Features

- **One-click save** — Click the icon, the page is instantly converted to Markdown
- **YAML Frontmatter** — Source URL, saved date, author, description, category
- **Image localization** — Downloads images to `assets/` folder, replaces URLs in Markdown
- **Bypass anti-scraping** — Content is extracted in your browser, defeating Cloudflare, EdgeOne, and other WAF protections
- **Clean Markdown output** — Automatic heading detection, link preservation, and table support
- **Smart categorization** — Organize saved pages into custom folder categories
- **Subfolder support** — Change save subfolder via Web UI, instant effect, no restart
- **Self-hosted** — All data saved to YOUR server. No third-party cloud, no tracking, no ads
- **Fully open source** — MIT License

---

## Quick Start

```bash
git clone https://github.com/ezzty/knowledge-base-collector.git
cd knowledge-base-collector/server
docker compose up -d
```

Open `http://your-server:8396/` to configure.

## Project Structure

```
├── extension/           # Chrome extension source
│   ├── manifest.json
│   ├── popup.html/js
│   ├── settings.html/js
│   ├── content.js
│   └── background.js
├── server/              # Docker backend
│   ├── server.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
└── README.md
```

## Install Chrome Extension

**Option A:** Install from [Chrome Web Store](https://chrome.google.com/webstore/detail/enjnfcibloffgkmbachgbpmkidjhapgm)

**Option B:** Manual install
1. Download the latest [release zip](https://github.com/ezzty/knowledge-base-collector/releases)
2. Go to `chrome://extensions/` → Enable "Developer mode"
3. Click "Load unpacked" → Select the `extension/` folder

## Configure Extension

1. Click the extension icon → ⚙️ Settings (top right)
2. Enter server address, e.g. `http://192.168.1.100:8396`
3. Click "Test Connection" → Save

## Web UI Settings

Visit `http://your-server:8396/` to configure:

- **Host Directory** — The directory on your host machine where files are saved (requires container restart)
- **Subfolder** — Subdirectory within the host directory (instant, no restart)

## How It Works

```
Browser (Chrome Extension)
    ↓ HTTP POST /save
Docker Container (server.py)
    ↓ Saves to /data/knowledge-base/
Host Directory (mapped via docker-compose.yml volumes)
```

The container saves files to `/data/knowledge-base/` internally. The `docker-compose.yml` `volumes` setting maps this to a directory on your host machine.

Default mapping: `./knowledge-base:/data/knowledge-base` — files are saved to `./knowledge-base/` relative to `docker-compose.yml`.

## Output Format

```markdown
---
title: "Article Title"
source_url: "https://example.com/article"
saved_date: "2026-06-16 13:46"
author: "Author Name"
description: "Page description"
category: "tech"
images_localized: 3
---

# Article Title

Content with local images:

![Photo](assets/ae79195aff.png)
```

## License

MIT

---

# 保存网页为 Markdown

一键将任意网页保存为干净的 Markdown 文件。自托管后端，不收集第三方数据。

## 功能特点

- **一键保存** — 点击图标，网页瞬间转为 Markdown
- **YAML Frontmatter** — 源链接、保存日期、作者、描述、分类
- **图片本地化** — 自动下载图片到 `assets/` 文件夹，替换 MD 中的链接
- **绕过反爬** — 内容在浏览器端提取，轻松突破 Cloudflare、EdgeOne 等 WAF 防护
- **干净的 Markdown** — 自动识别标题、保留链接、支持表格
- **智能分类** — 将保存的页面归入自定义文件夹分类
- **子文件夹支持** — 通过 Web UI 修改保存子目录，秒级生效，无需重启
- **完全自托管** — 所有数据保存在你的服务器上。无第三方云、无追踪、无广告
- **完全开源** — MIT 许可证

---

## 快速开始

```bash
git clone https://github.com/ezzty/knowledge-base-collector.git
cd knowledge-base-collector/server
docker compose up -d
```

打开 `http://你的服务器IP:8396/` 进行配置。

## 项目结构

```
├── extension/           # Chrome 扩展源码
│   ├── manifest.json
│   ├── popup.html/js
│   ├── settings.html/js
│   ├── content.js
│   └── background.js
├── server/              # Docker 后端
│   ├── server.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
└── README.md
```

## 安装 Chrome 扩展

**方式一：** 从 [Chrome 应用商店](https://chrome.google.com/webstore/detail/enjnfcibloffgkmbachgbpmkidjhapgm) 安装

**方式二：** 手动安装
1. 从 [GitHub Releases](https://github.com/ezzty/knowledge-base-collector/releases) 下载最新 zip
2. 打开 `chrome://extensions/` → 开启「开发者模式」
3. 点击「加载已解压的扩展程序」→ 选择 `extension/` 文件夹

## 配置扩展

1. 点击扩展图标 → 右上角 ⚙️ 设置
2. 输入服务器地址，如 `http://192.168.1.100:8396`
3. 点击「测试连接」→ 保存

## Web UI 设置

访问 `http://你的服务器IP:8396/` 进行配置：

- **Host Directory** — 宿主机上的存储目录（修改后需重启容器）
- **Subfolder** — 存储子目录（秒级生效，无需重启）

## 工作原理

```
浏览器（Chrome 扩展）
    ↓ HTTP POST /save
Docker 容器（server.py）
    ↓ 保存到 /data/knowledge-base/
宿主机目录（通过 docker-compose.yml volumes 映射）
```

容器内部将文件保存到 `/data/knowledge-base/`。`docker-compose.yml` 的 `volumes` 设置将其映射到宿主机的某个目录。

默认映射：`./knowledge-base:/data/knowledge-base` — 文件保存在 `docker-compose.yml` 同级的 `./knowledge-base/` 目录。

## 输出格式

```markdown
---
title: "文章标题"
source_url: "https://example.com/article"
saved_date: "2026-06-16 13:46"
author: "作者名"
description: "页面描述"
category: "tech"
images_localized: 3
---

# 文章标题

正文内容，图片已本地化：

![图片](assets/ae79195aff.png)
```

## 许可证

MIT
