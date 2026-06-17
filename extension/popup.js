const DEFAULT_SERVER = 'http://localhost:8396';

// Get server URL from storage
async function getServerUrl() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(['serverUrl'], (result) => {
      resolve((result.serverUrl || DEFAULT_SERVER).replace(/\/+$/, ''));
    });
  });
}

// Get current tab info
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const tab = tabs[0];
  document.getElementById('pageTitle').textContent = tab.title || 'Untitled';
  document.getElementById('pageUrl').textContent = tab.url;
});

// Settings button
document.getElementById('settingsBtn').addEventListener('click', () => {
  window.location.href = 'settings.html';
});

// Content extraction function (injected into the page)
function extractPageContent() {
  return new Promise((resolve) => {
    const hostname = window.location.hostname;
    const isXHS = hostname.includes('xiaohongshu.com') || hostname.includes('xhs.cn');
    const isReddit = hostname.includes('reddit.com') || hostname.includes('redd.it');
    const isV2EX = hostname.includes('v2ex.com');
    const isWechat = hostname.includes('mp.weixin.qq.com');

    // 小红书专用选择器
    const xhsSelectors = [
      '.note-content', '.content', '.desc', '.rich-text',
      '.note-text', 'article', '.detail-desc', '[class*="content"]'
    ];

    // Reddit 专用选择器
    const redditSelectors = [
      '[data-testid="post-content"]',
      '.Post',
      'article',
      '.usertext-body',
      '[data-click-id="text"]',
      '.md'
    ];

    // V2EX 专用选择器（只抓主帖）
    const v2exSelectors = [
      '#Main .box .cell .topic_content',
      '#Main .box .cell .markdown_body',
      '.topic_content',
      '#Main .markdown_body'
    ];

    // 微信公众号专用选择器
    const wechatSelectors = [
      '#js_content',
      '.rich_media_content',
      '#content'
    ];

    // 通用选择器
    const genericSelectors = [
      'article', '.post-content', '.article-content', '.entry-content',
      '.content', '.post-body', '#content', '.t_f', '.t_msgfontfix',
      'main', '.main-content'
    ];

    function tryExtract() {
      const selectors = isXHS ? xhsSelectors : 
                     (isWechat ? wechatSelectors : 
                     (isV2EX ? v2exSelectors : genericSelectors));
      const minLength = isXHS ? 50 : 100;

      let contentHtml = '';
      for (const sel of selectors) {
        const els = document.querySelectorAll(sel);
        for (const el of els) {
          const text = el.innerText.trim();
          if (text.length > minLength) {
            // 小红书清理无关区域
            if (isXHS) {
              el.querySelectorAll('.bottom-bar, .comments, .recommend, .interact, .footer, .note-bottom').forEach(e => e.remove());
            }
            contentHtml = el.innerHTML;
            break;
          }
        }
        if (contentHtml) break;
      }

      if (!contentHtml && !isXHS) {
        contentHtml = document.body.innerHTML;
      }

      return contentHtml;
    }

    // 小红书等待内容加载
    if (isXHS) {
      let attempts = 0;
      const maxAttempts = 10;
      const checkInterval = setInterval(() => {
        attempts++;
        const content = tryExtract();
        if (content || attempts >= maxAttempts) {
          clearInterval(checkInterval);
          resolve(buildResponse(content || document.body.innerHTML, isXHS));
        }
      }, 500);
    } else {
      resolve(buildResponse(tryExtract() || document.body.innerHTML, false));
    }

    function buildResponse(contentHtml, isXHS) {
      const meta = {};
      document.querySelectorAll('meta').forEach(m => {
        if (m.name === 'author') meta.author = m.content;
        if (m.name === 'description') meta.description = m.content;
        if (m.property === 'og:title') meta.ogTitle = m.content;
        if (m.property === 'og:description') meta.ogDescription = m.content;
      });

      const timeEl = document.querySelector('time, .publish-date, .post-date, [datetime]');
      if (timeEl) {
        meta.date = timeEl.getAttribute('datetime') || timeEl.textContent.trim();
      }

      if (isXHS) {
        meta.site_type = 'xhs';
        // 提取图片（适配弹出窗口 / 弹层）
        const images = [];
        const xhsImageSelectors = [
          '.note-content', '.note-container', '.content', '.desc',
          '.rich-text', '.note-text', '.swiper-wrapper', '.media-container',
          '.note-slider', '.image-container', 'article'
        ];

        xhsImageSelectors.forEach(selector => {
          const containers = document.querySelectorAll(selector);
          containers.forEach(container => {
            // 提取 <img> 标签
            container.querySelectorAll('img').forEach(img => {
              const src = img.src || img.dataset.src || img.dataset.original || img.getAttribute('data-lazy-src');
              if (src &&
                  !src.includes('data:image') &&
                  !src.includes('avatar') &&
                  !src.includes('icon') &&
                  !src.includes('logo') &&
                  src.length > 30) {
                images.push(src);
              }
            });

            // 提取 style 中的 background-image
            container.querySelectorAll('[style*="background-image"]').forEach(el => {
              const style = el.getAttribute('style') || '';
              const match = style.match(/url\(["']?([^"')]+)["']?\)/);
              if (match && match[1] && !match[1].includes('avatar')) {
                images.push(match[1]);
              }
            });
          });
        });

        meta.images = [...new Set(images)]; // 去重
      } else if (isWechat) {
        meta.site_type = 'wechat';
        // 微信公众号图片提取（加强 data-src 处理）
        const images = [];
        const contentEl = document.querySelector('#js_content') || document.querySelector('.rich_media_content');
        
        if (contentEl) {
          // 先等待图片加载
          contentEl.querySelectorAll('img').forEach(img => {
            let src = img.getAttribute('data-src') || img.dataset.src || img.src;
            
            if (src && src.includes('mmbiz.qpic.cn')) {
              // 去掉微信图片的裁剪参数，获取更清晰的图片
              if (src.includes('?')) {
                src = src.split('?')[0];
              }
              // 添加微信高清参数
              src = src + '?wx_fmt=png&tp=webp&wxfrom=5&wx_lazy=1';
              images.push(src);
            }
          });
        }
        meta.images = [...new Set(images)];
      } else if (isV2EX) {
        meta.site_type = 'v2ex';
        // V2EX 图片提取
        const images = [];
        document.querySelectorAll('#Main img, .topic_content img, .markdown_body img').forEach(img => {
          const src = img.src || img.dataset.src;
          if (src && !src.includes('avatar') && !src.includes('icon')) {
            images.push(src);
          }
        });
        meta.images = [...new Set(images)];
      } else if (isReddit) {
        meta.site_type = 'reddit';
        meta.site_type = 'reddit';
        const images = [];
        
        // Reddit 图片提取 - 更宽松的策略
        // 1. 先尝试特定选择器
        const redditImgSelectors = [
          'shreddit-post img',
          '[data-testid="post-content"] img',
          'img[src*="i.redd.it"]',
          'img[src*="preview.redd.it"]',
          'figure img'
        ];
        
        redditImgSelectors.forEach(selector => {
          document.querySelectorAll(selector).forEach(img => {
            let src = img.src || img.dataset.src || img.getAttribute('data-lazy-src');
            if (src && src.includes('redd.it') && !src.includes('avatar')) {
              images.push(src);
            }
          });
        });
        
        // 2. 如果上面没抓到，兜底抓取页面中所有 reddit 图片
        if (images.length === 0) {
          document.querySelectorAll('img').forEach(img => {
            const src = img.src || img.dataset.src;
            if (src && 
                src.includes('redd.it') && 
                !src.includes('avatar') && 
                !src.includes('icon') &&
                (img.naturalWidth > 100 || img.width > 100)) {
              images.push(src);
            }
          });
        }
        
        meta.images = [...new Set(images)];
      }

      return {
        success: true,
        html: contentHtml,
        title: document.title,
        url: window.location.href,
        meta: meta
      };
    }
  });
}

// Save button
document.getElementById('saveBtn').addEventListener('click', async () => {
  const btn = document.getElementById('saveBtn');
  const status = document.getElementById('status');
  const filename = document.getElementById('filename').value.trim();
  const category = document.getElementById('category').value.trim();

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const SERVER_URL = await getServerUrl();

  btn.disabled = true;
  btn.textContent = '⏳ Saving...';
  status.className = 'status loading';
  status.textContent = 'Extracting page content from browser...';

  try {
    let payload = {
      url: tab.url,
      title: tab.title || '',
      filename: filename || null,
      category: category || null
    };

    // Browser-side content extraction using chrome.scripting (activeTab)
    try {
      const [result] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: extractPageContent
      });

      if (result?.result?.success) {
        status.textContent = 'Converting to Markdown...';
        payload.html = result.result.html;
        payload.meta = result.result.meta || {};
        if (result.result.meta?.site_type) {
          payload.site_type = result.result.meta.site_type;
        }
      } else {
        throw new Error(result?.result?.error || 'Extraction failed');
      }
    } catch (e) {
      console.log('Content extraction unavailable, using server-side fetch:', e.message);
      status.textContent = 'Fetching page from server...';
    }

    const resp = await fetch(`${SERVER_URL}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await resp.json();

    if (data.success) {
      status.className = 'status success';
      status.textContent = `✅ Saved: ${data.saved_path}`;
      btn.textContent = '✅ Saved!';
      setTimeout(() => {
        btn.disabled = false;
        btn.textContent = '💾 Save to Markdown';
      }, 3000);
    } else {
      throw new Error(data.error || 'Save failed');
    }
  } catch (err) {
    status.className = 'status error';
    status.textContent = `❌ Error: ${err.message}`;
    btn.disabled = false;
    btn.textContent = '💾 Retry';
  }
});
