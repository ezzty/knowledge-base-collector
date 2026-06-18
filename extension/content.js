// 知识库收藏 - Content Script（v2.1 优化版）
// 参考 Jina Reader 思路 + 更健壮的提取逻辑

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extractContent') {
    extractPageContent().then(sendResponse);
    return true;
  }
  return true;
});

async function extractPageContent() {
  const hostname = window.location.hostname.toLowerCase();
  const url = window.location.href;

  try {
    // 等待页面稳定
    await new Promise(r => setTimeout(r, 600));

    let result;

    if (hostname.includes('xiaohongshu.com') || hostname.includes('xhs.cn')) {
      result = await extractXiaohongshu();
    } else if (hostname.includes('mp.weixin.qq.com')) {
      result = await extractWechat();
    } else if (hostname.includes('reddit.com') || hostname.includes('redd.it')) {
      result = await extractReddit();
    } else if (hostname.includes('v2ex.com')) {
      result = await extractV2EX();
    } else {
      result = await extractGeneric();
    }

    // 全局懒加载图片修复
    result.html = fixLazyImages(result.html);

    // 合并 meta
    const baseMeta = extractBaseMeta();
    const finalMeta = { ...baseMeta, ...(result.meta || {}) };

    // 站点类型标记
    if (!finalMeta.site_type) {
      finalMeta.site_type = detectSiteType(hostname);
    }

    return {
      success: true,
      html: result.html,
      title: cleanTitle(result.title || document.title, hostname),
      url: url,
      meta: finalMeta
    };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

// ==================== 通用提取 ====================
async function extractGeneric() {
  const noiseSelectors = [
    '.comment', '.comments', '.recommend', '.related',
    '.ad', '.ads', '.advertisement', '[class*="ad-"]',
    '.cookie', '.cookie-banner', '.modal', '.popup',
    '.share', '.social-share', '.toolbar',
    '.author-info', '.meta', '.tags', '.tag-list',
    'script', 'style', 'noscript', 'iframe'
  ];

  const contentSelectors = [
    'article',
    '[role="main"]',
    'main',
    '.post-content', '.article-content', '.entry-content',
    '.content', '.post-body', '#content',
    '.markdown-body', '.topic-content',
    '.rich_media_content', '#js_content'
  ];

  let contentEl = null;
  for (const selector of contentSelectors) {
    const el = document.querySelector(selector);
    if (el && el.innerText.trim().length > 120) {
      contentEl = el;
      break;
    }
  }

  if (!contentEl) {
    contentEl = document.body;
  }

  const clone = contentEl.cloneNode(true);
  cleanNoiseElements(clone, noiseSelectors);

  return {
    html: clone.innerHTML,
    title: document.title
  };
}

// ==================== 小红书 ====================
async function extractXiaohongshu() {
  await new Promise(r => setTimeout(r, 1200));

  const selectors = [
    '.note-content', '.desc', '.rich-text', '.note-text',
    '.detail-desc', 'article', '.content'
  ];

  let contentEl = null;
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText.trim().length > 80) {
      contentEl = el;
      break;
    }
  }

  if (!contentEl) {
    contentEl = document.querySelector('main') || document.body;
  }

  const clone = contentEl.cloneNode(true);
  cleanNoiseElements(clone, [
    '.bottom-bar', '.comments', '.recommend', '.interact',
    '.note-bottom', '.share'
  ]);

  return {
    html: clone.innerHTML,
    title: document.title,
    meta: { site_type: 'xhs' }
  };
}

// ==================== 微信公众号 ====================
async function extractWechat() {
  const contentEl = document.querySelector('#js_content') ||
                   document.querySelector('.rich_media_content') ||
                   document.body;

  const clone = contentEl.cloneNode(true);
  cleanNoiseElements(clone, [
    '.qr_code_pc', '.tips', '.original_area', '.share_area'
  ]);

  // 微信图片特殊处理
  clone.querySelectorAll('img').forEach(img => {
    let src = img.getAttribute('data-src') || img.src;
    if (src && src.includes('mmbiz.qpic.cn')) {
      src = src.split('?')[0] + '?wx_fmt=png';
      img.src = src;
    }
  });

  return {
    html: clone.innerHTML,
    title: document.title,
    meta: { site_type: 'wechat' }
  };
}

// ==================== Reddit ====================
async function extractReddit() {
  const selectors = [
    '[data-testid="post-content"]',
    '.Post',
    'article',
    '.usertext-body'
  ];

  let contentEl = null;
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText.trim().length > 60) {
      contentEl = el;
      break;
    }
  }

  if (!contentEl) contentEl = document.body;

  const clone = contentEl.cloneNode(true);
  cleanNoiseElements(clone, ['.comment', '.comments', '.sidebar']);

  return {
    html: clone.innerHTML,
    title: document.title,
    meta: { site_type: 'reddit' }
  };
}

// ==================== V2EX ====================
async function extractV2EX() {
  const selectors = [
    '#Main .box .cell .topic_content',
    '#Main .box .cell .markdown_body',
    '.topic_content'
  ];

  let contentEl = null;
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText.trim().length > 30) {
      contentEl = el;
      break;
    }
  }

  if (!contentEl) contentEl = document.body;

  const clone = contentEl.cloneNode(true);

  return {
    html: clone.innerHTML,
    title: document.title,
    meta: { site_type: 'v2ex' }
  };
}

// ==================== 工具函数 ====================

function cleanNoiseElements(root, selectors) {
  selectors.forEach(selector => {
    root.querySelectorAll(selector).forEach(el => el.remove());
  });
}

function fixLazyImages(html) {
  const temp = document.createElement('div');
  temp.innerHTML = html;

  temp.querySelectorAll('img').forEach(img => {
    const realSrc = img.getAttribute('data-src') ||
                    img.getAttribute('data-original') ||
                    img.getAttribute('data-lazy-src') ||
                    img.getAttribute('data-url') ||
                    img.src;

    if (realSrc && realSrc.length > 10 && !realSrc.startsWith('data:')) {
      img.src = realSrc;
    }

    img.removeAttribute('data-src');
    img.removeAttribute('data-original');
    img.removeAttribute('data-lazy-src');
    img.removeAttribute('loading');
  });

  return temp.innerHTML;
}

function extractBaseMeta() {
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
  return meta;
}

function detectSiteType(hostname) {
  if (hostname.includes('xiaohongshu.com') || hostname.includes('xhs.cn')) return 'xhs';
  if (hostname.includes('mp.weixin.qq.com')) return 'wechat';
  if (hostname.includes('reddit.com') || hostname.includes('redd.it')) return 'reddit';
  if (hostname.includes('v2ex.com')) return 'v2ex';
  return 'general';
}

function cleanTitle(title, hostname) {
  let t = title.trim();

  if (hostname.includes('xiaohongshu.com') || hostname.includes('xhs.cn')) {
    t = t.replace(/ - 小红书.*/, '').replace(/ - xiaohongshu.*/, '');
  } else if (hostname.includes('mp.weixin.qq.com')) {
    t = t.replace(/ - 微信公众号.*/, '');
  } else if (hostname.includes('v2ex.com')) {
    t = t.replace(/ - V2EX.*/, '');
  } else if (hostname.includes('reddit.com')) {
    t = t.replace(/ : r\/.*/, '');
  }

  return t;
}
