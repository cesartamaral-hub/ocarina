"Programs from Homebrew that Ocarina uses when they are there (an app opened from the Dock has a bare PATH, so the usual folders are tried too)."

import os
import shutil

FOLDERS = ("/opt/homebrew/bin", "/usr/local/bin")


def find(name):
    "Full path of a program, or None."
    found = shutil.which(name)
    if found:
        return found
    return next((p for p in (os.path.join(d, name) for d in FOLDERS) if os.path.exists(p)), None)


def ffmpeg():
    return find("ffmpeg")
