"""Build and serve locally; Ctrl+C stops. No runtime third-party dependencies."""
import argparse
import functools
import http.server
from pathlib import Path
import subprocess
import sys
import webbrowser

ROOT = Path(__file__).resolve().parents[2]
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--no-open', action='store_true')
    parser.add_argument('--auto-port', action='store_true', help='Use an available port if the requested port is occupied')
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / 'website/build.py')], check=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'build/site'))
    try:
        server = http.server.ThreadingHTTPServer((args.host, args.port), handler)
    except OSError:
        if not args.auto_port:
            raise
        server = http.server.ThreadingHTTPServer((args.host, 0), handler)
    with server:
        address = f'http://{args.host}:{server.server_port}/'
        print(f'学习笔记：{address}（Ctrl+C 停止；修改笔记后重新启动）', flush=True)
        if not args.no_open:
            webbrowser.open(address)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
