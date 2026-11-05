"Where the files live (ocarina/paths.py): the caches under cache/, the models in models/, complete in themselves."

import os

from huggingface_hub import constants

from ocarina import paths


def _write(path, text="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def test_old_caches_move_into_the_cache_folder(tmp_path):
    for old in paths.CACHES:
        _write(str(tmp_path / old / "a" / "f.txt"))
    paths._move_caches(str(tmp_path))  # pylint: disable=protected-access
    for old, new in paths.CACHES.items():
        assert not (tmp_path / old).exists() and (tmp_path / "cache" / new / "a" / "f.txt").exists()


def test_a_model_is_copied_with_its_files_not_links_into_the_shared_store(tmp_path):
    hub = tmp_path / "hub"
    shared = hub / "blobs" / "ab" / "big"
    _write(str(shared), "weights")
    repo = hub / "models--org--name"
    _write(str(repo / "blobs" / "small"), "cfg")
    os.symlink(str(shared), str(repo / "blobs" / "big"))
    os.makedirs(repo / "snapshots" / "rev")
    os.symlink("../../blobs/big", str(repo / "snapshots" / "rev" / "model.safetensors"))
    _write(str(hub / "models--handy-computer--other" / "blobs" / "x"))
    data = tmp_path / "data"
    os.makedirs(data)
    paths._bring_models(str(data), str(hub))  # pylint: disable=protected-access
    copied = data / "models" / "models--org--name"
    assert not (data / "models" / "models--handy-computer--other").exists()
    assert not os.path.islink(copied / "blobs" / "big")
    assert (copied / "snapshots" / "rev" / "model.safetensors").read_text() == "weights"
    assert (repo / "blobs" / "big").is_symlink()  # the original is left as it was


def test_hugging_face_is_pointed_at_the_models_folder(tmp_path):
    before = constants.HF_HUB_CACHE
    try:
        paths.configure(str(tmp_path), bring_models=False)
        assert constants.HF_HUB_CACHE == str(tmp_path / "models") and os.environ["HF_HUB_CACHE"] == str(tmp_path / "models")
    finally:
        constants.HF_HUB_CACHE = before
        paths._datapath = None  # pylint: disable=protected-access
