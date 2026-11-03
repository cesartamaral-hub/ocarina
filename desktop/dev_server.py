"""
Backend for development: python dev_server.py <app-dir> [port]

Runs Lute + Ocarina straight from the source files, on the data in <app-dir>
(a folder like ~/Library/Application Support/Ocarina). Restart it after Python edits.
"""
import os
import sys

from waitress import serve

from lute.app_factory import create_app
from ocarina.startup import prepare_library

app_dir = os.path.abspath(sys.argv[1])
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5001

os.makedirs(app_dir, exist_ok=True)
config = os.path.join(app_dir, "config.yml")
with open(config, "w", encoding="utf-8") as f:
    f.write(f"ENV: prod\nDBNAME: ocarina.db\nDATAPATH: {app_dir}\n")

app = create_app(config, output_func=lambda s: None)
prepare_library(app)
print(f"Backend on http://127.0.0.1:{port}  (data: {app_dir})", flush=True)
serve(app, host="127.0.0.1", port=port)
