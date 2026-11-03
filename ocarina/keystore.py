"""
Secrets the app must remember (a DeepL API key), kept apart from the preferences.

Preferences are sent to the web page in full; this file is never: the page only learns whether a key is saved
and its last characters. It is created readable by you alone.
"""

import json
import os
import tempfile


def path_for(datapath):
    "Where the secrets live."
    return os.path.join(datapath, "ocarina_secrets.json")


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get(datapath, name):
    "A saved secret, or None."
    return _load(path_for(datapath)).get(name) or None


def hint(datapath, name):
    "Enough of a secret to recognise it ('…:fx'), or None if none is saved."
    value = get(datapath, name)
    return ("…" + value[-4:]) if value else None


def put(datapath, name, value):
    "Save a secret, or remove it when value is empty."
    path = path_for(datapath)
    data = _load(path)
    if value:
        data[name] = value
    else:
        data.pop(name, None)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")  # mkstemp creates it 0600
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)
