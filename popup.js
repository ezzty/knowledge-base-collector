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

    // Browser-side content extraction (bypasses WAF)
    try {
      const extracted = await new Promise((resolve, reject) => {
        chrome.tabs.sendMessage(tab.id, { action: 'extractContent' }, (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else if (response && response.success) {
            resolve(response);
          } else {
            reject(new Error(response?.error || 'Extraction failed'));
          }
        });
      });

      status.textContent = 'Converting to Markdown...';
      payload.html = extracted.html;
      payload.meta = extracted.meta || {};
    } catch (e) {
      console.log('Content script unavailable, using server-side fetch:', e.message);
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
        btn.textContent = '💾 Save to Knowledge Base';
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
