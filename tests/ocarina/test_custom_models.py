"""
Models added by the user (models.json): look up, add, list, remove.
"""

import os
from types import SimpleNamespace

import pytest

from ocarina.tts import models as model_files

MODELS = "/ocarina/api/tts/models"


def _info(files=None, sha="abc123", license_="mit"):
    files = files or {"model.safetensors": 1000, "config.json": 50, "README.md": 9, ".gitattributes": 3}
    return SimpleNamespace(
        sha=sha,
        siblings=[SimpleNamespace(rfilename=n, size=s) for n, s in files.items()],
        card_data=SimpleNamespace(to_dict=lambda: {"license": license_}),
    )


@pytest.fixture(autouse=True)
def hub(app, monkeypatch):
    "A fake Hugging Face, and no models.json before or after each test."
    path = os.path.join(app.env_config.datapath, "models.json")
    if os.path.exists(path):
        os.remove(path)
    state = {"info": _info(), "asked": []}

    class FakeApi:
        def model_info(self, repo, files_metadata=False):  # pylint: disable=unused-argument
            state["asked"].append(repo)
            if state["info"] is None:
                raise OSError("offline")
            return state["info"]

    monkeypatch.setattr(model_files, "HfApi", FakeApi)
    yield state
    if os.path.exists(path):
        os.remove(path)


def test_lookup_reports_revision_license_and_size(client, hub):
    "The look-up leaves out README and git files and counts the rest."
    r = client.post(f"{MODELS}/lookup", json={"repo": "someone/some-model"})
    assert r.status_code == 200
    assert (r.json["revision"], r.json["license"], r.json["files"], r.json["totalBytes"]) == ("abc123", "mit", 2, 1050)
    assert hub["asked"] == ["someone/some-model"]


def test_lookup_errors_are_readable(client, hub):
    "A bad name, no network, and a repository without weights are explained."
    assert "owner/name" in client.post(f"{MODELS}/lookup", json={"repo": "not a repo"}).json["error"]
    assert "owner/name" in client.post(f"{MODELS}/lookup", json={"repo": "../../etc/passwd"}).json["error"]
    hub["info"] = None
    assert "connection" in client.post(f"{MODELS}/lookup", json={"repo": "a/b"}).json["error"]
    hub["info"] = _info(files={"config.json": 5})
    assert "safetensors" in client.post(f"{MODELS}/lookup", json={"repo": "a/b"}).json["error"]


def test_added_model_is_listed_pinned_and_survives(client, app):
    "An added model appears after the shipped ones, flagged custom, with its pinned files, and is saved to models.json."
    r = client.post(f"{MODELS}/custom", json={"repo": "someone/Some-Model", "engine": "mlx-audio8", "languages": ["nl", "xx"], "name": "Mijn model"})
    assert r.status_code == 201 and r.json["id"] == "custom-someone-some-model"
    listed = client.get(MODELS).json
    mine = listed[-1]
    assert mine["custom"] is True and mine["name"] == "Mijn model" and mine["languages"] == ["nl"]
    assert mine["repositories"][0]["revision"] == "abc123" and mine["sizeBytes"] == 1050 and mine["installed"] is False
    assert "custom" not in listed[0]
    assert os.path.exists(os.path.join(app.env_config.datapath, "models.json"))
    assert model_files.find_model("custom-someone-some-model")["engine"] == "mlx-audio8"


def test_adding_checks_engine_languages_and_duplicates(client):
    "Unknown engines, no language, and the same model twice are refused."
    body = {"repo": "a/b", "engine": "mlx-chatterbox", "languages": ["pl"]}
    assert client.post(f"{MODELS}/custom", json={**body, "engine": "nope"}).status_code == 400
    assert "language" in client.post(f"{MODELS}/custom", json={**body, "languages": ["xx"]}).json["error"]
    assert client.post(f"{MODELS}/custom", json=body).status_code == 201
    assert "already" in client.post(f"{MODELS}/custom", json=body).json["error"]


def test_remove_only_models_you_added(client):
    "The shipped models can't be removed from the list; added ones can, and then they are gone."
    shipped = client.get(MODELS).json[0]["id"]
    assert client.delete(f"{MODELS}/{shipped}/entry").status_code == 404
    client.post(f"{MODELS}/custom", json={"repo": "a/b", "engine": "mlx-chatterbox", "languages": ["fr"]})
    assert client.delete(f"{MODELS}/custom-a-b/entry").status_code == 200
    assert "custom-a-b" not in [m["id"] for m in client.get(MODELS).json]
    assert client.delete(f"{MODELS}/custom-a-b/entry").status_code == 404


def test_a_broken_models_file_does_not_hide_the_shipped_models(client, app):
    "Unreadable user catalog: the shipped models still list."
    with open(os.path.join(app.env_config.datapath, "models.json"), "w", encoding="utf-8") as f:
        f.write("{not json")
    assert len(client.get(MODELS).json) >= 2
    assert [e["id"] for e in client.get("/ocarina/api/tts/engines").json["engines"]] == ["mlx-chatterbox", "mlx-audio8", "mlx-lm"]


def test_download_progress_ignores_the_reconstructing_bar():
    "Hugging Face shows the same bytes twice (downloading and reconstructing); only one may count."
    seen = []
    progress = model_files._progress_class({"done": 0, "total": 100}, lambda d, t: seen.append(d))  # pylint: disable=protected-access
    download = progress(total=100, unit="B", desc="Downloading bytes", disable=False)
    rebuild = progress(total=100, unit="B", desc="Reconstructing (incomplete total...)", disable=False)
    download.update(40)
    rebuild.update(40)
    download.update(30)
    assert seen == [40, 70]
    files = progress(total=3, unit="it", desc="Fetching 3 files", disable=False)
    files.update(1)
    assert seen == [40, 70]


def test_lookup_describes_the_model_for_the_form(client, hub, monkeypatch):
    "The look-up reports the model type, engine support, memory and notes; the helper process and config are faked."
    monkeypatch.setattr(model_files, "_fetch_config", lambda repo, rev: {"model_type": "higgs_multimodal_qwen3"})
    monkeypatch.setattr(model_files, "_inspect", lambda t, r: {"known": True, "module": "higgs_audio_v3", "problem": None})
    hub["info"] = _info(files={"model.safetensors": 9_300_000_000, "config.json": 50})
    r = client.post(f"{MODELS}/lookup", json={"repo": "bosonai/higgs-tts-3-4b"}).json
    assert r["modelType"] == "higgs_multimodal_qwen3" and r["support"]["known"] is True and r["converted"] is False
    assert r["memoryGb"] == 10.7
    notes = " ".join(r["notes"])
    assert "original release" in notes and "10.7 GB" in notes and "tries it once" in notes


def test_lookup_warns_when_the_engine_does_not_know_the_model(client, hub, monkeypatch):
    "An unrecognised type is said plainly, and an MLX conversion is not called an original release."
    monkeypatch.setattr(model_files, "_fetch_config", lambda repo, rev: {"model_type": "mystery"})
    monkeypatch.setattr(model_files, "_inspect", lambda t, r: {"known": False, "module": None, "problem": "ValueError: not supported"})
    r = client.post(f"{MODELS}/lookup", json={"repo": "mlx-community/mystery-4bit"}).json
    assert r["converted"] is True and any("does not recognise" in n for n in r["notes"])
    assert not any("original release" in n for n in r["notes"])


def test_lookup_still_works_when_the_helper_fails(client, hub, monkeypatch):
    "A broken helper or unreadable config only means 'could not check'; the look-up itself succeeds."
    monkeypatch.setattr(model_files, "_fetch_config", lambda repo, rev: {})
    monkeypatch.setattr(model_files.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError("no python")))
    r = client.post(f"{MODELS}/lookup", json={"repo": "someone/some-model"})
    assert r.status_code == 200 and r.json["support"]["known"] is None and r.json["modelType"] is None


def test_inspect_only_says_not_supported_when_mlx_audio_does(monkeypatch):
    "A failure of the check itself is 'cannot tell' (None), never 'not recognised'."
    import sys, types  # pylint: disable=import-outside-toplevel
    from ocarina.tts import inspect_model  # pylint: disable=import-outside-toplevel

    def fake_modules(raises):
        utils = types.ModuleType("mlx_audio.tts.utils")
        utils.get_model_and_args = lambda t, parts: (_ for _ in ()).throw(raises)
        base = types.ModuleType("mlx_audio.utils")
        base.get_model_name_parts = lambda repo: [repo]
        monkeypatch.setitem(sys.modules, "mlx_audio", types.ModuleType("mlx_audio"))
        monkeypatch.setitem(sys.modules, "mlx_audio.utils", base)
        monkeypatch.setitem(sys.modules, "mlx_audio.tts", types.ModuleType("mlx_audio.tts"))
        monkeypatch.setitem(sys.modules, "mlx_audio.tts.utils", utils)

    fake_modules(ValueError("Model type gpt2 not supported for tts."))
    assert inspect_model.inspect("gpt2", "a/b")["known"] is False
    fake_modules(OSError("outgoing traffic has been disabled"))
    assert inspect_model.inspect("llama", "a/b")["known"] is None
    fake_modules(ValueError("something else entirely"))
    assert inspect_model.inspect("x", "a/b")["known"] is None
    fake_modules(ModuleNotFoundError("No module named 'torch'", name="torch"))
    found = inspect_model.inspect("y", "a/b")
    assert found["known"] is True and "torch" in found["problem"]


def test_a_translation_model_can_be_added_and_is_a_text_model(client, monkeypatch):
    "Choosing the translation style makes the entry a text model (so it is offered under Translation, not for voicing books)."
    from ocarina.tts import models as model_files  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(model_files, "lookup_hub_repo", lambda repo: {"repo": repo, "revision": "abc", "license": "apache-2.0", "files": {"model.safetensors": 10}, "totalBytes": 10})
    r = client.post("/ocarina/api/tts/models/custom", json={"repo": "mlx-community/translategemma-27b-it-4bit", "engine": "mlx-lm", "languages": ["nl"]})
    assert r.status_code == 201, r.json
    assert r.json["kind"] == "text" and r.json["prompt"] == "translategemma"
    assert any(m["id"] == r.json["id"] for m in model_files.text_models())
    assert all(m["id"] != r.json["id"] for m in model_files.speech_models())
    client.delete(f"/ocarina/api/tts/models/{r.json['id']}/entry")
