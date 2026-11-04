"""Smoke-test local preview and busy-port fallback without opening a browser."""
from pathlib import Path
import os
import re
import socket
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
with socket.socket() as occupied:
    occupied.bind(('127.0.0.1', 0))
    occupied.listen()
    port = occupied.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, str(ROOT / 'deploy/local/serve.py'), '--port', str(port), '--auto-port', '--no-open'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
        env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    try:
        first = process.stdout.readline()
        line = process.stdout.readline()
        address = re.search(r'http://127\.0\.0\.1:(\d+)/', line)
        assert address, (first, line)
        assert int(address[1]) != port, 'Busy port fallback failed'
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(address[0], timeout=5) as response:
            body = response.read().decode('utf-8')
            assert response.status == 200 and 'id="search-dialog"' in body and 'id="ui-style"' in body
        print('Local preview passed: rebuild, occupied-port fallback, HTTP 200, search and UI controls.')
    finally:
        process.terminate()
        process.communicate(timeout=5)
