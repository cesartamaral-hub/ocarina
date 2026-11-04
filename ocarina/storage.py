"""
How much disk space Ocarina's models and data use, and clearing the caches that can be made again.

Models live in the Hugging Face cache (shared with other programs), one folder per repository; a folder's size is the
size of its blobs (the snapshot entries are links to them), so a model's size here is what deleting it frees.
"""

import os
import shutil

from huggingface_hub import constants

from ocarina.tts import models as model_files

KIND_LABELS = {"speech": "Voice models", "text": "Translation models", "aligner": "Audio sync model", "transcriber": "Transcription model"}

# What is kept in the data folder: id, folder or file name, what it is, and whether it can be cleared (made again as needed).
DATA_ITEMS = [
    ("recordings", "useraudio", "Audio", "Your recordings and the audio Ocarina made for your books.", False),
    ("pictures", "userimages", "Pictures", "Pictures you added to words.", False),
    ("library", "ocarina.db", "Library", "Your books, words and statuses.", False),
    ("backups", "backups", "Backups", "Copies of your library.", False),
    ("sentence_audio", "tts_cache", "Voiced sentences", "Sentences already voiced, so making a book's audio again is quick. Cleared, they are voiced again when needed.", True),
    ("translations", "translation_cache", "Saved translations", "Translations you have seen, so they work offline. Cleared, they are asked for again.", True),
    ("dictionary", "dictionary_cache", "Saved definitions", "Definitions from Wiktionary. Cleared, they are fetched again.", True),
    ("temp", "temp", "Temporary files", "Leftovers of previews and checks.", True),
]


def path_bytes(path):
    "Size of a file, or of everything below a folder (links are not followed, so nothing is counted twice)."
    try:
        if os.path.islink(path):
            return 0
        if os.path.isfile(path):
            return os.path.getsize(path)
        total = 0
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.is_symlink():
                    continue
                total += entry.stat().st_size if entry.is_file(follow_symlinks=False) else path_bytes(entry.path)
        return total
    except OSError:
        return 0


def _repo_folder(repo_id):
    return os.path.join(constants.HF_HUB_CACHE, "models--" + repo_id.replace("/", "--"))


def _blob_sizes(folder):
    """
    {where the file really is: size} for a cached repository folder. Large files are links into a store shared by the
    whole cache, so the link is followed; a download that was not finished counts too.
    """
    sizes = {}
    blobs = os.path.join(folder, "blobs")
    try:
        names = os.listdir(blobs)
    except OSError:
        return sizes
    for name in names:
        path = os.path.join(blobs, name)
        try:
            sizes[os.path.realpath(path)] = os.path.getsize(path)  # getsize follows a link
        except OSError:
            continue  # a link to nothing
    return sizes


def repo_bytes(repo_id):
    "Disk space of one cached repository: what deleting it frees."
    return sum(_blob_sizes(_repo_folder(repo_id)).values())


def model_bytes(model):
    "Disk space of a model (all its repositories; a file two of them share counts once)."
    sizes = {}
    for repo in model["repositories"]:
        sizes.update(_blob_sizes(_repo_folder(repo["id"])))
    return sum(sizes.values())


def other_hub_bytes(known_repo_ids):
    "Disk space in the Hugging Face cache that no model of Ocarina's uses (and that Ocarina never deletes)."
    known = {os.path.basename(_repo_folder(r)) for r in known_repo_ids}
    mine = set()
    for repo_id in known_repo_ids:
        mine |= set(_blob_sizes(_repo_folder(repo_id)))
    theirs = {}
    try:
        with os.scandir(constants.HF_HUB_CACHE) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False) and entry.name not in known and "--" in entry.name:
                    theirs.update(_blob_sizes(entry.path))
    except OSError:
        pass
    return sum(size for path, size in theirs.items() if path not in mine)


def leftover_files():
    "[(path, size)] of files in the shared blob store that no repository links to: what deleted models left behind."
    shared = os.path.join(constants.HF_HUB_CACHE, "blobs")
    kept = model_files.referenced_blobs()
    found = []
    for root, _dirs, names in os.walk(shared):
        for name in names:
            path = os.path.join(root, name)
            if not name.startswith(".") and os.path.realpath(path) not in kept:
                try:
                    found.append((path, os.path.getsize(path)))
                except OSError:
                    continue
    return found


def models_usage():
    "Every model with something on disk: [{id, name, kind, installed, bytes, custom}], biggest first within its kind."
    rows = []
    for model in model_files.load_catalog():
        size = model_bytes(model)
        if size > 0:
            rows.append(
                {
                    "id": model["id"],
                    "name": model["name"],
                    "kind": model_files.kind_of(model),
                    "installed": model_files.is_installed(model),
                    "bytes": size,
                    "custom": bool(model.get("custom")),
                }
            )
    return sorted(rows, key=lambda r: (list(KIND_LABELS).index(r["kind"]) if r["kind"] in KIND_LABELS else 9, -r["bytes"]))


def summary(datapath):
    "Everything the Storage page shows."
    rows = models_usage()
    groups = [
        {"kind": kind, "label": label, "bytes": sum(r["bytes"] for r in rows if r["kind"] == kind), "count": sum(1 for r in rows if r["kind"] == kind)}
        for kind, label in KIND_LABELS.items()
    ]
    repos = [r["id"] for m in model_files.load_catalog() for r in m["repositories"]]
    data = [
        {"id": key, "label": label, "description": text, "bytes": path_bytes(os.path.join(datapath, name)), "clearable": clearable}
        for key, name, label, text, clearable in DATA_ITEMS
    ]
    leftovers = sum(size for _, size in leftover_files())
    free = None
    try:
        free = shutil.disk_usage(datapath).free
    except OSError:
        pass
    return {
        "models": rows,
        "groups": groups,
        "modelsBytes": sum(r["bytes"] for r in rows),
        "otherHubBytes": other_hub_bytes(repos),
        "leftoverBytes": leftovers,
        "hubPath": constants.HF_HUB_CACHE,
        "data": data,
        "dataBytes": sum(d["bytes"] for d in data),
        "freeBytes": free,
    }


def clear(datapath, key):
    "Empty one of the caches that can be made again; returns the bytes freed, or None if `key` is not one of them."
    if key == "leftovers":
        found = leftover_files()
        for path, _size in found:
            try:
                os.remove(path)
            except OSError:
                pass
        return sum(size for _, size in found)
    item = next((i for i in DATA_ITEMS if i[0] == key and i[4]), None)
    if item is None:
        return None
    folder = os.path.join(datapath, item[1])
    freed = path_bytes(folder)
    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(folder, exist_ok=True)
    return freed
