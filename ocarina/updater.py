"""
Updates: the app finds the latest GitHub release, downloads its disk image, checks it against the published SHA-256, and swaps itself.

    latest()        the newest release {version, notes, url, assetUrl, size, sha256} or None (network; cached for a few minutes)
    is_newer(a, b)  whether version a is newer than b
    start_download  a thread fetches the disk image into <data>/cache/update, checking the SHA-256
    install(...)    unpacks the new app next to the installed one and starts a helper that swaps them after this app quits

The update never touches the data folder (library, models, dictionaries). The helper keeps the old app until the new one has started,
and puts it back if it did not. Nothing here runs while Work offline is on.
"""

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time

import requests

from ocarina import offline, paths
from ocarina.version import VERSION

REPO = "cesartamaral-hub/ocarina"
ASSET = "Ocarina.dmg"
TIMEOUT = 8
CACHE_SECONDS = 300
SNOOZE_SECONDS = 24 * 3600
USER_AGENT = f"Ocarina/{VERSION} (update check)"

PREF_CHECK = "update.check"  # check for updates when Ocarina starts (default on)
PREF_SKIP = "update.skip"  # a version the user chose to skip
PREF_SNOOZE = "update.snooze"  # epoch seconds: no reminder before then

_cache = {"at": 0.0, "release": None}
_download = {"state": "idle", "done": 0, "total": 0, "error": "", "path": "", "version": ""}
_lock = threading.Lock()


class UpdateError(Exception):
    "Something the user can be told: the message says what and why."


def version_key(version):
    "(1, 2, 3) for 'v1.2.3'; None when it is not a plain version."
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(version).strip())
    return tuple(int(x) for x in m.groups()) if m else None


def is_newer(candidate, current=VERSION):
    a, b = version_key(candidate), version_key(current)
    return a is not None and b is not None and a > b


def _release_from(data):
    "The release as the app needs it, or None when it has no disk image or no checksum."
    version = (data.get("tag_name") or "").lstrip("v")
    if version_key(version) is None or data.get("draft") or data.get("prerelease"):
        return None
    asset = next((a for a in data.get("assets", []) if a.get("name") == ASSET), None)
    digest = ((asset or {}).get("digest") or "").removeprefix("sha256:")
    sha_asset = next((a for a in data.get("assets", []) if a.get("name") == ASSET + ".sha256"), None)
    if not asset or not (re.fullmatch(r"[0-9a-f]{64}", digest) or sha_asset):
        return None
    return {
        "version": version,
        "notes": data.get("body") or "",
        "url": data.get("html_url") or f"https://github.com/{REPO}/releases",
        "assetUrl": asset["browser_download_url"],
        "size": int(asset.get("size") or 0),
        "sha256": digest if re.fullmatch(r"[0-9a-f]{64}", digest) else None,
        "shaUrl": sha_asset["browser_download_url"] if sha_asset else None,
    }


def latest(force=False):
    "The newest release, or None when there is none (or it cannot be read). Raises UpdateError when GitHub cannot be reached."
    if offline.is_on():
        raise UpdateError("Work offline is on.")
    with _lock:
        if not force and time.time() - _cache["at"] < CACHE_SECONDS:
            return _cache["release"]
    try:
        r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}, timeout=TIMEOUT)
        if r.status_code == 404:
            release = None  # no release published yet
        else:
            r.raise_for_status()
            release = _release_from(r.json())
    except requests.exceptions.RequestException as e:
        raise UpdateError("GitHub could not be reached.") from e
    with _lock:
        _cache.update(at=time.time(), release=release)
    return release


def should_show(release, prefs, now=None):
    "Whether to tell the user about this release: newer, not skipped, not postponed."
    if not release or not is_newer(release["version"]):
        return False
    if prefs.get(PREF_SKIP) == release["version"]:
        return False
    return (now if now is not None else time.time()) >= float(prefs.get(PREF_SNOOZE) or 0)


def app_path():
    "The installed Ocarina.app this process runs from, or None when it is not running from an app (a developer's copy)."
    resources = os.environ.get("RESOURCEPATH")
    if not resources:
        return None
    path = os.path.dirname(os.path.dirname(resources.rstrip("/")))
    return path if path.endswith(".app") else None


def can_install():
    path = app_path()
    return bool(path) and os.access(os.path.dirname(path), os.W_OK)


def state():
    with _lock:
        return dict(_download)


def _expected_sha(release):
    if release["sha256"]:
        return release["sha256"]
    r = requests.get(release["shaUrl"], headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    found = re.search(r"\b[0-9a-f]{64}\b", r.text)
    if not found:
        raise UpdateError("The release has no usable checksum.")
    return found.group(0)


def _fetch(release, datapath):
    folder = os.path.join(paths.cache(datapath, "update"))
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, f"Ocarina-{release['version']}.dmg")
    sha = _expected_sha(release)
    digest = hashlib.sha256()
    with requests.get(release["assetUrl"], headers={"User-Agent": USER_AGENT}, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or release["size"] or 0)
        with _lock:
            _download.update(total=total, done=0)
        with open(dest + ".part", "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                digest.update(chunk)
                with _lock:
                    _download["done"] += len(chunk)
    if digest.hexdigest() != sha:
        os.remove(dest + ".part")
        raise UpdateError("The download does not match its checksum, so it was thrown away.")
    os.replace(dest + ".part", dest)
    return dest


def start_download(release, datapath):
    "Fetch the disk image in a thread; state() shows how far it is. Returns False when one is already running."
    with _lock:
        if _download["state"] == "running":
            return False
        _download.update(state="running", done=0, total=0, error="", path="", version=release["version"])

    def run():
        try:
            path = _fetch(release, datapath)
            with _lock:
                _download.update(state="done", path=path)
        except (UpdateError, requests.exceptions.RequestException, OSError) as e:
            with _lock:
                _download.update(state="error", error=str(e) if isinstance(e, UpdateError) else "The download failed. Check the connection and try again.")

    threading.Thread(target=run, daemon=True).start()
    return True


HELPER = """#!/bin/bash
# Swaps the new Ocarina.app for the old one after Ocarina has quit; the old one is kept until the new one has started.
PID="$1"; NEW="$2"; TARGET="$3"; OLD="$3.old"
while kill -0 "$PID" 2>/dev/null; do sleep 0.3; done
rm -rf "$OLD"
if mv "$TARGET" "$OLD" && mv "$NEW" "$TARGET"; then
  xattr -dr com.apple.quarantine "$TARGET" 2>/dev/null
  open "$TARGET"
  sleep 20
  if pgrep -f "$TARGET/Contents/MacOS" >/dev/null; then rm -rf "$OLD"; else pkill -f "$TARGET/Contents/MacOS"; rm -rf "$TARGET"; mv "$OLD" "$TARGET"; open "$TARGET"; fi
else
  [ -d "$TARGET" ] || mv "$OLD" "$TARGET"
  rm -rf "$NEW"
  open "$TARGET"
fi
"""


def _stage(dmg, target):
    "Unpack the new app next to the installed one (same folder, so swapping is one rename); returns its path."
    mount = tempfile.mkdtemp(prefix="ocarina-update-")
    staged = target + ".new"
    try:
        subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-noverify", "-mountpoint", mount, dmg], check=True, capture_output=True, timeout=120)
        try:
            shutil.rmtree(staged, ignore_errors=True)
            subprocess.run(["ditto", os.path.join(mount, "Ocarina.app"), staged], check=True, capture_output=True, timeout=600)
        finally:
            subprocess.run(["hdiutil", "detach", "-force", mount], check=False, capture_output=True, timeout=60)
    finally:
        shutil.rmtree(mount, ignore_errors=True)
    subprocess.run(["codesign", "--verify", "--deep", staged], check=True, capture_output=True, timeout=120)
    return staged


def install(datapath, quit_app):
    "Unpack the downloaded app and hand over to the helper; quit_app() is called after the helper is running."
    target = app_path()
    if not target:
        raise UpdateError("Updating works in the installed Ocarina app only.")
    if not can_install():
        raise UpdateError(f"Ocarina cannot replace itself here ({os.path.dirname(target)} is not writable). Download the new version and drag it in.")
    info = state()
    if info["state"] != "done" or not os.path.exists(info["path"]):
        raise UpdateError("Download the update first.")
    try:
        staged = _stage(info["path"], target)
    except (subprocess.SubprocessError, OSError) as e:
        raise UpdateError("The update could not be unpacked, so nothing was changed.") from e
    script = os.path.join(paths.cache(datapath, "update"), "apply.sh")
    with open(script, "w", encoding="utf-8") as f:
        f.write(HELPER)
    os.chmod(script, 0o755)
    subprocess.Popen(["/bin/bash", script, str(os.getpid()), staged, target], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # pylint: disable=consider-using-with
    quit_app()
