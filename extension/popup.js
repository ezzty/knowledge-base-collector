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
  const selectors = [
    'article', '.post-content', '.article-content', '.entry-content',
    '.content', '.post-body', '#content', '.t_f', '.t_msgfontfix',
    'main', '.main-content'
  ];

  let contentHtml = '';
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText.trim().length > 100) {
      contentHtml = el.innerHTML;
      break;
    }
  }
  if (!contentHtml) {
    contentHtml = document.body.innerHTML;
  }

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

  return {
    success: true,
    html: contentHtml,
    title: document.title,
    url: window.location.href,
    meta: meta
  };
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
