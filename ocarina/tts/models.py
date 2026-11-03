"""
Model files: is a model installed, download it with progress, delete it.

Files live in the standard Hugging Face cache, because the MLX
library looks there. After a download "main" is pointed at the pinned
revision, so the worker can run fully offline (HF_HUB_OFFLINE=1) and
never fetches anything on its own.
"""

import json
import os
import shutil
import tempfile

from huggingface_hub import constants, snapshot_download
from tqdm.auto import tqdm

CATALOG = os.path.join(os.path.dirname(__file__), "catalog.json")


def load_catalog():
    "All models in the catalog."
    with open(CATALOG, encoding="utf-8") as f:
        return json.load(f)["models"]


def find_model(model_id):
    "The catalog entry with this id, or None."
    return next((m for m in load_catalog() if m["id"] == model_id), None)


def choose_model(requested_id=None, preferred_id=None):
    """
    The model to voice a book with: the one asked for, else the user's choice
    for the book's language, else the first installed one, else the first in the catalog.
    """
    if requested_id:
        return find_model(requested_id)  # None for an unknown id: the caller reports it
    preferred = find_model(preferred_id) if preferred_id else None
    if preferred:
        return preferred
    catalog = load_catalog()
    return next((m for m in catalog if is_installed(m)), catalog[0])


def total_bytes(model):
    "Download size of all files of a model."
    return sum(sum(r["files"].values()) for r in model["repositories"])


def _repo_dir(repo_id):
    return os.path.join(constants.HF_HUB_CACHE, "models--" + repo_id.replace("/", "--"))


def _repo_installed(repo):
    snap = os.path.join(_repo_dir(repo["id"]), "snapshots", repo["revision"])
    main = os.path.join(_repo_dir(repo["id"]), "refs", "main")
    if not os.path.exists(main):
        return False
    for name, size in repo["files"].items():
        path = os.path.join(snap, name)
        if not os.path.exists(path) or os.path.getsize(path) != size:
            return False
    return True


def is_installed(model):
    "True if every file of the model is present with the expected size."
    return all(_repo_installed(r) for r in model["repositories"])


def _progress_class(state, on_progress):
    class Progress(tqdm):
        "Counts bytes of the file downloads only (not the 'N files' bar)."

        def update(self, n=1):
            result = super().update(n)
            if self.unit == "B":
                state["done"] += n
                on_progress(min(state["done"], state["total"]), state["total"])
            return result

    return Progress


def download(model, on_progress=None):
    "Download all files of a model; on_progress(done_bytes, total_bytes)."
    state = {"done": 0, "total": total_bytes(model)}
    cb = on_progress or (lambda done, total: None)
    for repo in model["repositories"]:
        snapshot_download(
            repo["id"],
            revision=repo["revision"],
            allow_patterns=list(repo["files"]),
            tqdm_class=_progress_class(state, cb),
        )
        refs = os.path.join(_repo_dir(repo["id"]), "refs")
        os.makedirs(refs, exist_ok=True)
        with open(os.path.join(refs, "main"), "w", encoding="utf-8") as f:
            f.write(repo["revision"])
    if not is_installed(model):
        raise RuntimeError("Download finished but some files are missing or the wrong size.")
    cb(state["total"], state["total"])


def delete(model):
    "Remove the model's files from the cache (blobs shared with nothing else go too)."
    for repo in model["repositories"]:
        shutil.rmtree(_repo_dir(repo["id"]), ignore_errors=True)


class FolderError(Exception):
    "The folder does not contain every file of the model."


def _index_folder(folder):
    "Map (file name, size) to a path for every file below the folder."
    found = {}
    for root, _dirs, names in os.walk(folder, followlinks=True):
        for name in names:
            path = os.path.join(root, name)
            try:
                found.setdefault((name, os.path.getsize(path)), path)
            except OSError:
                continue
    return found


def find_import_files(model, folder):
    """
    Match the model's files to files in a folder by name and exact size, however
    the folder is laid out (flat, per-repo subfolders, or a Hugging Face cache).
    Returns [(repo, name, source path)]; raises FolderError listing what is missing.
    """
    if not os.path.isdir(folder):
        raise FolderError("That folder does not exist.")
    index = _index_folder(folder)
    matches, missing = [], []
    for repo in model["repositories"]:
        for name, size in repo["files"].items():
            path = index.get((name, size))
            if path:
                matches.append((repo, name, path))
            else:
                missing.append(f"{name} ({size} bytes, from {repo['id']})")
    if missing:
        raise FolderError("The folder is missing: " + "; ".join(missing))
    return matches


def import_from_folder(model, folder, on_progress=None):
    "Copy the model's files from a folder into the cache; on_progress(done_bytes, total_bytes)."
    matches = find_import_files(model, folder)
    total, done = total_bytes(model), 0
    cb = on_progress or (lambda done, total: None)
    for repo, name, src in matches:
        snap = os.path.join(_repo_dir(repo["id"]), "snapshots", repo["revision"])
        os.makedirs(snap, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=snap, suffix=".part")
        os.close(fd)
        shutil.copyfile(src, tmp)
        os.replace(tmp, os.path.join(snap, name))  # never leaves a half-copied file
        done += repo["files"][name]
        cb(done, total)
    for repo in model["repositories"]:
        refs = os.path.join(_repo_dir(repo["id"]), "refs")
        os.makedirs(refs, exist_ok=True)
        with open(os.path.join(refs, "main"), "w", encoding="utf-8") as f:
            f.write(repo["revision"])
    if not is_installed(model):
        raise RuntimeError("Copy finished but some files are missing or the wrong size.")
