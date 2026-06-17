// 知识库收藏 - Content Script（已优化小红书支持）
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extractContent') {
    try {
      const hostname = window.location.hostname;
      
      // ==================== 小红书专用 ====================
      if (hostname.includes('xiaohongshu.com') || hostname.includes('xhs.cn')) {
        extractXiaohongshu().then(sendResponse);
        return true; // 异步响应
      }

      // ==================== 通用逻辑（保持不变）===================
      let contentHtml = '';

      const selectors = [
        'article', '.post-content', '.article-content', '.entry-content',
        '.content', '.post-body', '#content', '.t_f', '.t_msgfontfix',
        'main', '.main-content'
      ];

      for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el && el.innerText.trim().length > 100) {
          contentHtml = el.innerHTML;
          break;
        }
      }

      if (!contentHtml) contentHtml = document.body.innerHTML;

      const meta = extractMeta();
      sendResponse({ success: true, html: contentHtml, title: document.title, url: window.location.href, meta: meta });
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
  }
  return true;
});

// 小红书专用提取函数
async function extractXiaohongshu() {
  // 等待页面加载（小红书笔记经常需要时间）
  await new Promise(r => setTimeout(r, 2000));

  let contentHtml = '';
  const xhsSelectors = [
    '.note-content', '.content', '.desc', '.rich-text',
    '.note-text', 'article', '.detail-desc', '[class*="content"]'
  ];

  for (const sel of xhsSelectors) {
    const els = document.querySelectorAll(sel);
    for (const el of els) {
      const text = el.innerText.trim();
      if (text.length > 150) {
        // 清理无关区域
        el.querySelectorAll('.bottom-bar, .comments, .recommend, .interact, .footer, .note-bottom').forEach(e => e.remove());
        contentHtml = el.innerHTML;
        break;
      }
    }
    if (contentHtml) break;
  }

  // 兜底方案
  if (!contentHtml) {
    const main = document.querySelector('main') || document.querySelector('.app') || document.body;
    contentHtml = main.innerHTML;
  }

  const meta = extractMeta();
  meta.site_type = 'xhs';   // 传递给后端

  return {
    success: true,
    html: contentHtml,
    title: document.title.replace(/ - 小红书.*/, '').replace(/ - xiaohongshu.*/, ''),
    url: window.location.href,
    meta: meta
  };
}

function extractMeta() {
  const meta = {};
  document.querySelectorAll('meta').forEach(m => {
    if (m.name === 'author') meta.author = m.content;
    if (m.name === 'description') meta.description = m.content;
    if (m.property === 'og:title') meta.ogTitle = m.content;
    if (m.property === 'og:description') meta.ogDescription = m.content;
  });

  const timeEl = document.querySelector('time, .publish-date, .post-date');
  if (timeEl) meta.date = timeEl.textContent.trim();

  // 小红书图片提取（适配弹出窗口）
  const hostname = window.location.hostname;
  if (hostname.includes('xiaohongshu.com') || hostname.includes('xhs.cn')) {
    meta.site_type = 'xhs';
    const images = [];
    const xhsImageSelectors = [
      '.note-content', '.note-container', '.content', '.desc',
      '.rich-text', '.note-text', '.swiper-wrapper', '.media-container',
      '.note-slider', '.image-container', 'article', 'main'
    ];

    xhsImageSelectors.forEach(selector => {
      document.querySelectorAll(selector).forEach(container => {
        container.querySelectorAll('img').forEach(img => {
          const src = img.src || img.dataset.src || img.dataset.original || img.getAttribute('data-lazy-src');
          if (src &&
              !src.includes('data:image') &&
              !src.includes('avatar') &&
              !src.includes('icon') &&
              src.length > 30) {
            images.push(src);
          }
        });

        // 提取背景图片
        container.querySelectorAll('[style*="background-image"]').forEach(el => {
          const style = el.getAttribute('style') || '';
          const match = style.match(/url\(["']?([^"')]+)["']?\)/);
          if (match && match[1] && !match[1].includes('avatar')) {
            images.push(match[1]);
          }
        });
      });
    });

    meta.images = [...new Set(images)];
  }

  // 微信公众号图片提取
  if (hostname.includes('mp.weixin.qq.com')) {
    meta.site_type = 'wechat';
    const images = [];
    const contentEl = document.querySelector('#js_content') || document.querySelector('.rich_media_content');
    
    if (contentEl) {
      contentEl.querySelectorAll('img').forEach(img => {
        let src = img.getAttribute('data-src') || img.dataset.src || img.src;
        if (src && src.includes('mmbiz.qpic.cn')) {
          if (src.includes('?')) src = src.split('?')[0];
          src = src + '?wx_fmt=png';
          images.push(src);
        }
      });
    }
    meta.images = [...new Set(images)];
  }

  // Reddit 图片提取
  if (hostname.includes('reddit.com') || hostname.includes('redd.it')) {
    meta.site_type = 'reddit';
    const images = [];
    const redditImgSelectors = [
      'img[alt*="Post image"]',
      'shreddit-post img',
      '[data-testid="post-content"] img',
      'figure img',
      'img[src*="i.redd.it"]',
      'img[src*="preview.redd.it"]'
    ];
    
    redditImgSelectors.forEach(selector => {
      document.querySelectorAll(selector).forEach(img => {
        const src = img.src || img.dataset.src;
        if (src && 
            src.includes('redd.it') &&
            !src.includes('avatar') && 
            !src.includes('icon')) {
          images.push(src);
        }
      });
    });
    
    meta.images = [...new Set(images)];
  }

  return meta;
}
