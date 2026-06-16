// Background service worker for 知识库收藏 extension
// No persistent background logic needed - popup handles everything

chrome.runtime.onInstalled.addListener(() => {
  console.log('知识库收藏 extension installed');
});
