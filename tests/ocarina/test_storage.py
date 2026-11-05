"""
The Storage page: what each model and each kind of data takes on disk, and clearing the caches.
"""

import os

import pytest
from huggingface_hub import constants

from ocarina import storage
from ocarina.api import jobs

URL = "/ocarina/api/storage"
CHATTERBOX = "mlx-community/chatterbox-multilingual-v3"
TOKENIZER = "mlx-community/S3TokenizerV2"
QWEN = "mlx-community/Qwen3-4B-Instruct-2507-4bit"


def _blob(root, repo, name, size, shared=False):
    "A file in a repository's blobs; shared=True puts it in the cache-wide store and links to it, as new downloads do."
    folder = os.path.join(root, "models--" + repo.replace("/", "--"), "blobs")
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, name)
    if shared:
        store = os.path.join(root, "blobs", name[:2])
        os.makedirs(store, exist_ok=True)
        real = os.path.join(store, name)
        with open(real, "wb") as f:
            f.write(b"x" * size)
        os.symlink(real, target)
        return real
    with open(target, "wb") as f:
        f.write(b"x" * size)
    return target


@pytest.fixture
def hub(tmp_path, monkeypatch):
    "A Hugging Face cache with known contents, in place of the real one."
    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(tmp_path))
    _blob(tmp_path, CHATTERBOX, "a", 1000)
    _blob(tmp_path, TOKENIZER, "b", 200)
    _blob(tmp_path, QWEN, "c", 500)
    _blob(tmp_path, QWEN, "d.incomplete", 50)  # an unfinished download is on disk too
    _blob(tmp_path, "someone/else-model", "e", 7000)  # not Ocarina's
    return tmp_path


def test_each_model_is_measured_by_its_own_repositories(client, hub):
    data = client.get(URL).json
    by_id = {m["id"]: m for m in data["models"]}
    assert by_id["chatterbox-multilingual-v3-mlx"]["bytes"] == 1200  # both of its repositories
    assert by_id["qwen3-4b-instruct-mlx"]["bytes"] == 550
    assert by_id["chatterbox-multilingual-v3-mlx"]["kind"] == "speech" and by_id["qwen3-4b-instruct-mlx"]["kind"] == "text"
    assert "audio8-realistic-mlx" not in by_id  # nothing on disk: not listed
    assert by_id["qwen3-4b-instruct-mlx"]["installed"] is False  # files are there, but not all of them


def test_groups_total_and_the_space_that_is_not_ocarinas(client, hub):
    data = client.get(URL).json
    sizes = {g["kind"]: g["bytes"] for g in data["groups"]}
    assert sizes == {"speech": 1200, "text": 550, "aligner": 0, "transcriber": 0}
    assert data["modelsBytes"] == 1750
    assert data["otherHubBytes"] == 7000
    assert data["hubPath"] == str(hub)
    assert [g["label"] for g in data["groups"]] == ["Voice models", "Translation models", "Audio sync model", "Transcription model"]


def test_data_folders_are_measured_and_only_caches_can_be_cleared(app, client, hub):
    datapath = app.env_config.datapath
    os.makedirs(os.path.join(datapath, "cache", "translation", "ab"), exist_ok=True)
    with open(os.path.join(datapath, "cache", "translation", "ab", "x.json"), "wb") as f:
        f.write(b"y" * 300)
    data = client.get(URL).json
    items = {d["id"]: d for d in data["data"]}
    assert items["translations"]["bytes"] >= 300 and items["translations"]["clearable"] is True
    assert items["recordings"]["clearable"] is False and items["library"]["clearable"] is False
    assert data["dataBytes"] == sum(d["bytes"] for d in data["data"]) and data["freeBytes"] > 0


def test_clearing_a_cache_empties_it_and_says_how_much_was_freed(app, client, hub):
    datapath = app.env_config.datapath
    folder = os.path.join(datapath, "cache", "tts")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "s.wav"), "wb") as f:
        f.write(b"z" * 400)
    r = client.post(f"{URL}/clear", json={"what": "sentence_audio"})
    assert r.status_code == 200 and r.json["freed"] >= 400
    assert os.path.isdir(folder) and os.listdir(folder) == []  # the folder is still there for the next sentence


def test_what_you_made_yourself_cannot_be_cleared(client, hub):
    assert client.post(f"{URL}/clear", json={"what": "recordings"}).status_code == 400
    assert client.post(f"{URL}/clear", json={"what": "library"}).status_code == 400
    assert client.post(f"{URL}/clear", json={}).status_code == 400


def test_nothing_is_cleared_while_a_job_runs(client, hub, monkeypatch):
    monkeypatch.setattr(jobs, "active", lambda **match: [{"id": "j"}])
    r = client.post(f"{URL}/clear", json={"what": "temp"})
    assert r.status_code == 409 and r.json["code"] == "busy"


def test_a_missing_or_unreadable_hub_is_not_an_error(client, tmp_path, monkeypatch):
    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(tmp_path / "nope"))
    data = client.get(URL).json
    assert data["models"] == [] and data["modelsBytes"] == 0 and data["otherHubBytes"] == 0


def test_path_bytes_does_not_count_links_twice(tmp_path):
    (tmp_path / "blob").write_bytes(b"x" * 100)
    os.symlink(tmp_path / "blob", tmp_path / "link")
    assert storage.path_bytes(str(tmp_path)) == 100


def test_big_files_in_the_shared_store_are_counted_through_their_links(client, tmp_path, monkeypatch):
    "New downloads keep their big files in one store for the whole cache; a model's size follows the links."
    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(tmp_path))
    _blob(tmp_path, QWEN, "abcdef1", 9000, shared=True)
    _blob(tmp_path, QWEN, "small", 100)
    _blob(tmp_path, "someone/else-model", "ffeedd2", 4000, shared=True)
    data = client.get(URL).json
    assert {m["id"]: m["bytes"] for m in data["models"]} == {"qwen3-4b-instruct-mlx": 9100}
    assert data["otherHubBytes"] == 4000 and data["leftoverBytes"] == 0


def test_a_file_two_repositories_share_is_counted_once_for_a_model(client, tmp_path, monkeypatch):
    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(tmp_path))
    real = _blob(tmp_path, CHATTERBOX, "abcdef1", 5000, shared=True)
    folder = os.path.join(tmp_path, "models--" + TOKENIZER.replace("/", "--"), "blobs")
    os.makedirs(folder)
    os.symlink(real, os.path.join(folder, "abcdef1"))
    assert {m["id"]: m["bytes"] for m in client.get(URL).json["models"]}["chatterbox-multilingual-v3-mlx"] == 5000


def test_deleting_a_model_frees_its_shared_files_but_not_ones_another_model_uses(tmp_path, monkeypatch):
    from ocarina.tts import models as model_files  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(tmp_path))
    own = _blob(tmp_path, QWEN, "abcdef1", 9000, shared=True)
    common = _blob(tmp_path, QWEN, "abcdef2", 300, shared=True)
    folder = os.path.join(tmp_path, "models--" + "someone/else-model".replace("/", "--"), "blobs")
    os.makedirs(folder)
    os.symlink(common, os.path.join(folder, "abcdef2"))  # another repository uses this one too
    model_files.delete(model_files.find_model("qwen3-4b-instruct-mlx"))
    assert not os.path.exists(own) and os.path.exists(common)
    assert not os.path.exists(os.path.join(tmp_path, "models--" + QWEN.replace("/", "--")))


def test_what_deleted_models_left_behind_is_shown_and_can_be_freed(client, tmp_path, monkeypatch):
    "Older versions removed only the model's folder, leaving the big files in the shared store."
    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(tmp_path))
    kept = _blob(tmp_path, QWEN, "abcdef1", 1000, shared=True)
    os.makedirs(tmp_path / "blobs" / "zz")
    stray = tmp_path / "blobs" / "zz" / "zzstray"
    stray.write_bytes(b"s" * 6000)
    assert client.get(URL).json["leftoverBytes"] == 6000
    r = client.post(f"{URL}/clear", json={"what": "leftovers"})
    assert r.status_code == 200 and r.json["freed"] == 6000 and r.json["leftoverBytes"] == 0
    assert not stray.exists() and os.path.exists(kept)
