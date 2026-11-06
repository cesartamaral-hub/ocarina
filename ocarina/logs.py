"""
The log file: <data folder>/logs/ocarina.log.

An app opened from the Dock has no terminal, so errors would vanish. setup() sends everything the app and its model workers print or
log to this file, plus uncaught errors, and writes a header with the versions. A log over 2 MB is kept as ocarina.log.1 at the next
start (one older log is kept). The file holds paths, versions and error messages, not the texts you read; look it over before sending it.
"""

import logging
import os
import platform
import sys
import threading

from ocarina.version import VERSION

NAME = "ocarina.log"
MAX_BYTES = 2 * 1024 * 1024

_ready = False


def log_dir(datapath):
    return os.path.join(datapath, "logs")


def log_path(datapath):
    return os.path.join(log_dir(datapath), NAME)


def _rotate(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            os.replace(path, path + ".1")
    except OSError:
        pass


def setup(datapath, redirect=None):
    """
    Start logging to the file. redirect sends the process's own output (and that of the workers it starts) there too; it defaults to on
    inside the app bundle, where there is no terminal.
    """
    global _ready  # pylint: disable=global-statement
    if _ready or not datapath:
        return log_path(datapath) if datapath else None
    os.makedirs(log_dir(datapath), exist_ok=True)
    path = log_path(datapath)
    _rotate(path)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    logging.captureWarnings(True)

    if redirect is None:
        redirect = bool(os.environ.get("RESOURCEPATH"))
    if redirect:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        for target in (1, 2):
            os.dup2(fd, target)
        os.close(fd)
        sys.stdout = os.fdopen(1, "w", buffering=1, encoding="utf-8", errors="replace", closefd=False)
        sys.stderr = os.fdopen(2, "w", buffering=1, encoding="utf-8", errors="replace", closefd=False)

    def on_uncaught(kind, value, trace):
        logging.getLogger("ocarina").critical("Uncaught %s", kind.__name__, exc_info=(kind, value, trace))

    sys.excepthook = on_uncaught
    threading.excepthook = lambda a: on_uncaught(a.exc_type, a.exc_value, a.exc_traceback)
    logging.getLogger("ocarina").info(
        "Ocarina %s starting; macOS %s (%s); Python %s; data folder %s", VERSION, platform.mac_ver()[0] or platform.platform(), platform.machine(), platform.python_version(), datapath
    )
    _ready = True
    return path
