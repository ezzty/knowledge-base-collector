#!/usr/bin/env python3
"""
Knowledge Base Collector Server - Receives web page URLs from the Chrome extension,
fetches content, converts to Markdown, and saves to the knowledge base directory.

Port: 8396
Knowledge base: /data/knowledge-base/ (configurable via KB_DIR env var)
"""

import http.server
import json
import os
import re
import subprocess
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

import requests
import markdownify
import trafilatura

PORT = int(os.environ.get('KB_PORT', 8396))
KNOWLEDGE_BASE = Path(os.environ.get('KB_DIR', '/data/knowledge-base'))

# 浏览器请求头，绕过反爬
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}


def sanitize_filename(name: str) -> str:
    """清理文件名，保留中文和常见字符"""
    # 移除文件系统不允许的字符
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # 把连续空格/特殊字符替换为 -
    name = re.sub(r'[\s]+', '-', name.strip())
    # 截断过长的文件名
    if len(name) > 80:
        name = name[:80]
    # 去掉首尾的 -
    return name.strip('-') or 'untitled'


def convert_html_to_markdown(html: str, url: str, meta: dict = None) -> dict:
    """把浏览器端提取的 HTML 转换为 Markdown"""
    try:
        if meta is None:
            meta = {}

        # 用 trafilatura 提取
        content = trafilatura.extract(
            html,
            url=url,
            output_format='markdown',
            include_links=True,
            include_images=False,
            include_tables=True,
            favor_recall=True
        )

        # fallback: trafilatura 纯文本
        if not content:
            content = trafilatura.extract(
                html,
                url=url,
                output_format='txt',
                include_links=True,
                include_tables=True,
                favor_recall=True
            )

        # fallback: readability + markdownify
        if not content:
            try:
                from readability import Document
                doc = Document(html)
                readable_html = doc.summary()
                content = markdownify.markdownify(readable_html, heading_style='ATX')
                content = re.sub(r'\n{3,}', '\n\n', content).strip()
            except:
                # 最后手段：直接 markdownify
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
    """抓取网页并提取正文内容"""
    try:
        # 用 requests 带浏览器 headers 下载，绕过反爬
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'
        html = resp.text

        if not html or len(html) < 100:
            return {"error": "Page content is empty"}

        # 用 trafilatura 从 HTML 提取正文为 Markdown
        content = trafilatura.extract(
            html,
            url=url,
            output_format='markdown',
            include_links=True,
            include_images=False,
            include_tables=True,
            favor_recall=True
        )

        # fallback: 尝试纯文本模式
        if not content:
            content = trafilatura.extract(
                html,
                url=url,
                output_format='txt',
                include_links=True,
                include_tables=True,
                favor_recall=True
            )

        # fallback: 用 markdownify 直接转换
        if not content:
            from readability import Document
            doc = Document(html)
            readable_html = doc.summary()
            content = markdownify.markdownify(readable_html, heading_style='ATX')
            # 清理多余空行
            content = re.sub(r'\n{3,}', '\n\n', content).strip()

        if not content or len(content) < 30:
            return {"error": "Failed to extract page content"}

        # 提取元信息
        meta = {}
        metadata = trafilatura.extract(
            html,
            url=url,
            output_format='json',
            include_links=False
        )
        if metadata:
            try:
                meta = json.loads(metadata)
            except:
                pass

        # 如果没提取到标题，从 HTML 的 title 标签获取
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


def save_to_knowledge_base(url: str, title: str, content: str,
                           filename: str = None, category: str = None,
                           author: str = "", date: str = "") -> dict:
    """保存内容到知识库"""
    # 确定保存目录
    save_dir = KNOWLEDGE_BASE
    if category:
        category = sanitize_filename(category)
        save_dir = KNOWLEDGE_BASE / category
    save_dir.mkdir(parents=True, exist_ok=True)

    # 确定文件名
    if filename:
        fname = sanitize_filename(filename)
    elif title:
        fname = sanitize_filename(title)
    else:
        # 用 URL 的域名作为文件名
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('.', '-')
        fname = sanitize_filename(domain)

    # 确保 .md 后缀
    if not fname.endswith('.md'):
        fname += '.md'

    filepath = save_dir / fname

    # 如果文件已存在，加时间戳
    if filepath.exists():
        ts = datetime.now().strftime('%H%M')
        fname = fname.replace('.md', f'-{ts}.md')
        filepath = save_dir / fname

    # 构建 Markdown 文档
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    md_lines = []
    md_lines.append(f"# {title or 'Untitled'}")
    md_lines.append("")
    md_lines.append(f"> 来源: [{url}]({url})")
    if author:
        md_lines.append(f"> 作者: {author}")
    if date:
        md_lines.append(f"> 发布日期: {date}")
    md_lines.append(f"> 收藏时间: {now}")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append(content)

    md_content = "\n".join(md_lines)

    # 写入文件
    filepath.write_text(md_content, encoding='utf-8')

    # 返回相对路径
    rel_path = filepath.relative_to(KNOWLEDGE_BASE)
    return {
        "success": True,
        "saved_path": str(rel_path),
        "full_path": str(filepath)
    }


class RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        """健康检查"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "service": "Knowledge Base Collector",
                "knowledge_base": str(KNOWLEDGE_BASE)
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """处理保存请求"""
        if self.path != '/save':
            self.send_response(404)
            self.end_headers()
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            url = data.get('url', '').strip()
            title = data.get('title', '').strip()
            filename = data.get('filename')
            category = data.get('category')
            browser_html = data.get('html')  # 浏览器端提取的 HTML
            browser_meta = data.get('meta', {})  # 浏览器端提取的 meta

            if not url:
                self._json_response(400, {"success": False, "error": "URL cannot be empty"})
                return

            # 如果浏览器端已经提取了 HTML，直接用服务端转换
            if browser_html and len(browser_html) > 50:
                result = convert_html_to_markdown(browser_html, url, browser_meta)
            else:
                # 否则由服务端抓取
                result = fetch_page_content(url)

            if 'error' in result:
                self._json_response(500, {"success": False, "error": result['error']})
                return

            # 用抓取到的标题，如果用户没传标题的话
            if not title:
                title = result.get('title', 'Untitled')

            # 保存到知识库
            save_result = save_to_knowledge_base(
                url=url,
                title=title,
                content=result['content'],
                filename=filename,
                category=category,
                author=result.get('author', ''),
                date=result.get('date', '')
            )

            self._json_response(200, save_result)

        except Exception as e:
            self._json_response(500, {"success": False, "error": str(e)})

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
        """自定义日志格式"""
        now = datetime.now().strftime('%H:%M:%S')
        print(f"[{now}] {args[0]}")


def main():
    from http.server import ThreadingHTTPServer
    server = ThreadingHTTPServer(('0.0.0.0', PORT), RequestHandler)
    print(f"📚 Knowledge Base Collector started")
    print(f"   Port: {PORT}")
    print(f"   Knowledge base: {KNOWLEDGE_BASE}")
    print(f"   Health check: http://localhost:{PORT}/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server.server_close()


if __name__ == '__main__':
    main()
