"""
The desktop app: Lute's Flask backend and the React frontend in a native pywebview window.
No terminal, no visible localhost URL (loopback only, random free port).
"""
import os
import socket
import sys
import threading
import time
import urllib.request

import webview
from waitress import create_server

from lute.app_factory import create_app, data_initialization
from lute.db import db

APP_DIR = os.environ.get("OCARINA_APP_DIR") or os.path.expanduser(
    "~/Library/Application Support/Ocarina"
)


def _write_config():
    os.makedirs(APP_DIR, exist_ok=True)
    path = os.path.join(APP_DIR, "config.yml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"ENV: prod\nDBNAME: ocarina.db\nDATAPATH: {APP_DIR}\n")
    return path


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(url, tries=100):
    for _ in range(tries):
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:  # pylint: disable=broad-exception-caught
            time.sleep(0.1)
    return False


def main():
    app = create_app(_write_config(), output_func=lambda s: None)
    with app.app_context():
        data_initialization(db.session, lambda s: None)

    port = _free_port()
    server = create_server(app, host="127.0.0.1", port=port)
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{port}/ocarina/app/"
    if not _wait_until_up(url):
        sys.exit("Backend did not start")

    webview.create_window("Ocarina", url, width=1280, height=860)
    webview.start()
    server.close()


if __name__ == "__main__":
    main()
