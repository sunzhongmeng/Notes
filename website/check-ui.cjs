// Lightweight DOM harness: exercise the shipped script without browser/network access.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const base = path.resolve(__dirname, '..');
const notes = JSON.parse(fs.readFileSync(path.join(base, 'build/site/search-index.json'), 'utf8'));
class Element {
  constructor(tag = 'div') { this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.attrs = {}; this.events = {}; this.value = ''; this.hidden = false; this.checked = false; this.classList = {add() {}, toggle() {}}; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(k, v) { this.attrs[k] = v; }
  addEventListener(k, f) { this.events[k] = f; }
  add(option) { this.children.push(option); }
  get options() { return this.children; }
  querySelectorAll() { return this.children.filter(x => x.dataset.view); }
  focus() { this.focused = true; }
  showModal() { this.open = true; }
  close() { this.open = false; this.events.close?.(); }
}
function run(relative, query = '', stored = {}) {
  const ids = ['ui-style','search-dialog','global-search','global-results','global-count','quick-search','close-search','notes-data','theme','sidebar','menu-toggle','sidebar-topics','sidebar-keywords','review','article-keywords','related-notes','outline','knowledge','topic-grid','category','topic','only-review','active-filters','result-count','notes-grid'];
  if (relative === 'index.html') ids.push('search');
  const elements = Object.fromEntries(ids.map(id => ['#' + id, new Element()]));
  for (const selector of ['.layout', '.hero h1']) elements[selector] = new Element();
  elements['#notes-data'].textContent = JSON.stringify(notes);
  for (const id of ['category','topic']) elements['#' + id].add({value: ''});
  for (const view of ['notes','knowledge','review']) { const a = new Element('a'); a.dataset.view = view; elements['#sidebar'].append(a); }
  const location = new URL('file:///E:/notebook/' + relative + query);
  const storage = new Map(Object.entries(stored));
  const root = '../'.repeat(relative.split('/').length - 1);
  const listeners = {};
  const context = { URL, URLSearchParams, location, matchMedia: () => ({matches: false}),
    history: {replaceState(a, b, value) { context.lastURL = value; }},
    localStorage: {getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value)},
    Option: function(text, value) { this.text = text; this.value = value; },
    document: {currentScript: {dataset: {root}}, documentElement: {dataset: {}}, body: new Element(), activeElement: new Element(), querySelector: s => elements[s] || null, createElement: tag => new Element(tag), addEventListener(event, fn) { (listeners[event] ||= []).push(fn); }}
  };
  vm.runInNewContext(fs.readFileSync(path.join(base, 'website/static/app.js'), 'utf8'), context);
  return {elements, storage, context, key(event) { for (const fn of listeners.keydown || []) fn(event); }};
}
let {elements: e, storage} = run('index.html');
assert.equal(e['#notes-grid'].children.length, notes.length);
e['#menu-toggle'].onclick();
assert.equal(e['#sidebar'].hidden, true);
assert.equal(e['#menu-toggle'].attrs['aria-expanded'], 'false');
assert.equal(storage.get('notes-menu'), 'false');
assert.equal(run('index.html', '', {'notes-menu':'false'}).elements['#sidebar'].hidden, true);
e['#search'].value = 'no-such-note-916274'; e['#search'].events.input();
assert.match(e['#result-count'].textContent, /^0 /);
assert.equal(e['#notes-grid'].children[0].className, 'empty');
e['#active-filters'].children.at(-1).onclick();
assert.equal(e['#notes-grid'].children.length, notes.length);
for (const topic of new Set(notes.flatMap(n => n.topics))) {
  const result = run('index.html', '?view=knowledge&topic=' + encodeURIComponent(topic));
  assert.equal(result.elements['#knowledge'].hidden, false);
  assert.equal(result.elements['#notes-grid'].children.length, notes.filter(n => n.topics.includes(topic)).length);
}
const selected = notes.find(n => n.keywords.length);
const keyword = selected.keywords[0];
assert.equal(run('index.html', '?keyword=' + encodeURIComponent(keyword)).elements['#notes-grid'].children.length, notes.filter(n => n.keywords.includes(keyword)).length);
assert.match(run('index.html', '?topic=unknown').elements['#result-count'].textContent, /^0 /);
const reviewState = {'notes-review': JSON.stringify([decodeURIComponent(selected.url)])};
assert.match(run('index.html', '?review=1', reviewState).elements['#result-count'].textContent, /^1 /);
for (const note of notes) {
  const article = run(note.url);
  assert.equal(article.elements['#article-keywords'].children.length, note.topics.length + note.keywords.length);
  assert.equal(article.elements['#review'].hidden, false);
  article.elements['#review'].onclick();
  assert.ok(JSON.parse(article.storage.get('notes-review')).includes(decodeURIComponent(note.url)));
  article.elements['#review'].onclick();
  assert.equal(JSON.parse(article.storage.get('notes-review')).length, 0);
}
console.log('Interaction checks passed: menu, saved state, search/reset, topics, keywords, stale filters, reviews, article navigation.');
for (const relative of ['index.html', notes[0].url]) {
  const page = run(relative);
  let prevented = false;
  page.key({key: '/', code: 'Slash', preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
  assert.equal(page.elements['#search-dialog'].open, true);
  assert.equal(page.elements['#global-search'].focused, true);
  page.elements['#global-search'].value = 'no-such-note-916274';
  page.elements['#global-search'].events.input();
  assert.match(page.elements['#global-count'].textContent, /0/);
  page.elements['#close-search'].onclick();
  assert.equal(page.elements['#search-dialog'].open, false);
  page.context.document.activeElement = new Element('input');
  page.key({key: '/', code: 'Slash', preventDefault() { throw Error('Must not intercept typing'); }});
  assert.equal(page.elements['#search-dialog'].open, false);
  page.elements['#quick-search'].onclick();
  assert.equal(page.elements['#search-dialog'].open, true);
  for (const style of ['forest','paper','ocean','minimal']) {
    page.elements['#ui-style'].value = style;
    page.elements['#ui-style'].events.change();
    assert.equal(page.context.document.documentElement.dataset.ui, style);
    assert.equal(JSON.parse(page.storage.get('notes-ui')), style);
    assert.equal(run(relative, '', {'notes-ui': JSON.stringify(style)}).context.document.documentElement.dataset.ui, style);
  }
}
console.log('New checks passed: global search on home/article, input protection, search button, four saved UI styles.');
