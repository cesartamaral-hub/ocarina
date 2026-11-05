"""
Work offline: the app uses only what is on this Mac, and never contacts the internet.

The switch is the preference `offline.only` (General in Settings). Each feature that would use the internet asks `require_online` first and
says why it cannot (a clear message); as a safety net `install_guard` makes any other attempt of this process to reach a server outside this
Mac fail the same way, so nothing leaks through a place that was missed.
"""

import os
import socket
import urllib.parse
import urllib.request

import requests

from ocarina import prefs

PREF = "offline.only"
MESSAGE = "Work offline is on, so this needs a connection it may not use. Turn it off in Settings → General."
LOOPBACK = {"localhost", "127.0.0.1", "::1", "[::1]"}

_datapath = None
_cache = {"mtime": None, "on": False}


class OfflineMode(requests.exceptions.ConnectionError):
    """
    Raised for what would use the internet while offline mode is on. It is a connection error, so code that copes with "no connection" does
    (the dictionary then answers from what is on this Mac), and code that does not shows its message.
    """

    code = "offline_mode"

    def __init__(self, what="This"):
        super().__init__(f"{what} needs the internet, and Work offline is on. Turn it off in Settings → General to use it.")


def configure(datapath):
    "Where the preferences are (called once when the app starts)."
    global _datapath  # pylint: disable=global-statement
    _datapath = datapath
    _cache["mtime"] = None


def is_on():
    "Whether Work offline is switched on (read from the preferences file, which is looked at again only when it changes)."
    if not _datapath:
        return False
    path = prefs.path_for(_datapath)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return False
    if mtime != _cache["mtime"]:
        _cache["on"] = bool(prefs.load(path).get(PREF))
        _cache["mtime"] = mtime
    return _cache["on"]


def require_online(what="This"):
    "Raise OfflineMode when Work offline is on."
    if is_on():
        raise OfflineMode(what)


def _is_local(host):
    if not host:
        return True
    host = host.strip("[]").lower()
    return host in LOOPBACK or host.startswith("127.")


def install_guard():
    "Make this process's own attempts to reach another computer fail while Work offline is on (called once at start; harmless when it is off)."
    if getattr(requests.Session, "_ocarina_guard", False):
        return
    original_request = requests.Session.request
    original_urlopen = urllib.request.urlopen
    original_connect = socket.socket.connect

    def request(self, method, url, *args, **kwargs):
        if is_on() and not _is_local(urllib.parse.urlparse(str(url)).hostname):
            raise OfflineMode()
        return original_request(self, method, url, *args, **kwargs)

    def urlopen(url, *args, **kwargs):
        target = url.full_url if hasattr(url, "full_url") else str(url)
        if is_on() and not _is_local(urllib.parse.urlparse(target).hostname):
            raise OfflineMode()
        return original_urlopen(url, *args, **kwargs)

    def connect(self, address):
        host = address[0] if isinstance(address, tuple) else None
        if is_on() and isinstance(host, str) and self.family in (socket.AF_INET, socket.AF_INET6) and not _is_local(host):
            raise OfflineMode()
        return original_connect(self, address)

    requests.Session.request = request
    requests.Session._ocarina_guard = True  # pylint: disable=protected-access
    urllib.request.urlopen = urlopen
    socket.socket.connect = connect
