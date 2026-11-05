"Programs Ocarina uses: its own copy of ffmpeg inside the app, else Homebrew's when it is there (an app opened from the Dock has a bare PATH, so the usual folders are tried too)."

import os
import shutil

FOLDERS = ("/opt/homebrew/bin", "/usr/local/bin")


def bundled_dir():
    "The folder of programs inside the app (Contents/Resources/bin), or None when not running from the app."
    folder = os.path.join(os.environ.get("RESOURCEPATH", ""), "bin")
    return folder if os.environ.get("RESOURCEPATH") and os.path.isdir(folder) else None


def find(name):
    "Full path of a program, or None. The one inside the app comes first."
    own = bundled_dir()
    if own and os.access(os.path.join(own, name), os.X_OK):
        return os.path.join(own, name)
    found = shutil.which(name)
    if found:
        return found
    return next((p for p in (os.path.join(d, name) for d in FOLDERS) if os.path.exists(p)), None)


def ffmpeg():
    return find("ffmpeg")
