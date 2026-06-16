# Save Page to Markdown

Save any web page as clean Markdown with one click. Self-hosted backend, no third-party data collection.

[![Chrome Web Store](https://img.shields.io/chrome-web-store/v/enjnfcibloffgkmbachgbpmkidjhapgm)](https://chrome.google.com/webstore/detail/enjnfcibloffgkmbachgbpmkidjhapgm)

## Features

- **One-click save** — Click the icon, the page is instantly converted to Markdown
- **Bypass anti-scraping** — Content is extracted in your browser, defeating Cloudflare, EdgeOne, and other WAF protections
- **Clean Markdown output** — Automatic heading detection, link preservation, and table support
- **Smart categorization** — Organize saved pages into custom folder categories
- **Metadata extraction** — Captures title, author, publish date, and source URL automatically
- **Self-hosted** — All data saved to YOUR server. No third-party cloud, no tracking, no ads
- **Fully open source** — MIT License, both extension and backend

## Quick Start

### Step 1: Deploy the Backend Server

**Option A: Docker Compose (Recommended)**

```bash
git clone https://github.com/ezzty/knowledge-base-collector.git
cd knowledge-base-collector/docker
docker compose up -d
```

Server runs at `http://localhost:8396`. Files saved to `./data/knowledge-base/`.

**Option B: Direct Python**

```bash
pip install trafilatura markdownify readability-lxml requests
python3 server.py
```

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `KB_PORT` | `8396` | Server port |
| `KB_DIR` | `./knowledge-base` | Knowledge base save path |

### Step 2: Install the Chrome Extension

1. Install from [Chrome Web Store](https://chrome.google.com/webstore/detail/enjnfcibloffgkmbachgbpmkidjhapgm), or
2. Download `knowledge-base-extension.zip` and load manually:
   - Open Chrome → `chrome://extensions/`
   - Enable "Developer mode" (top right)
   - Click "Load unpacked" → select the extracted folder

### Step 3: Configure the Server Address

1. Click the extension icon → ⚙️ Settings (top right)
2. Enter your backend server address, e.g. `http://192.168.1.100:8396`
3. Click "Test Connection" to verify
4. Save settings

### Step 4: Use

1. Browse to any page you want to save
2. Click the extension icon
3. Optionally set a filename or category
4. Click "Save to Markdown"

## Project Structure

```
├── manifest.json          # Chrome extension config (Manifest V3)
├── popup.html/js          # Popup UI
├── settings.html/js       # Settings page
├── background.js          # Service Worker
├── server.py              # Backend server (direct run)
├── docker/                # Docker deployment
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── server.py          # Backend server (Docker version)
│   └── requirements.txt
├── privacy.html           # Privacy policy page
└── icon*.png              # Extension icons
```

## Tech Stack

- **Frontend**: Chrome Extension Manifest V3, `activeTab` + `chrome.scripting` (on-demand injection)
- **Backend**: Python HTTP Server, trafilatura, readability-lxml, markdownify
- **Deployment**: Docker Compose

## Permissions

| Permission | Reason |
|-----------|--------|
| `activeTab` | Access the current tab content when the user clicks the extension icon |
| `storage` | Save the user's server URL preference locally |
| `scripting` | Inject content extraction script on demand (only when user clicks "Save") |

## License

MIT
