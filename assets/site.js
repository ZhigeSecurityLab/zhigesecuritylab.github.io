/* Theme runs before CSS to avoid a flash; counter runs after the page is ready. */
(function () {
  'use strict';
  var root = document.documentElement;
  var preference = null;
  function timeTheme() {
    var hour = new Date().getHours();
    return hour >= 7 && hour < 19 ? 'light' : 'dark';
  }
  try {
    var saved = sessionStorage.getItem('zhige-theme');
    if (saved === 'light' || saved === 'dark') preference = saved;
  } catch (_) { /* Storage may be disabled; switching still works for this page. */ }

  function applyTheme(theme) {
    root.dataset.theme = theme;
    var dark = theme === 'dark';
    var zh = root.lang === 'zh-CN';
    var button = document.querySelector('[data-theme-toggle]');
    if (button) {
      button.hidden = false;
      button.setAttribute('aria-label', zh ? (dark ? '切换至日间模式' : '切换至夜间模式') : (dark ? 'Switch to day mode' : 'Switch to night mode'));
      button.querySelector('[data-theme-label]').textContent = zh ? (dark ? '日间模式' : '夜间模式') : (dark ? 'Day mode' : 'Night mode');
    }
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = dark ? '#161f1c' : '#f7f8f6';
  }
  applyTheme(preference || timeTheme());
  // Follow the visitor's local clock until they choose a mode themselves.
  setInterval(function () {
    if (!preference) applyTheme(timeTheme());
  }, 60000);

  function loadCounter() {
    var counter = document.getElementById('busuanzi_value_site_pv');
    if (!counter) return;
    var group = counter.closest('.visit-counter');
    var originalTitle = group.title;
    var canonical = document.querySelector('link[rel="canonical"]');
    // Only the canonical production host counts; previews never pollute totals.
    if (!canonical || location.protocol !== 'https:' || location.hostname !== new URL(canonical.href).hostname) {
      group.title = root.lang === 'zh-CN' ? '访问量仅在正式网站统计' : 'Views are counted on the published website';
      return;
    }
    counter.textContent = '…';
    var finished = false;
    var timeout;
    var observer = new MutationObserver(function () {
      if (finished) return;
      var value = counter.textContent.trim();
      if (/^\d+$/.test(value)) {
        finished = true;
        observer.disconnect();
        clearTimeout(timeout);
        counter.textContent = Number(value).toLocaleString(root.lang);
        group.dataset.status = 'ready';
        group.title = originalTitle;
      }
    });
    function unavailable() {
      if (finished) return;
      clearTimeout(timeout);
      counter.textContent = '—';
      group.dataset.status = 'unavailable';
      group.title = root.lang === 'zh-CN' ? '统计服务暂时无法连接，请稍后重试' : 'The counter is temporarily unavailable';
    }
    observer.observe(counter, {childList:true, subtree:true, characterData:true});
    timeout = setTimeout(unavailable, 12000);
    var script = document.createElement('script');
    script.src = 'https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js';
    script.async = true;
    script.onerror = unavailable;
    document.head.appendChild(script);
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyTheme(root.dataset.theme);
    var button = document.querySelector('[data-theme-toggle]');
    if (button) button.addEventListener('click', function () {
      preference = root.dataset.theme === 'dark' ? 'light' : 'dark';
      try { sessionStorage.setItem('zhige-theme', preference); } catch (_) {}
      applyTheme(preference);
    });
    loadCounter();
  });
}());
