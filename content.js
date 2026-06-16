// 知识库收藏 - Content Script
// 在当前页面提取正文 HTML，返回给 popup

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'extractContent') {
    try {
      // 尝试用 Readability 提取正文
      const docClone = document.cloneNode(true);

      // 提取正文区域的几种常见选择器
      let contentHtml = '';

      // 优先尝试常见的正文容器
      const selectors = [
        'article',
        '.post-content',
        '.article-content',
        '.entry-content',
        '.content',
        '.post-body',
        '#content',
        '.t_f',           // Chiphell 帖子正文
        '.t_msgfontfix',   // Chiphell 备选
        'main',
        '.main-content'
      ];

      for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el && el.innerText.trim().length > 100) {
          contentHtml = el.innerHTML;
          break;
        }
      }

      // fallback: 用 body
      if (!contentHtml) {
        contentHtml = document.body.innerHTML;
      }

      // 获取 meta 信息
      const meta = {};
      const metaTags = document.querySelectorAll('meta');
      metaTags.forEach(m => {
        if (m.name === 'author') meta.author = m.content;
        if (m.name === 'description') meta.description = m.content;
        if (m.property === 'og:title') meta.ogTitle = m.content;
        if (m.property === 'og:description') meta.ogDescription = m.content;
      });

      // 获取发布时间
      const timeEl = document.querySelector('time, .publish-date, .post-date, [datetime]');
      if (timeEl) {
        meta.date = timeEl.getAttribute('datetime') || timeEl.textContent.trim();
      }

      sendResponse({
        success: true,
        html: contentHtml,
        title: document.title,
        url: window.location.href,
        meta: meta
      });
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
  }
  return true; // 异步响应
});
