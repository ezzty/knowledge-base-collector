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

Markdown files are saved to `./knowledge-base/` (same directory as `docker-compose.yml`).

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
├── store-assets/        # Chrome Web Store screenshots
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

Visit `http://your-server:8396/` to:

- **Subfolder** — Change save subfolder (instant, no restart)
- **Host Directory** — Change the host volume mapping (requires container restart)

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
