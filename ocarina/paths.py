"""
Where Ocarina keeps its files, in one place.

    <data folder>/
        models/         the downloaded models, one folder each (models--<owner>--<name>), complete in themselves: copy one in or
                        out to share it
        dictionaries/   the dictionary packs, one .sqlite file each: copy a file in or out
        cache/          everything that can be made again (tts, pronounce, translation, dictionary, temp)
        ocarina.db, useraudio, userimages, backups, ocarina_prefs.json ...   your library and settings

configure() is called when the app starts: it moves what older versions kept elsewhere (the caches next to the library, the
models in the shared Hugging Face folder) and points Hugging Face at models/.
"""

import os
import shutil
import subprocess

CACHES = {  # the old folder -> the name inside cache/
    "tts_cache": "tts",
    "pronounce_cache": "pronounce",
    "translation_cache": "translation",
    "dictionary_cache": "dictionary",
    "temp": "temp",
}
OTHER_APPS = ("models--handy-computer--", "models--hf-internal-testing--")  # in the shared Hugging Face folder, not ours

_datapath = None


def cache(datapath, name):
    "<data folder>/cache/<name> (tts, pronounce, translation, dictionary, temp)."
    return os.path.join(datapath, "cache", name)


def models_dir(datapath):
    return os.path.join(datapath, "models")


def _move_caches(datapath):
    for old, new in CACHES.items():
        src, dst = os.path.join(datapath, old), cache(datapath, new)
        if os.path.isdir(src) and not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.rename(src, dst)


def _clone(src, dst):
    "A copy that takes no extra space on APFS (a clone), a plain copy elsewhere. Follows links."
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    done = subprocess.run(["cp", "-c", src, dst], capture_output=True, check=False)
    if done.returncode != 0:
        shutil.copyfile(src, dst)


def _copy_repo(src, dst):
    "One cached repository, made complete: every link into the shared blob store becomes a file of its own."
    shutil.copytree(src, dst, symlinks=True, copy_function=lambda a, b: _clone(a, b) if not os.path.islink(a) else os.symlink(os.readlink(a), b))
    blobs = os.path.join(dst, "blobs")
    for name in os.listdir(blobs) if os.path.isdir(blobs) else ():
        path = os.path.join(blobs, name)
        if os.path.islink(path):
            target = os.path.realpath(os.path.join(src, "blobs", name))
            os.remove(path)
            _clone(target, path)


def _bring_models(datapath, old):
    "The models of the shared Hugging Face folder, copied (not moved: other tools may use them) once, the first time."
    dst = models_dir(datapath)
    if os.path.exists(dst) or not old or not os.path.isdir(old):
        os.makedirs(dst, exist_ok=True)
        return
    part = dst + ".part"
    shutil.rmtree(part, ignore_errors=True)
    os.makedirs(part)
    for name in sorted(os.listdir(old)):
        if name.startswith("models--") and not name.startswith(OTHER_APPS) and os.path.isdir(os.path.join(old, name)):
            _copy_repo(os.path.join(old, name), os.path.join(part, name))
    os.rename(part, dst)


def configure(datapath, bring_models=True):
    "Tidy the data folder and point Hugging Face at models/. Safe to call again."
    global _datapath  # pylint: disable=global-statement
    if not datapath:
        return
    from huggingface_hub import constants  # pylint: disable=import-outside-toplevel

    if _datapath != datapath:
        old = None if _datapath is not None or os.environ.get("OCARINA_NO_MODEL_MIGRATION") else constants.HF_HUB_CACHE
        _move_caches(datapath)
        if bring_models and old and os.path.abspath(old) != os.path.abspath(models_dir(datapath)):
            _bring_models(datapath, old)
        os.makedirs(models_dir(datapath), exist_ok=True)
        _datapath = datapath
    folder = models_dir(datapath)
    constants.HF_HUB_CACHE = constants.HUGGINGFACE_HUB_CACHE = folder
    os.environ["HF_HUB_CACHE"] = os.environ["HUGGINGFACE_HUB_CACHE"] = folder  # the model workers start with these
