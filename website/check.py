"""Check generated site at both root and repository-prefixed URL layouts."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import posixpath
from build import build, OUT, classify

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag in ('a', 'img', 'script', 'link'):
            value = attrs.get('src') if tag in ('img', 'script') else attrs.get('href')
            if value:
                self.links.append(value)

if __name__ == '__main__':
    records = build()
    rules = [{'name': '电子设计', 'keywords': ['PCB', '封装']}, {'name': '建模', 'keywords': ['STEP']}]
    keys, topics = classify({'title': 'PCB封装与STEP模型', 'tags': [], 'keywords': ['定位']}, '', rules)
    assert topics == ['电子设计', '建模'] and '定位' in keys
    assert classify({'title': 'steps', 'tags': []}, '', rules)[1] == ['待整理']
    assert classify({'title': '说明', 'tags': ['PCB']}, '', rules)[1] == ['电子设计']
    pages = {}
    for source in OUT.rglob('*.html'):
        parser = Parser()
        parser.feed(source.read_text(encoding='utf-8'))
        assert {'sidebar', 'menu-toggle', 'sidebar-topics', 'sidebar-keywords', 'notes-data'} <= parser.ids
        import re
        data = re.search(r'<script id="notes-data" type="application/json">(.*?)</script>', source.read_text(encoding='utf-8'), re.S)
        assert data and json.loads(data[1]) == records, '每页必须包含完整离线知识索引'
        pages[source.relative_to(OUT).as_posix()] = parser
    failures = []
    for prefix in ('/', '/sample-repository/'):
        for relative, parser in pages.items():
            for value in parser.links:
                parsed = urlsplit(value)
                if parsed.scheme or parsed.netloc:
                    continue
                target_url = posixpath.normpath(posixpath.join(prefix, posixpath.dirname(relative), unquote(parsed.path))) if parsed.path else prefix + relative
                if not target_url.startswith(prefix):
                    failures.append(f'超出部署路径: {relative} -> {value}')
                    continue
                target_name = target_url[len(prefix):]
                target = OUT / target_name
                if not target.is_file():
                    failures.append(f'缺少文件: {relative} -> {value}')
                elif parsed.fragment and target_name in pages and unquote(parsed.fragment) not in pages[target_name].ids:
                    failures.append(f'缺少锚点: {relative} -> {value}')
    for note in records:
        assert (OUT / unquote(note['url'])).is_file()
    assert len(json.loads((OUT / 'search-index.json').read_text(encoding='utf-8'))) == len(records)
    import re
    home = (OUT / 'index.html').read_text(encoding='utf-8')
    embedded = re.search(r'<script id="notes-data" type="application/json">(.*?)</script>', home, re.S)
    assert embedded and json.loads(embedded[1]) == records, '离线搜索索引不匹配'
    if failures:
        raise SystemExit('\n'.join(failures))
    print(f'检查通过：{len(records)} 篇笔记，{len(pages)} 个页面；根路径与仓库子路径均无失效内部链接。')
