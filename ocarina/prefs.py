"""
User preferences (playback speed and similar), kept in a small JSON file in the data folder.

They live here, not in the web view's own storage: the packaged app picks a new port on every
launch, and the browser storage of a different port is a different, empty storage.
"""

import json
import os
import tempfile


def path_for(datapath):
    "Where the preferences file lives."
    return os.path.join(datapath, "ocarina_prefs.json")


def load(path):
    "All preferences; an empty dict if there are none yet or the file is unreadable."
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def update(path, values):
    "Merge values into the saved preferences, write them, and return all of them."
    merged = {**load(path), **values}
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)  # never leaves a half-written file
    return merged
