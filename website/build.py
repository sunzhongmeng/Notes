"""Portable static notebook builder. Run from any working directory."""
from pathlib import Path
import html
import json
import posixpath
import re
import shutil
from urllib.parse import quote, unquote, urlsplit
import xml.etree.ElementTree as ET
import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build' / 'site'

def url(path):
    return quote(path.as_posix(), safe='/')

class Links(Treeprocessor):
    def run(self, root):
        for el in root.iter():
            attr = 'src' if el.tag == 'img' else 'href' if el.tag == 'a' else None
            if not attr:
                continue
            value = el.get(attr, '')
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            source = (self.md.source.parent / unquote(parsed.path)).resolve()
            if not source.is_relative_to(ROOT / 'content') or not source.is_file():
                raise ValueError(f'{self.md.source}: 无效的本地链接 {value}')
            dest = source.relative_to(ROOT / 'content')
            if dest.parts[0] == 'notes' and dest.suffix.lower() == '.md':
                dest = dest.with_suffix('.html')
            link = quote(posixpath.relpath(dest.as_posix(), self.md.page.parent.as_posix()), safe='/')
            el.set(attr, link + (('?' + parsed.query) if parsed.query else '') + (('#' + parsed.fragment) if parsed.fragment else ''))
        return root

class LinkExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(Links(md), 'local_links', 5)

def metadata(source):
    text = source.read_text(encoding='utf-8-sig')
    meta = {}
    match = re.match(r'<!-- note\s+(\{.*?\})\s*-->\s*', text, re.S)
    if match:
        meta = json.loads(match[1])
        text = text[match.end():]
    title = re.search(r'^#\s+(.+)$', text, re.M)
    meta.setdefault('title', title[1] if title else source.stem)
    meta.setdefault('tags', [])
    if not isinstance(meta['tags'], list):
        raise ValueError(f'{source}: tags 必须为数组')
    return meta, text

def classify(meta, text, rules):
    """Explicit keywords and tags coexist with reproducible keyword rules."""
    explicit = meta.get('keywords', [])
    if not isinstance(explicit, list) or not all(isinstance(x, str) for x in explicit + meta['tags']):
        raise ValueError('keywords 和 tags 必须为字符串数组')
    haystack = (meta['title'] + '\n' + text).casefold()
    keywords = list(dict.fromkeys(x.strip() for x in meta['tags'] + explicit if x.strip()))
    topics = []
    for rule in rules:
        matches = [word for word in rule['keywords'] if re.search(
            (r'(?<![a-z0-9_])' + re.escape(word) + r'(?![a-z0-9_])') if word.isascii() else re.escape(word), haystack, re.I)]
        if matches or any(x.casefold() in [w.casefold() for w in rule['keywords']] for x in keywords):
            topics.append(rule['name'])
            keywords.extend(matches)
    return list(dict.fromkeys(keywords)), topics or ['待整理']

def build():
    OUT.mkdir(parents=True, exist_ok=True)
    # Remove only files recorded by the previous build, confined to this output.
    manifest = OUT / '.generated.json'
    if manifest.exists():
        for name in json.loads(manifest.read_text(encoding='utf-8')):
            target = (OUT / name).resolve()
            if target.is_relative_to(OUT.resolve()) and target.is_file():
                target.unlink()
    config = json.loads((ROOT / 'website/settings.json').read_text(encoding='utf-8'))
    template = (ROOT / 'website/templates/page.html').read_text(encoding='utf-8')
    records = []
    def page(title, body, relative, toc='', source=''):
        prefix = '../' * (len(relative.parts) - 1)
        values = {'TITLE': html.escape(title), 'SITE': html.escape(config['title']),
                  'SUBTITLE': html.escape(config['subtitle']), 'PREFIX': prefix,
                  'BODY': body, 'TOC': toc, 'SOURCE': source,
                  'DATA': json.dumps(records, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')}
        rendered = re.sub(r'\{\{([A-Z]+)\}\}', lambda m: values[m[1]], template)
        target = OUT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding='utf-8')
    articles = []
    for source in sorted((ROOT / 'content/notes').rglob('*.md')):
        meta, text = metadata(source)
        relative = source.relative_to(ROOT / 'content').with_suffix('.html')
        md = markdown.Markdown(extensions=['extra', 'toc', 'sane_lists', LinkExtension()], extension_configs={'toc': {'permalink': '¶'}})
        md.source, md.page = source, relative
        body = md.convert(text)
        category = source.parent.relative_to(ROOT / 'content/notes').as_posix()
        record = {'title': meta['title'], 'category': category if category != '.' else '未分类',
                  'tags': meta['tags'], 'updated': meta.get('updated', ''),
                  'url': url(relative), 'text': re.sub('<[^>]+>', ' ', body)}
        record['keywords'], record['topics'] = classify(meta, text, config.get('topics', []))
        records.append(record)
        raw = Path('source') / source.relative_to(ROOT / 'content')
        articles.append((meta['title'], '<div class="article-meta">' + html.escape(record['category']) + ' · ' + html.escape(record['updated']) + '</div><div id="article-keywords" class="chips"></div>' + body + '<section id="related"><h2>相关笔记</h2><div id="related-notes" class="notes-grid"></div></section>', relative, md.toc, '<a href="' + '../' * (len(relative.parts)-1) + url(raw) + '" download>下载 Markdown ↗</a>'))
    for article in articles:
        page(*article)
    cards = ''.join('<a class="note-card" href="' + r['url'] + '"><span class="eyebrow">' + html.escape(r['category']) + '</span><h2>' + html.escape(r['title']) + '</h2><p>' + html.escape(' · '.join(r['tags'])) + '</p></a>' for r in records)
    home = '<section class="hero"><span class="eyebrow">PERSONAL KNOWLEDGE BASE</span><h1>记录所学，连接知识。</h1><p>' + html.escape(config['subtitle']) + '</p><span class="stat">' + str(len(records)) + ' 篇笔记 · 持续积累中</span></section><section id="knowledge" hidden><h2>知识主题</h2><p>一篇笔记可以连接多个主题。选择主题或关键词，探索相关内容。</p><div id="topic-grid" class="notes-grid"></div></section><section class="toolbar"><label class="search"><span>⌕</span><input id="search" type="search" placeholder="搜索标题、正文、关键词…" aria-label="全文搜索"></label><select id="category" aria-label="筛选目录"><option value="">全部目录</option></select><select id="topic" aria-label="筛选知识主题"><option value="">全部主题</option></select><label class="review-filter"><input id="only-review" type="checkbox"> 待复习</label></section><div id="active-filters" class="chips"></div><p id="result-count" aria-live="polite"></p><div id="notes-grid" class="notes-grid">' + cards + '</div>'
    # Every page embeds its index for file:// navigation without fetch.
    page(config['title'], home, Path('index.html'))
    for name in ['images', 'attachments', 'code']:
        source = ROOT / 'content' / name
        if source.exists():
            shutil.copytree(source, OUT / name, dirs_exist_ok=True)
    shutil.copytree(ROOT / 'content', OUT / 'source', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'website/static', OUT / 'static', dirs_exist_ok=True)
    (OUT / 'search-index.json').write_text(json.dumps(records, ensure_ascii=False), encoding='utf-8')
    (OUT / '.nojekyll').touch()
    files = [p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p != manifest]
    manifest.write_text(json.dumps(files), encoding='utf-8')
    print(f'构建完成：{len(records)} 篇笔记 → {OUT}')
    return records

if __name__ == '__main__':
    build()
