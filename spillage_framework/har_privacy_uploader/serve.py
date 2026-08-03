#!/usr/bin/env python3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os


ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
print("HAR Privacy Uploader: http://127.0.0.1:8787")
ThreadingHTTPServer(("127.0.0.1", 8787), SimpleHTTPRequestHandler).serve_forever()
