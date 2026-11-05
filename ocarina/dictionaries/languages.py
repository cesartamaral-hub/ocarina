"""What the dictionaries catalog knows of each language (catalog.json): its name, and which dictionaries exist for it and how big they are."""

import json
import os

CATALOG = os.path.join(os.path.dirname(__file__), "catalog.json")
_cache = {}


def data():
    if not _cache:
        with open(CATALOG, encoding="utf-8") as f:
            _cache.update(json.load(f))
    return _cache


def name(code):
    return data()["languages"].get(code, {}).get("name", code.upper())


def bundled():
    "The languages whose small dictionary (WikDict) comes with the app."
    return list(data()["bundled"])
