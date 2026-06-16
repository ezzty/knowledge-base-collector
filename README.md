# Save Page to Markdown

Save any web page as clean Markdown with one click. Self-hosted backend, no third-party data collection.

[![Chrome Web Store](https://img.shields.io/chrome-web-store/v/enjnfcibloffgkmbachgbpmkidjhapgm)](https://chrome.google.com/webstore/detail/enjnfcibloffgkmbachgbpmkidjhapgm)

## Features

- **One-click save** — Click the icon, the page is instantly converted to Markdown
- **Bypass anti-scraping** — Content is extracted in your browser, defeating Cloudflare, EdgeOne, and other WAF protections
- **Clean Markdown output** — Automatic heading detection, link preservation, and table support
- **Smart categorization** — Organize saved pages into custom folder categories
- **Metadata extraction** — Captures title, author, publish date, and source URL automatically
- **Web-based settings** — Configure save path via a web UI at `http://server:8396/`
- **Self-hosted** — All data saved to YOUR server. No third-party cloud, no tracking, no ads
- **Fully open source** — MIT License, both extension and backend

---

## ⚠️ IMPORTANT: Docker Volume Mapping

> **This is the #1 thing you MUST understand before using Docker.**
>
> Docker containers are **isolated from your host machine**. The save path you see inside the container (e.g. `/data/knowledge-base`) is **NOT** the same as a path on your host machine.
>
> You **MUST** configure the **volume mapping** in `docker-compose.yml` to tell Docker which folder on your host machine should be used to store files.

### How it works:

```
Your host machine:          Docker container:
/home/you/notes/      ←→    /data/knowledge-base/
       ↑                           ↑
   You edit files here      The container writes here
```

The `volumes` section in `docker-compose.yml` creates this mapping:

```yaml
volumes:
  - /home/you/notes:/data/knowledge-base    # host_path:container_path
```

### ⚠️ After changing the path, you MUST restart the container:

```bash
docker compose down
docker compose up -d
```

**Without restarting, the new path will NOT take effect.** The container will still use the old path.

---

## Quick Start

### Step 1: Deploy the Backend Server

```bash
git clone https://github.com/ezzty/knowledge-base-collector.git
cd knowledge-base-collector/docker
```

**Edit `docker-compose.yml`** — change the volume mapping to your desired save path:

```yaml
volumes:
  - /your/actual/save/path:/data/knowledge-base    # ← CHANGE THIS
```

Then start:

```bash
docker compose up -d
```

### Step 2: Install the Chrome Extension

1. Install from [Chrome Web Store](https://chrome.google.com/webstore/detail/enjnfcibloffgkmbachgbpmkidjhapgm), or
2. Download `knowledge-base-extension.zip` from [Releases](https://github.com/ezzty/knowledge-base-collector/releases) and load manually:
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

---

## 🌐 Web-Based Settings

After starting the server, visit `http://your-server:8396/` in your browser to access the settings page.

You can:
- View server status and file count
- **Change the host save path** (updates `docker-compose.yml` automatically)

### ⚠️ After saving a new path in the web UI, you MUST restart:

```bash
docker compose down
docker compose up -d
```

The web UI will remind you of this. **Do not skip this step** — the container must be recreated to mount the new path.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KB_PORT` | `8396` | Server port |
| `KB_DIR` | `/data/knowledge-base` | Container-internal save path (do not change) |

### Volume Mapping (in docker-compose.yml)

| Container Path | Description |
|---------------|-------------|
| `/data/knowledge-base` | Where Markdown files are stored — **must be mapped to a host path** |
| `/data/config` | Config file storage — mapped to `./data/config` by default |

### `.env` file (optional)

Create a `.env` file in the `docker/` directory:

```bash
cp .env.example .env
```

Edit `.env`:

```
KB_PORT=8396
KB_SAVE_PATH=/home/yourname/notes
```

Then `docker compose up -d` will use these values automatically.

---

## Project Structure

```
├── manifest.json          # Chrome extension config (Manifest V3)
├── popup.html/js          # Popup UI
├── settings.html/js       # Settings page
├── background.js          # Service Worker
├── server.py              # Backend server (direct run)
├── docker/                # Docker deployment
│   ├── Dockerfile
│   ├── docker-compose.yml # ← Edit volume mapping here
│   ├── server.py          # Backend server (Docker version, includes web UI)
│   ├── requirements.txt
│   └── .env.example       # Example environment config
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
