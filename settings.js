const DEFAULT_SERVER = 'http://localhost:8396';
const status = document.getElementById('status');

// 加载已保存的设置
chrome.storage.sync.get(['serverUrl'], (result) => {
  document.getElementById('serverUrl').value = result.serverUrl || DEFAULT_SERVER;
});

// 返回
document.getElementById('backBtn').addEventListener('click', () => {
  window.location.href = 'popup.html';
});

// 测试连接
document.getElementById('testBtn').addEventListener('click', async () => {
  const url = document.getElementById('serverUrl').value.trim().replace(/\/+$/, '');
  status.className = 'status loading';
  status.textContent = '正在测试连接...';

  try {
    const resp = await fetch(`${url}/health`, { signal: AbortSignal.timeout(5000) });
    const data = await resp.json();
    if (data.status === 'ok') {
      status.className = 'status success';
      status.textContent = `✅ 连接成功！服务正常运行`;
    } else {
      throw new Error('服务响应异常');
    }
  } catch (err) {
    status.className = 'status error';
    status.textContent = `❌ 连接失败: ${err.message}`;
  }
});

// 保存设置
document.getElementById('saveBtn').addEventListener('click', () => {
  const url = document.getElementById('serverUrl').value.trim().replace(/\/+$/, '');
  if (!url) {
    status.className = 'status error';
    status.textContent = '❌ 服务器地址不能为空';
    return;
  }
  chrome.storage.sync.set({ serverUrl: url }, () => {
    status.className = 'status success';
    status.textContent = '✅ 设置已保存';
    setTimeout(() => { status.style.display = 'none'; }, 2000);
  });
});
