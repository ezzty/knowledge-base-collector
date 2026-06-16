const DEFAULT_SERVER = 'http://localhost:8396';
const status = document.getElementById('status');

// Load saved settings
chrome.storage.sync.get(['serverUrl'], (result) => {
  document.getElementById('serverUrl').value = result.serverUrl || DEFAULT_SERVER;
});

// Back button
document.getElementById('backBtn').addEventListener('click', () => {
  window.location.href = 'popup.html';
});

// Test connection
document.getElementById('testBtn').addEventListener('click', async () => {
  const url = document.getElementById('serverUrl').value.trim().replace(/\/+$/, '');
  status.className = 'status loading';
  status.textContent = 'Testing connection...';

  try {
    const resp = await fetch(`${url}/health`, { signal: AbortSignal.timeout(5000) });
    const data = await resp.json();
    if (data.status === 'ok') {
      status.className = 'status success';
      status.textContent = '✅ Connection successful! Server is running.';
    } else {
      throw new Error('Unexpected server response');
    }
  } catch (err) {
    status.className = 'status error';
    status.textContent = `❌ Connection failed: ${err.message}`;
  }
});

// Save settings
document.getElementById('saveBtn').addEventListener('click', () => {
  const url = document.getElementById('serverUrl').value.trim().replace(/\/+$/, '');
  if (!url) {
    status.className = 'status error';
    status.textContent = '❌ Server address cannot be empty';
    return;
  }
  chrome.storage.sync.set({ serverUrl: url }, () => {
    status.className = 'status success';
    status.textContent = '✅ Settings saved';
    setTimeout(() => { status.style.display = 'none'; }, 2000);
  });
});
