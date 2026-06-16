const DEFAULT_SERVER = 'http://localhost:8396';

// 从 storage 获取服务器地址
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

// 设置按钮
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
  btn.textContent = '⏳ 保存中...';
  status.className = 'status loading';
  status.textContent = '正在从浏览器提取页面内容...';

  try {
    let payload = {
      url: tab.url,
      title: tab.title || '',
      filename: filename || null,
      category: category || null
    };

    // 浏览器端提取内容（绕过 WAF）
    try {
      const extracted = await new Promise((resolve, reject) => {
        chrome.tabs.sendMessage(tab.id, { action: 'extractContent' }, (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else if (response && response.success) {
            resolve(response);
          } else {
            reject(new Error(response?.error || '提取失败'));
          }
        });
      });

      status.textContent = '正在转换为 Markdown...';
      payload.html = extracted.html;
      payload.meta = extracted.meta || {};
    } catch (e) {
      console.log('Content script 不可用，使用服务端抓取:', e.message);
      status.textContent = '正在由服务端抓取页面...';
    }

    const resp = await fetch(`${SERVER_URL}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await resp.json();

    if (data.success) {
      status.className = 'status success';
      status.textContent = `✅ 已保存: ${data.saved_path}`;
      btn.textContent = '✅ 保存成功';
      setTimeout(() => {
        btn.disabled = false;
        btn.textContent = '💾 保存到知识库';
      }, 3000);
    } else {
      throw new Error(data.error || '保存失败');
    }
  } catch (err) {
    status.className = 'status error';
    status.textContent = `❌ 错误: ${err.message}`;
    btn.disabled = false;
    btn.textContent = '💾 重试';
  }
});
