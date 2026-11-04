"""Build and open a file:// preview without a local HTTP port."""
from pathlib import Path
import subprocess
import sys
import webbrowser

ROOT = Path(__file__).resolve().parents[2]

if __name__ == '__main__':
    subprocess.run([sys.executable, str(ROOT / 'website/build.py')], check=True)
    address = (ROOT / 'build/site/index.html').as_uri()
    print(f'离线预览：{address}', flush=True)
    if not webbrowser.open(address):
        print('浏览器未自动打开，请手动打开 build/site/index.html。')
