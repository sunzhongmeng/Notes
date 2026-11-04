const root = document.currentScript.dataset.root;
function get(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
function put(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch {} }
const notes = JSON.parse(document.querySelector('#notes-data').textContent);
const params = new URLSearchParams(location.search);
const homeURL = new URL(root + 'index.html', location.href);
const articleKey = decodeURIComponent(location.pathname.slice(homeURL.pathname.lastIndexOf('/') + 1));
let reviews = get('notes-review', []);
if (!Array.isArray(reviews)) reviews = [];
document.documentElement.dataset.theme = get('notes-theme', 'light');
const stylePicker = document.querySelector('#ui-style');
const styles = ['forest', 'paper', 'ocean', 'minimal'];
const savedStyle = get('notes-ui', 'forest');
stylePicker.value = styles.includes(savedStyle) ? savedStyle : 'forest';
document.documentElement.dataset.ui = stylePicker.value;
stylePicker.addEventListener('change', () => {
  document.documentElement.dataset.ui = stylePicker.value; put('notes-ui', stylePicker.value);
});
document.querySelector('#theme').onclick = () => {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next; put('notes-theme', next);
};
const sidebar = document.querySelector('#sidebar');
const toggle = document.querySelector('#menu-toggle');
function setMenu(open) {
  sidebar.hidden = !open;
  document.body.classList.toggle('menu-open', open);
  toggle.setAttribute('aria-expanded', String(open));
  toggle.setAttribute('aria-label', open ? '隐藏菜单' : '显示菜单');
}
setMenu(get('notes-menu', !matchMedia('(max-width: 900px)').matches));
toggle.onclick = () => { const open = sidebar.hidden; setMenu(open); put('notes-menu', open); };
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !document.querySelector('#search-dialog').open && !sidebar.hidden) { setMenu(false); put('notes-menu', false); toggle.focus(); } });
function element(tag, text, className = '') { const el = document.createElement(tag); el.textContent = text; el.className = className; return el; }
function indexLink(text, values, className = '') {
  const link = element('a', text, className);
  link.href = root + 'index.html?' + new URLSearchParams(values);
  return link;
}
function counts(field) {
  const result = new Map();
  for (const note of notes) for (const value of new Set(note[field])) result.set(value, (result.get(value) || 0) + 1);
  return [...result].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh-CN'));
}
const topics = counts('topics'), keywords = counts('keywords');
for (const [name, count] of topics) document.querySelector('#sidebar-topics').append(indexLink(`${name} · ${count}`, {view: 'knowledge', topic: name}));
for (const [name, count] of keywords) document.querySelector('#sidebar-keywords').append(indexLink(`${name} ${count}`, {keyword: name}, 'chip'));
const search = document.querySelector('#search');
const view = !search ? '' : params.get('review') === '1' ? 'review' : params.get('view') === 'knowledge' ? 'knowledge' : 'notes';
for (const link of sidebar.querySelectorAll('[data-view]')) if (link.dataset.view === view) link.setAttribute('aria-current', 'page');
function card(note) {
  const link = element('a', '', 'note-card'); link.href = root + note.url;
  link.append(element('span', note.topics.join(' · '), 'eyebrow'), element('h2', note.title), element('p', note.text.replace(/\s+/g, ' ').trim().slice(0, 115) + '…'), element('div', (note.keywords.join(' / ') || '待整理') + (note.updated ? ' · ' + note.updated : '') + (reviews.includes(decodeURIComponent(note.url)) ? ' · 待复习' : ''), 'card-meta'));
  return link;
}
const searchDialog = document.querySelector('#search-dialog');
const globalSearch = document.querySelector('#global-search');
function renderGlobalSearch() {
  const words = globalSearch.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const result = notes.filter(n => words.every(w => [n.title, n.text, n.category, ...n.keywords, ...n.topics].join(' ').toLocaleLowerCase().includes(w)));
  const list = document.querySelector('#global-results'); list.replaceChildren();
  document.querySelector('#global-count').textContent = `找到 ${result.length} 篇笔记`;
  for (const note of result.slice(0, 30)) list.append(card(note));
  if (!result.length) list.append(element('p', '没有匹配的笔记，请尝试其他关键词。', 'empty'));
  if (result.length > 30) list.append(indexLink('查看全部搜索结果 →', {q: globalSearch.value}));
}
let searchOrigin;
function openSearch() {
  searchOrigin = document.activeElement;
  if (!searchDialog.open) searchDialog.showModal();
  renderGlobalSearch(); globalSearch.focus();
}
document.querySelector('#quick-search').onclick = openSearch;
document.querySelector('#close-search').onclick = () => searchDialog.close();
searchDialog.addEventListener('close', () => { if (searchOrigin) searchOrigin.focus(); });
globalSearch.addEventListener('input', renderGlobalSearch);
document.addEventListener('keydown', e => {
  const active = document.activeElement;
  if (e.isComposing || e.ctrlKey || e.metaKey || e.altKey || e.shiftKey || ['INPUT', 'TEXTAREA', 'SELECT'].includes(active.tagName) || active.isContentEditable) return;
  if (e.key === '/' || e.key === '／' || e.code === 'Slash') { e.preventDefault(); openSearch(); }
});
if (!search) {
  const reviewButton = document.querySelector('#review'); reviewButton.hidden = false;
  function updateReview() { reviewButton.textContent = reviews.includes(articleKey) ? '✓ 已加入待复习 · 点击移除' : '＋ 加入待复习'; }
  updateReview();
  reviewButton.onclick = () => { reviews = reviews.includes(articleKey) ? reviews.filter(x => x !== articleKey) : [...reviews, articleKey]; put('notes-review', reviews); updateReview(); };
  const current = notes.find(n => decodeURIComponent(n.url) === articleKey);
  if (current) {
    const chips = document.querySelector('#article-keywords');
    for (const name of current.topics) chips.append(indexLink(name, {view: 'knowledge', topic: name}, 'chip topic-chip'));
    for (const name of current.keywords) chips.append(indexLink('# ' + name, {keyword: name}, 'chip'));
    const related = notes.filter(n => n !== current).map(n => ({note: n, score: n.keywords.filter(k => current.keywords.includes(k)).length * 2 + n.topics.filter(t => t !== '待整理' && current.topics.includes(t)).length})).filter(n => n.score > 0).sort((a, b) => b.score - a.score).slice(0, 4);
    const grid = document.querySelector('#related-notes');
    for (const item of related) grid.append(card(item.note));
    if (!related.length) grid.append(element('p', '还没有相关笔记。继续记录相同主题的内容，这里会自动建立关联。', 'empty'));
  }
} else {
  document.querySelector('#outline').hidden = true;
  document.querySelector('.layout').classList.add('home');
  const category = document.querySelector('#category'), topic = document.querySelector('#topic'), only = document.querySelector('#only-review');
  let keyword = params.get('keyword') || '';
  for (const name of [...new Set(notes.map(n => n.category))].sort()) category.add(new Option(name, name));
  for (const [name, count] of topics) topic.add(new Option(`${name} (${count})`, name));
  // Preserve unknown values so stale bookmarked filters yield an honest empty state.
  function restore(select, value) { if (value && ![...select.options].some(o => o.value === value)) select.add(new Option(value, value)); select.value = value; }
  search.value = params.get('q') || ''; restore(category, params.get('category') || ''); restore(topic, params.get('topic') || ''); only.checked = params.get('review') === '1';
  const knowledge = params.get('view') === 'knowledge';
  document.querySelector('#knowledge').hidden = !knowledge;
  if (knowledge) {
    document.querySelector('.hero h1').textContent = '把零散记录，连成知识。';
    for (const [name, count] of topics) {
      const link = indexLink('', {view: 'knowledge', topic: name}, 'note-card topic-card');
      const members = notes.filter(n => n.topics.includes(name));
      link.append(element('span', `${count} 篇关联笔记`, 'eyebrow'), element('h2', name), element('p', [...new Set(members.flatMap(n => n.keywords))].slice(0, 6).join(' · ')));
      document.querySelector('#topic-grid').append(link);
    }
  }
  function render() {
    const words = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const result = notes.filter(n => (!category.value || n.category === category.value) && (!topic.value || n.topics.includes(topic.value)) && (!keyword || n.keywords.includes(keyword)) && (!only.checked || reviews.includes(decodeURIComponent(n.url))) && words.every(w => [n.title, n.text, n.category, ...n.keywords, ...n.topics].join(' ').toLocaleLowerCase().includes(w)));
    const grid = document.querySelector('#notes-grid'); grid.replaceChildren();
    document.querySelector('#result-count').textContent = `${result.length} / ${notes.length} 篇笔记`;
    for (const note of result) grid.append(card(note));
    if (!result.length) grid.append(element('p', '没有匹配的笔记。可清除筛选，或尝试其他关键词。', 'empty'));
    const filters = document.querySelector('#active-filters'); filters.replaceChildren();
    for (const [label, clear] of [
      ...(keyword ? [[`关键词：${keyword}`, () => { keyword = ''; }]] : []),
      ...(topic.value ? [[`主题：${topic.value}`, () => { topic.value = ''; }]] : []),
      ...(category.value ? [[`目录：${category.value}`, () => { category.value = ''; }]] : [])
    ]) { const button = element('button', label + ' ×', 'chip'); button.setAttribute('aria-label', '清除' + label); button.onclick = () => { clear(); render(); }; filters.append(button); }
    if (words.length || keyword || topic.value || category.value || only.checked) {
      const reset = element('button', '清除全部筛选', 'chip'); reset.onclick = () => { search.value = ''; keyword = ''; topic.value = ''; category.value = ''; only.checked = false; render(); }; filters.append(reset);
    }
    const query = new URLSearchParams(); if (knowledge) query.set('view', 'knowledge'); if (search.value) query.set('q', search.value); if (category.value) query.set('category', category.value); if (topic.value) query.set('topic', topic.value); if (keyword) query.set('keyword', keyword); if (only.checked) query.set('review', '1');
    try { history.replaceState(null, '', location.pathname + (query.size ? '?' + query : '')); } catch {}
  }
  search.addEventListener('input', render); category.addEventListener('change', render); topic.addEventListener('change', render); only.addEventListener('change', render); render();
}
