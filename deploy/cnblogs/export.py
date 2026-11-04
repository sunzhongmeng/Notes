"""Export one article, keeping source untouched and listing unresolved resources."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'website'))
from build import metadata

def export(source, base_url='', mapping=None):
    source = source.resolve()
    content = ROOT / 'content'
    if not source.is_relative_to(content / 'notes') or source.suffix.lower() != '.md':
        raise ValueError('仅接受 content/notes 内的 Markdown 文件')
    meta, text = metadata(source)
    target = ROOT / 'exports/cnblogs' / source.relative_to(content / 'notes').with_suffix('')
    target.mkdir(parents=True, exist_ok=True)
    resources = []
    mapping = mapping or {}
    def replace(match):
        original = match[2]
        parts = urlsplit(original)
        if parts.scheme or parts.netloc or not parts.path:
            return match[0]
        path = (source.parent / unquote(parts.path)).resolve()
        if not path.is_relative_to(content) or not path.is_file():
            raise ValueError(f'本地链接不存在或超出 content：{original}')
        key = path.relative_to(content).as_posix()
        public = mapping.get(key)
        if not public and base_url and path.suffix.lower() != '.md':
            public = base_url.rstrip('/') + '/' + quote(key, safe='/')
        resource = {'source': key, 'url': public, 'needs_upload_or_url': not bool(public)}
        resources.append(resource)
        if public:
            return match[1] + public + (('#' + parts.fragment) if parts.fragment else '') + match[3]
        dest = target / 'resources' / path.relative_to(content)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        return match[1] + 'resources/' + quote(key, safe='/') + (('#' + parts.fragment) if parts.fragment else '') + match[3]
    # Protect fenced/inline code: examples in code should not be rewritten.
    chunks = re.split(r'(```[^\n]*\n.*?```|~~~[^\n]*\n.*?~~~|`[^`\n]+`)', text, flags=re.S)
    link = re.compile(r'(!?\[[^\]\n]*\]\()([^\s)]+)(\))')
    text = ''.join(chunk if i % 2 else link.sub(replace, chunk) for i, chunk in enumerate(chunks))
    if re.search(r'^\s*\[[^\]]+\]:|<img\b|<a\b|!?\[[^\]]+\]\[[^\]]*\]', text, re.M | re.I):
        resources.append({'manual_check': '检测到引用式链接或 HTML，请手动核对图片和链接。'})
    (target / 'article.md').write_text(text, encoding='utf-8')
    (target / 'resources.json').write_text(json.dumps(resources, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'已导出：{target}；需人工处理 {sum(bool(r.get("needs_upload_or_url")) for r in resources)} 项资源')
    return target

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('note', type=Path)
    parser.add_argument('--base-url', default='', help='公开静态站点根 URL，包含仓库子路径（如有）')
    parser.add_argument('--map', type=Path, help='content 相对路径到公开 URL 的 JSON 映射')
    args = parser.parse_args()
    export(args.note, args.base_url, json.loads(args.map.read_text(encoding='utf-8')) if args.map else None)
