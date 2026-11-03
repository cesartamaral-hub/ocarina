"""
Model files: the catalog, is a model installed, download it with progress, delete it.

The catalog is catalog.json (shipped) plus the user's own entries in <data folder>/models.json,
which the app writes when a model is added from Hugging Face. Entries have the same shape:
pinned revisions and exact file sizes, so "installed" and offline loading work the same way.

Files live in the standard Hugging Face cache, because the MLX
library looks there. After a download "main" is pointed at the pinned
revision, so the worker can run fully offline (HF_HUB_OFFLINE=1) and
never fetches anything on its own.
"""

import json
import os
import re
import shutil
import tempfile

from huggingface_hub import HfApi, constants, snapshot_download
from tqdm.auto import tqdm

CATALOG = os.path.join(os.path.dirname(__file__), "catalog.json")

# How the worker talks to a model: the engine decides which arguments generate() gets.
ENGINES = {
    "mlx-chatterbox": "Chatterbox style: imitates a voice clip",
    "mlx-audio8": "Audio8 style: own voice; imitates a clip only with the words spoken in it",
}
LANGUAGE_CODES = ("nl", "pl", "fr")
_user_catalog = None  # path of models.json, set by configure()


def configure(datapath):
    "Where the user's own catalog entries live (called once when the app starts)."
    global _user_catalog  # pylint: disable=global-statement
    _user_catalog = os.path.join(datapath, "models.json") if datapath else None


def _load_user_models():
    if not _user_catalog or not os.path.exists(_user_catalog):
        return []
    try:
        with open(_user_catalog, encoding="utf-8") as f:
            models = json.load(f)["models"]
    except (OSError, ValueError, KeyError):
        return []  # an unreadable file must not take the shipped models down with it
    return [{**m, "custom": True} for m in models if isinstance(m, dict)]


def _save_user_models(models):
    os.makedirs(os.path.dirname(_user_catalog), exist_ok=True)
    plain = [{k: v for k, v in m.items() if k != "custom"} for m in models]
    with open(_user_catalog, "w", encoding="utf-8") as f:
        json.dump({"schema": 1, "models": plain}, f, indent=2, ensure_ascii=False)


def load_catalog():
    "All models: the shipped ones, then the user's own."
    with open(CATALOG, encoding="utf-8") as f:
        shipped = json.load(f)["models"]
    ids = {m["id"] for m in shipped}
    return shipped + [m for m in _load_user_models() if m.get("id") and m["id"] not in ids]


def find_model(model_id):
    "The catalog entry with this id, or None."
    return next((m for m in load_catalog() if m["id"] == model_id), None)


def kind_of(model):
    'What a model is for: "speech" (it voices books) or "text" (it translates sentences).'
    return model.get("kind", "speech")


def speech_models():
    "The models that can voice a book."
    return [m for m in load_catalog() if kind_of(m) == "speech"]


def choose_model(requested_id=None, preferred_id=None):
    """
    The model to voice a book with: the one asked for, else the user's choice
    for the book's language, else the first installed one, else the first in the catalog.
    Only speech models count; None if the one asked for is unknown or not a speech model.
    """
    if requested_id:
        asked = find_model(requested_id)
        return asked if asked and kind_of(asked) == "speech" else None  # the caller reports it
    preferred = find_model(preferred_id) if preferred_id else None
    if preferred and kind_of(preferred) == "speech":
        return preferred
    catalog = speech_models()
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
        """
        Counts bytes of the file downloads only: not the 'N files' bar, and not the "Reconstructing"
        bar that Hugging Face's fast downloader shows for the same bytes a second time.
        """

        def update(self, n=1):
            result = super().update(n)
            if self.unit == "B" and not str(self.desc or "").startswith("Reconstructing"):
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


class HubError(Exception):
    "A model can't be added from Hugging Face; the message says why."


REPO_ID = re.compile(r"^[A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]*$")
SKIP_FILES = (".gitattributes",)


def lookup_hub_repo(repo_id):
    "Latest revision, license and file sizes of a Hugging Face model repository (needs the internet)."
    if not REPO_ID.match(repo_id or ""):
        raise HubError("Give the repository as owner/name, for example mlx-community/some-model.")
    try:
        info = HfApi().model_info(repo_id, files_metadata=True)
    except Exception as e:  # pylint: disable=broad-exception-caught
        raise HubError(f"Can't look up {repo_id} ({type(e).__name__}). Check the name and your connection.") from e
    files = {
        s.rfilename: s.size
        for s in info.siblings
        if s.size and s.rfilename not in SKIP_FILES and not s.rfilename.lower().endswith(".md")
    }
    if not any(name.endswith(".safetensors") for name in files):
        raise HubError("That repository has no .safetensors weights, so it can't be loaded here.")
    card = info.card_data.to_dict() if info.card_data else {}
    return {
        "repo": repo_id,
        "revision": info.sha,
        "license": str(card.get("license") or "unknown"),
        "files": files,
        "totalBytes": sum(files.values()),
    }


def add_custom_model(repo_id, engine, languages, name=None):
    "Add a Hugging Face model to the user's catalog (pinned to its latest revision) and return the entry."
    if engine not in ENGINES:
        raise HubError("Choose how the model is used.")
    languages = [code for code in languages if code in LANGUAGE_CODES]
    if not languages:
        raise HubError("Choose at least one language.")
    found = lookup_hub_repo(repo_id)
    model_id = "custom-" + re.sub(r"[^a-z0-9]+", "-", repo_id.lower()).strip("-")
    if find_model(model_id):
        raise HubError("That model is already in the list.")
    entry = {
        "id": model_id,
        "name": (name or repo_id.split("/")[1]).strip()[:80],
        "description": f"From Hugging Face: {repo_id}.",
        "engine": engine,
        "repositories": [{"id": repo_id, "revision": found["revision"], "files": found["files"]}],
        "license": found["license"],
        "languages": languages,
    }
    _save_user_models([m for m in _load_user_models()] + [entry])
    return {**entry, "custom": True}


def remove_custom_model(model_id):
    "Take a user-added model out of the catalog (its files are deleted separately); False if it isn't one."
    models = _load_user_models()
    kept = [m for m in models if m["id"] != model_id]
    if len(kept) == len(models):
        return False
    _save_user_models(kept)
    return True
