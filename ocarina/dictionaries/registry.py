"""
Which packs there are, which are on, and in what order they are asked.

Packs are files: the ones that come with the app in builtin/ (read only), the user's in <data folder>/dictionaries. The choice (on or off, and
the order) is kept in the preferences: `dictionaries.order` (a list of pack ids, first asked first) and `dictionaries.off` (ids switched off).
A pack that is in neither list is new: packs the user added or downloaded come before the built-in ones.
"""

import glob
import os

from ocarina import prefs
from ocarina.dictionaries.pack import Pack

BUILTIN_DIR = os.path.join(os.path.dirname(__file__), "builtin")
KIND_RANK = {"stardict": 0, "wiktionary": 1, "wikdict": 2, "builtin": 2}
_open = {}  # path -> (mtime, Pack): a pack is opened once and again when the file changes


def user_dir(datapath):
    return os.path.join(datapath, "dictionaries")


def _pack(path):
    mtime = os.path.getmtime(path)
    kept = _open.get(path)
    if kept and kept[0] == mtime:
        return kept[1]
    if kept:
        kept[1].close()
    try:
        found = Pack(path)
    except Exception:  # pylint: disable=broad-exception-caught  # a file that is not a pack is left out
        return None
    _open[path] = (mtime, found)
    return found


def all_packs(datapath):
    "Every pack there is, in the order they are asked (the user's order, then the new ones by kind)."
    found = []
    for folder in (user_dir(datapath), BUILTIN_DIR):
        for path in sorted(glob.glob(os.path.join(folder, "*.sqlite"))):
            pack = _pack(path)
            if pack is not None and all(p.id != pack.id for p in found):
                found.append(pack)
    saved = prefs.load(prefs.path_for(datapath)).get("dictionaries.order") or []
    rank = {pack_id: i for i, pack_id in enumerate(saved)}
    return sorted(found, key=lambda p: (0, rank[p.id]) if p.id in rank else (1, KIND_RANK.get(p.meta.get("kind"), 3), p.name))


def switched_off(datapath):
    return set(prefs.load(prefs.path_for(datapath)).get("dictionaries.off") or [])


def active(datapath, code):
    "The packs of a language that are on, in order."
    off = switched_off(datapath)
    return [p for p in all_packs(datapath) if p.language == code and p.id not in off]


def listing(datapath):
    "All packs for the settings page: info, and whether each is on, in order; builtin ones cannot be deleted."
    off = switched_off(datapath)
    return [{**p.info(), "on": p.id not in off, "removable": os.path.dirname(p.path) != BUILTIN_DIR} for p in all_packs(datapath)]


def save_choice(datapath, order=None, off=None):
    changes = {}
    if order is not None:
        changes["dictionaries.order"] = [str(i) for i in order]
    if off is not None:
        changes["dictionaries.off"] = sorted({str(i) for i in off})
    prefs.update(prefs.path_for(datapath), changes)


def remove(datapath, pack_id):
    "Delete a pack of the user's; returns False for the built-in ones and for ids that do not exist."
    for pack in all_packs(datapath):
        if pack.id == pack_id and os.path.dirname(pack.path) != BUILTIN_DIR:
            pack.close()
            _open.pop(pack.path, None)
            os.remove(pack.path)
            return True
    return False
