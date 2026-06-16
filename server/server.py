#!/usr/bin/env python3
"""
Knowledge Base Collector Server - Receives web page URLs from the Chrome extension,
fetches content, converts to Markdown, and saves to the knowledge base directory.

Port: 8396 (configurable via KB_PORT env var)
Knowledge base: /data/knowledge-base/ (configurable via web UI or KB_DIR env var)
"""

import http.server
import json
import os
import re
import hashlib
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import requests
import markdownify
import trafilatura

PORT = int(os.environ.get('KB_PORT', 8396))
BASE_DIR = Path(os.environ.get('KB_DIR', '/data/knowledge-base'))
CONFIG_FILE = Path('/data/config/config.json')

# Browser headers for bypassing anti-scraping
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}


def load_config() -> dict:
    """Load config from file, or create default"""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except:
            pass
    return {"subfolder": ""}


def save_config(config: dict):
    """Save config to file"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False))


def get_save_path() -> Path:
    """Get current save path: BASE_DIR + subfolder from config"""
    config = load_config()
    subfolder = config.get('subfolder', '').strip()
    # Sanitize subfolder: no leading/trailing slashes, no .. traversal
    if subfolder:
        subfolder = subfolder.replace('..', '').strip('/')
    if subfolder:
        return BASE_DIR / subfolder
    return BASE_DIR


# ==================== SETTINGS PAGE HTML ====================

SETTINGS_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Save Page to Markdown — Settings</title>
<style>
  :root {
    --bg: #0f172a; --card: #1e293b; --border: #334155;
    --text: #e2e8f0; --sub: #94a3b8; --accent: #3b82f6;
    --accent-hover: #2563eb; --green: #22c55e; --red: #ef4444;
    --input-bg: #0f172a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg); color: var(--text);
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    padding: 20px;
  }
  .container {
    width: 100%; max-width: 520px;
    background: var(--card); border: 1px solid var(--border);
    border-radius: 16px; padding: 32px; box-shadow: 0 4px 24px rgba(0,0,0,0.3);
  }
  .header {
    text-align: center; margin-bottom: 28px;
    padding-bottom: 20px; border-bottom: 1px solid var(--border);
  }
  .header h1 { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
  .header p { font-size: 13px; color: var(--sub); }
  .field { margin-bottom: 20px; }
  .field label {
    display: block; font-size: 12px; color: var(--sub);
    text-transform: uppercase; letter-spacing: 0.5px;
    margin-bottom: 6px; font-weight: 600;
  }
  .field input {
    width: 100%; padding: 10px 14px; background: var(--input-bg);
    border: 1px solid var(--border); border-radius: 8px;
    color: var(--text); font-size: 14px; outline: none;
    transition: border-color 0.2s;
  }
  .field input:focus { border-color: var(--accent); }
  .field .hint { font-size: 11px; color: var(--sub); margin-top: 4px; }
  .btn {
    width: 100%; padding: 12px; border: none; border-radius: 8px;
    font-size: 14px; font-weight: 600; cursor: pointer;
    transition: all 0.2s; margin-bottom: 8px;
  }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover { background: var(--accent-hover); }
  .btn-secondary { background: var(--border); color: var(--text); }
  .btn-secondary:hover { background: #475569; }
  .status {
    margin-top: 12px; padding: 10px 14px; border-radius: 8px;
    font-size: 13px; display: none; word-break: break-all;
  }
  .status.success { display: block; background: #052e16; color: var(--green); border: 1px solid #166534; }
  .status.error { display: block; background: #2d0a0a; color: var(--red); border: 1px solid #7f1d1d; }
  .status.info { display: block; background: #0c1a3a; color: var(--accent); border: 1px solid #1e3a5f; }
  .stats {
    background: var(--input-bg); border: 1px solid var(--border);
    border-radius: 8px; padding: 14px; margin-bottom: 20px;
  }
  .stats .row {
    display: flex; justify-content: space-between;
    padding: 4px 0; font-size: 13px;
  }
  .stats .label { color: var(--sub); }
  .stats .value { color: var(--text); font-weight: 500; }
  .footer {
    margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border);
    text-align: center; font-size: 12px; color: var(--sub);
  }
  .footer a { color: var(--accent); text-decoration: none; }
  .footer a:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📚 Save Page to Markdown</h1>
    <p>Server Settings</p>
  </div>

  <div class="stats" id="stats">
    <div class="row"><span class="label">Status</span><span class="value" id="serverStatus">Loading...</span></div>
    <div class="row"><span class="label">Host Directory</span><span class="value" id="hostDir">—</span></div>
    <div class="row"><span class="label">Save Path</span><span class="value" id="currentPath">—</span></div>
    <div class="row"><span class="label">Files Saved</span><span class="value" id="fileCount">—</span></div>
  </div>

  <div class="field">
    <label>Host Directory</label>
    <input type="text" id="hostDirInput" placeholder="./knowledge-base">
    <div class="hint">Directory on the host machine where files are saved. ⚠️ Changing this requires container restart.</div>
  </div>

  <div class="field">
    <label>Subfolder (optional)</label>
    <input type="text" id="subfolder" placeholder="e.g. tech/articles or 我的收藏">
    <div class="hint">Subfolder within the host directory. Leave empty to save directly to the root. Changes take effect immediately.</div>
  </div>

  <button class="btn btn-primary" id="saveBtn">💾 Save Subfolder</button>
  <button class="btn btn-secondary" id="saveHostDirBtn" style="background:#475569">📁 Change Host Directory & Restart</button>
  <button class="btn btn-secondary" id="testBtn">🔗 Test Connection</button>

  <div class="status" id="status"></div>

  <div class="footer">
    <p><a href="https://github.com/ezzty/knowledge-base-collector" target="_blank">GitHub</a> · <a href="/health" target="_blank">Health Check</a></p>
  </div>

<details style="margin-top:24px;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px 32px;color:var(--text)">
  <summary style="cursor:pointer;font-weight:700;font-size:16px;color:var(--accent)">📖 安装说明（中文）</summary>

  <h3 style="margin-top:20px;color:var(--accent)">🚀 快速安装</h3>
  <pre style="background:var(--border);padding:12px;border-radius:8px;overflow-x:auto;font-size:13px"><code>git clone https://github.com/ezzty/knowledge-base-collector.git
cd knowledge-base-collector/docker
docker compose up -d</code></pre>
  <p>Markdown 文件默认保存在 <code>./knowledge-base/</code> 目录（与 docker-compose.yml 同级）。</p>

  <h3 style="margin-top:20px;color:var(--accent)">🔧 安装 Chrome 插件</h3>
  <ol>
    <li>从 <a href="https://chrome.google.com/webstore/detail/enjnfcibloffgkmbachgbpmkidjhapgm" target="_blank">Chrome 应用商店</a> 安装，或</li>
    <li>从 <a href="https://github.com/ezzty/knowledge-base-collector/releases" target="_blank">GitHub Releases</a> 下载 zip 解压手动加载：
      <br>Chrome → <code>chrome://extensions/</code> → 开启"开发者模式" → "加载已解压的扩展程序"</li>
  </ol>

  <h3 style="margin-top:20px;color:var(--accent)">⚙️ 配置插件</h3>
  <ol>
    <li>点击插件图标 → 右上角 ⚙️ 设置</li>
    <li>填入服务器地址，如 <code>http://192.168.1.100:8396</code></li>
    <li>点"测试连接"确认正常 → 保存</li>
  </ol>

  <h3 style="margin-top:20px;color:var(--accent)">🌐 网页端修改保存子目录</h3>
  <p>访问 <code>http://服务器IP:8396/</code> 可以在网页上直接修改保存子目录。</p>
  <p style="color:var(--sub);font-size:12px">子目录修改后<strong>立即生效</strong>，无需重启容器。留空则保存到根目录。</p>
</details>

<details style="margin-top:16px;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px 32px;color:var(--text)">
  <summary style="cursor:pointer;font-weight:700;font-size:16px;color:var(--accent)">📖 Installation Guide (English)</summary>

  <h3 style="margin-top:20px;color:var(--accent)">🚀 Quick Start</h3>
  <pre style="background:var(--border);padding:12px;border-radius:8px;overflow-x:auto;font-size:13px"><code>git clone https://github.com/ezzty/knowledge-base-collector.git
cd knowledge-base-collector/docker
docker compose up -d</code></pre>
  <p>Markdown files are saved to <code>./knowledge-base/</code> by default (same directory as docker-compose.yml).</p>

  <h3 style="margin-top:20px;color:var(--accent)">🔧 Install Chrome Extension</h3>
  <ol>
    <li>Install from <a href="https://chrome.google.com/webstore/detail/enjnfcibloffgkmbachgbpmkidjhapgm" target="_blank">Chrome Web Store</a>, or</li>
    <li>Download zip from <a href="https://github.com/ezzty/knowledge-base-collector/releases" target="_blank">GitHub Releases</a> and load manually:
      <br>Chrome → <code>chrome://extensions/</code> → Enable "Developer mode" → "Load unpacked"</li>
  </ol>

  <h3 style="margin-top:20px;color:var(--accent)">⚙️ Configure Extension</h3>
  <ol>
    <li>Click extension icon → ⚙️ Settings (top right)</li>
    <li>Enter server address, e.g. <code>http://192.168.1.100:8396</code></li>
    <li>Click "Test Connection" to verify → Save</li>
  </ol>

  <h3 style="margin-top:20px;color:var(--accent)">🌐 Change Save Subfolder via Web UI</h3>
  <p>Visit <code>http://your-server:8396/</code> to change the save subfolder in your browser.</p>
  <p style="color:var(--sub);font-size:12px">Changes take effect <strong>immediately</strong> — no restart needed. Leave empty to save to the root directory.</p>
</details>
</div>

<script>
const status = document.getElementById('status');

function showStatus(msg, type) {
  status.className = 'status ' + type;
  status.textContent = msg;
}

async function loadConfig() {
  try {
    const resp = await fetch('/api/config');
    const data = await resp.json();
    document.getElementById('subfolder').value = data.subfolder || '';
    document.getElementById('serverStatus').textContent = '✅ Running';
    document.getElementById('fileCount').textContent = data.file_count ?? '—';
    document.getElementById('currentPath').textContent = data.save_path || '—';
    document.getElementById('hostDir').textContent = data.host_dir || '—';
    document.getElementById('hostDirInput').value = data.host_dir || '';
  } catch (e) {
    document.getElementById('serverStatus').textContent = '❌ Error';
    showStatus('Failed to load config: ' + e.message, 'error');
  }
}

document.getElementById('saveBtn').addEventListener('click', async () => {
  const subfolder = document.getElementById('subfolder').value.trim();
  try {
    const resp = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subfolder: subfolder })
    });
    const data = await resp.json();
    if (data.success) {
      showStatus('✅ Save path updated! Files will be saved to: ' + data.save_path, 'success');
      loadConfig();
    } else {
      showStatus('❌ Error: ' + (data.error || 'Unknown error'), 'error');
    }
  } catch (e) {
    showStatus('❌ Failed to save: ' + e.message, 'error');
  }
});

document.getElementById('saveHostDirBtn').addEventListener('click', async () => {
  const hostDir = document.getElementById('hostDirInput').value.trim();
  if (!hostDir) {
    showStatus('Host directory cannot be empty', 'error');
    return;
  }
  if (!confirm('⚠️ Changing host directory requires container restart. Files in the old directory won\'t move automatically. Continue?')) return;
  try {
    const resp = await fetch('/api/host-dir', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host_dir: hostDir })
    });
    const data = await resp.json();
    if (data.success) {
      showStatus('✅ docker-compose.yml updated! Restart the container: docker compose down && docker compose up -d', 'success');
      loadConfig();
    } else {
      showStatus('❌ Error: ' + (data.error || 'Unknown error'), 'error');
    }
  } catch (e) {
    showStatus('❌ Failed: ' + e.message, 'error');
  }
});

document.getElementById('testBtn').addEventListener('click', async () => {
  try {
    const resp = await fetch('/health');
    const data = await resp.json();
    if (data.status === 'ok') {
      showStatus('✅ Server is running! Knowledge base: ' + data.knowledge_base, 'success');
    } else {
      showStatus('❌ Server responded with error', 'error');
    }
  } catch (e) {
    showStatus('❌ Connection failed: ' + e.message, 'error');
  }
});

loadConfig();
</script>
</body>
</html>"""


# ==================== UTILITY FUNCTIONS ====================

def sanitize_filename(name: str) -> str:
    """Clean filename, keep Chinese and common characters"""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'[\s]+', '-', name.strip())
    if len(name) > 80:
        name = name[:80]
    return name.strip('-') or 'untitled'


def count_md_files(path: Path) -> int:
    """Count .md files in directory"""
    try:
        return len(list(path.rglob('*.md')))
    except:
        return 0


def list_directory(path: str) -> dict:
    """List directories for path browser"""
    p = Path(path)
    if not p.exists():
        return {'error': f'Path does not exist: {path}', 'dirs': []}
    if not p.is_dir():
        return {'error': f'Not a directory: {path}', 'dirs': []}
    try:
        dirs = sorted([
            {'name': item.name, 'path': str(item)}
            for item in p.iterdir()
            if item.is_dir() and not item.name.startswith('.')
        ], key=lambda x: x['name'].lower())
        return {'path': str(p), 'parent': str(p.parent), 'dirs': dirs}
    except PermissionError:
        return {'error': f'Permission denied: {path}', 'dirs': []}


COMPOSE_FILE = Path('/app/docker-compose.yml')

def get_host_dir() -> str:
    """Read current host directory from docker-compose.yml"""
    try:
        if COMPOSE_FILE.exists():
            content = COMPOSE_FILE.read_text()
            # Match volume line: - ./something:/data/knowledge-base
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('-') and ':/data/knowledge-base' in line:
                    return line.lstrip('- ').split(':')[0].strip()
    except Exception:
        pass
    return './knowledge-base'


def update_host_dir(new_host_dir: str) -> dict:
    """Update docker-compose.yml host volume mapping. User must restart container."""
    try:
        if not COMPOSE_FILE.exists():
            return {'error': 'docker-compose.yml not found'}
        content = COMPOSE_FILE.read_text()
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('-') and ':/data/knowledge-base' in stripped:
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(f'{indent}- {new_host_dir}:/data/knowledge-base')
            else:
                new_lines.append(line)
        COMPOSE_FILE.write_text('\n'.join(new_lines) + '\n')
        return {'success': True, 'host_dir': new_host_dir, 'restart_required': True}
    except Exception as e:
        return {'error': str(e)}


def convert_html_to_markdown(html: str, url: str, meta: dict = None) -> dict:
    """Convert browser-extracted HTML to Markdown"""
    try:
        if meta is None:
            meta = {}

        content = trafilatura.extract(
            html, url=url, output_format='markdown',
            include_links=True, include_images=True,
            include_tables=True, favor_recall=True
        )

        if not content:
            content = trafilatura.extract(
                html, url=url, output_format='txt',
                include_links=True, include_tables=True, favor_recall=True
            )

        if not content:
            try:
                from readability import Document
                doc = Document(html)
                readable_html = doc.summary()
                content = markdownify.markdownify(readable_html, heading_style='ATX')
                content = re.sub(r'\n{3,}', '\n\n', content).strip()
            except:
                content = markdownify.markdownify(html, heading_style='ATX')
                content = re.sub(r'\n{3,}', '\n\n', content).strip()

        if not content or len(content) < 30:
            return {"error": "Failed to extract content from page"}

        return {
            "content": content,
            "title": meta.get("ogTitle", meta.get("title", "")),
            "author": meta.get("author", ""),
            "date": meta.get("date", ""),
            "description": meta.get("ogDescription", meta.get("description", ""))
        }
    except Exception as e:
        return {"error": f"HTML conversion failed: {str(e)}"}


def fetch_page_content(url: str) -> dict:
    """Fetch and extract web page content"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'
        html = resp.text

        if not html or len(html) < 100:
            return {"error": "Page content is empty"}

        content = trafilatura.extract(
            html, url=url, output_format='markdown',
            include_links=True, include_images=True,
            include_tables=True, favor_recall=True
        )

        if not content:
            content = trafilatura.extract(
                html, url=url, output_format='txt',
                include_links=True, include_tables=True, favor_recall=True
            )

        if not content:
            from readability import Document
            doc = Document(html)
            readable_html = doc.summary()
            content = markdownify.markdownify(readable_html, heading_style='ATX')
            content = re.sub(r'\n{3,}', '\n\n', content).strip()

        if not content or len(content) < 30:
            return {"error": "Failed to extract page content"}

        meta = {}
        metadata = trafilatura.extract(html, url=url, output_format='json', include_links=False)
        if metadata:
            try:
                meta = json.loads(metadata)
            except:
                pass

        if not meta.get("title"):
            import html.parser
            class TitleParser(html.parser.HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._in_title = False
                    self.title = ''
                def handle_starttag(self, tag, attrs):
                    if tag == 'title': self._in_title = True
                def handle_endtag(self, tag):
                    if tag == 'title': self._in_title = False
                def handle_data(self, data):
                    if self._in_title: self.title += data
            try:
                p = TitleParser()
                p.feed(html[:5000])
                if p.title.strip():
                    meta["title"] = p.title.strip()
            except:
                pass

        return {
            "content": content,
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "date": meta.get("date", ""),
            "description": meta.get("description", "")
        }

    except requests.HTTPError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}
    except requests.ConnectionError:
        return {"error": "Cannot connect to target website"}
    except requests.Timeout:
        return {"error": "Request timed out (15 seconds)"}
    except Exception as e:
        return {"error": str(e)}


def localize_image_urls(content: str, save_dir: Path, page_url: str) -> tuple:
    """Download images and replace URLs with local relative paths.
    Returns (updated_content, image_count).
    """
    from urllib.parse import urlparse, urljoin
    img_pattern = re.compile(r'!\[([^\]]*)\]\((https?://[^)]+)\)')
    matches = img_pattern.findall(content)
    if not matches:
        return content, 0

    assets_dir = save_dir / 'assets'
    assets_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    def download_image(match):
        alt, img_url = match
        try:
            # Build absolute URL if relative
            if not img_url.startswith('http'):
                img_url = urljoin(page_url, img_url)

            # Generate filename from URL hash + original extension
            url_hash = hashlib.md5(img_url.encode()).hexdigest()[:10]
            ext = Path(urlparse(img_url).path).suffix or '.jpg'
            # Clean extension
            ext = ext.split('?')[0].lower()
            if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'):
                ext = '.jpg'
            local_name = f"{url_hash}{ext}"
            local_path = assets_dir / local_name

            if not local_path.exists():
                req = urllib.request.Request(img_url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                    # Skip tiny images (likely tracking pixels)
                    if len(data) < 500:
                        return None
                    local_path.write_bytes(data)

            rel_path = f"assets/{local_name}"
            return (f'![{alt}]({img_url})', f'![{alt}]({rel_path})')
        except Exception:
            return None

    # Download images in parallel (max 4 threads)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(download_image, matches))

    for result in results:
        if result:
            old, new = result
            content = content.replace(old, new, 1)
            count += 1

    return content, count


def save_to_knowledge_base(url: str, title: str, content: str,
                           filename: str = None, category: str = None,
                           author: str = "", date: str = "",
                           description: str = "", localize_images: bool = True) -> dict:
    """Save content to knowledge base with YAML frontmatter and optional image localization"""
    kb = get_save_path()
    save_dir = kb
    if category:
        category = sanitize_filename(category)
        save_dir = kb / category
    save_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        fname = sanitize_filename(filename)
    elif title:
        fname = sanitize_filename(title)
    else:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('.', '-')
        fname = sanitize_filename(domain)

    if not fname.endswith('.md'):
        fname += '.md'

    filepath = save_dir / fname

    if filepath.exists():
        ts = datetime.now().strftime('%H%M')
        fname = fname.replace('.md', f'-{ts}.md')
        filepath = save_dir / fname

    # --- P0: Image localization ---
    image_count = 0
    if localize_images:
        content, image_count = localize_image_urls(content, save_dir, url)

    # --- P0: YAML Frontmatter ---
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    safe_title = (title or 'Untitled').replace('"', '\\"')
    safe_author = author.replace('"', '\\"') if author else ''
    safe_desc = description.replace('"', '\\"')[:200] if description else ''

    frontmatter = [
        "---",
        f'title: "{safe_title}"',
        f'source_url: "{url}"',
        f'saved_date: "{now}"',
    ]
    if safe_author:
        frontmatter.append(f'author: "{safe_author}"')
    if date:
        frontmatter.append(f'date: "{date}"')
    if category:
        frontmatter.append(f'category: "{category}"')
    if safe_desc:
        frontmatter.append(f'description: "{safe_desc}"')
    if image_count > 0:
        frontmatter.append(f"images_localized: {image_count}")
    frontmatter.append("---")

    md_lines = frontmatter + ["", f"# {title or 'Untitled'}", "", content]
    filepath.write_text("\n".join(md_lines), encoding='utf-8')

    rel_path = filepath.relative_to(kb)
    return {
        "success": True,
        "saved_path": str(rel_path),
        "full_path": str(filepath)
    }


# ==================== HTTP REQUEST HANDLER ====================

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == '/health':
            self._json_response(200, {
                "status": "ok",
                "service": "Knowledge Base Collector",
                "knowledge_base": str(get_save_path()),
                "port": PORT
            })
        elif self.path == '/api/config':
            config = load_config()
            config['file_count'] = count_md_files(get_save_path())
            config['save_path'] = str(get_save_path())
            config['base_dir'] = str(BASE_DIR)
            config['host_dir'] = get_host_dir()
            self._json_response(200, config)

        elif self.path.startswith('/api/browsable-path'):
            from urllib.parse import urlparse, parse_qs
            query = parse_qs(urlparse(self.path).query)
            path = query.get('path', ['/'])[0]
            self._json_response(200, list_directory(path))
        elif self.path == '/' or self.path == '/settings':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(SETTINGS_HTML.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/config':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                data = json.loads(body)

                subfolder = data.get('subfolder', '').strip()
                # Sanitize: no .. traversal
                subfolder = subfolder.replace('..', '').strip('/')

                config = load_config()
                config['subfolder'] = subfolder
                save_config(config)

                save_path = get_save_path()
                save_path.mkdir(parents=True, exist_ok=True)

                self._json_response(200, {
                    "success": True,
                    "subfolder": subfolder,
                    "save_path": str(save_path),
                    "message": f"Save path updated to {save_path}"
                })
            except Exception as e:
                self._json_response(500, {"success": False, "error": str(e)})

        elif self.path == '/api/host-dir':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                data = json.loads(body)
                host_dir = data.get('host_dir', '').strip()
                if not host_dir:
                    self._json_response(400, {"success": False, "error": "host_dir cannot be empty"})
                    return
                result = update_host_dir(host_dir)
                if 'error' in result:
                    self._json_response(500, {"success": False, "error": result['error']})
                else:
                    self._json_response(200, result)
            except Exception as e:
                self._json_response(500, {"success": False, "error": str(e)})

        elif self.path == '/save':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                data = json.loads(body)

                url = data.get('url', '').strip()
                title = data.get('title', '').strip()
                filename = data.get('filename')
                category = data.get('category')
                browser_html = data.get('html')
                browser_meta = data.get('meta', {})

                if not url:
                    self._json_response(400, {"success": False, "error": "URL cannot be empty"})
                    return

                if browser_html and len(browser_html) > 50:
                    result = convert_html_to_markdown(browser_html, url, browser_meta)
                else:
                    result = fetch_page_content(url)

                if 'error' in result:
                    self._json_response(500, {"success": False, "error": result['error']})
                    return

                if not title:
                    title = result.get('title', 'Untitled')

                save_result = save_to_knowledge_base(
                    url=url, title=title, content=result['content'],
                    filename=filename, category=category,
                    author=result.get('author', ''), date=result.get('date', ''),
                    description=result.get('description', '')
                )

                self._json_response(200, save_result)
            except Exception as e:
                self._json_response(500, {"success": False, "error": str(e)})
        else:
            self.send_response(404)
            self.end_headers()

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, format, *args):
        now = datetime.now().strftime('%H:%M:%S')
        print(f"[{now}] {args[0]}")


def main():
    from http.server import ThreadingHTTPServer
    server = ThreadingHTTPServer(('0.0.0.0', PORT), RequestHandler)
    print(f"📚 Knowledge Base Collector started")
    print(f"   Port: {PORT}")
    print(f"   Knowledge base: {get_save_path()}")
    print(f"   Settings page: http://localhost:{PORT}/")
    print(f"   Health check: http://localhost:{PORT}/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server.server_close()


if __name__ == '__main__':
    main()
