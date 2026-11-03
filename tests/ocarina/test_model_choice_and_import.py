"""
Choosing a model per language, and importing a model from a folder.
"""

import json

from huggingface_hub import constants

from ocarina import prefs
from ocarina.tts import models as model_files
from tests.ocarina.helpers import make_dutch_book, wait_for_job

TINY = {
    "id": "tiny",
    "name": "Tiny",
    "engine": "fake",
    "languages": ["nl"],
    "repositories": [
        {"id": "o/main", "revision": "r1", "files": {"model.bin": 5, "config.json": 2}},
        {"id": "o/other", "revision": "r2", "files": {"model.bin": 3}},
    ],
}


def _use_catalog(monkeypatch, tmp_path, models):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"schema": 1, "models": models}), encoding="utf-8")
    monkeypatch.setattr(model_files, "CATALOG", str(path))
    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(tmp_path / "cache"))


def test_choose_model_order(monkeypatch, tmp_path):
    "Requested id, then the language's choice, then the first installed, then the first."
    a, b = {**TINY, "id": "a"}, {**TINY, "id": "b"}
    _use_catalog(monkeypatch, tmp_path, [a, b])
    installed = {"b"}
    monkeypatch.setattr(model_files, "is_installed", lambda m: m["id"] in installed)
    assert model_files.choose_model("a", "b")["id"] == "a"
    assert model_files.choose_model(None, "a")["id"] == "a"
    assert model_files.choose_model(None, "gone")["id"] == "b"
    installed.clear()
    assert model_files.choose_model()["id"] == "a"
    assert model_files.choose_model("gone") is None


def test_audio_uses_the_model_chosen_for_the_language(app, client, monkeypatch, tmp_path):
    "The pref model.nl decides which model voices a Dutch book."
    a, b = {**TINY, "id": "a"}, {**TINY, "id": "b"}
    _use_catalog(monkeypatch, tmp_path, [a, b])
    monkeypatch.setattr(prefs, "path_for", lambda datapath: str(tmp_path / "prefs.json"))
    prefs.update(str(tmp_path / "prefs.json"), {"model.nl": "b"})
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    used = []
    import ocarina.api.audio as audio  # pylint: disable=import-outside-toplevel


    def fake_run(app, job, book_id, model, *rest):  # pylint: disable=unused-argument
        used.append(model["id"])
        job["state"] = "done"

    monkeypatch.setattr(audio, "_run_job", fake_run)
    with app.app_context():
        book_id = make_dutch_book("Choice").id
    r = client.post(f"/ocarina/api/books/{book_id}/audio", json={})
    assert r.status_code == 202
    wait_for_job(client, r.json["id"])
    assert used == ["b"]


def _make_folder(root, layout):
    for rel, size in layout.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)


def test_import_finds_files_by_name_and_size_in_any_layout(monkeypatch, tmp_path):
    "Two repos with a same-named file are told apart by size; subfolders are searched."
    _use_catalog(monkeypatch, tmp_path, [TINY])
    _make_folder(tmp_path / "dl", {"a/model.bin": 5, "a/config.json": 2, "b/deep/model.bin": 3})
    got = {(r["id"], n) for r, n, _ in model_files.find_import_files(TINY, str(tmp_path / "dl"))}
    assert got == {("o/main", "model.bin"), ("o/main", "config.json"), ("o/other", "model.bin")}


def test_import_reports_missing_and_wrong_size_files(monkeypatch, tmp_path):
    "The error names what is missing, including files of the wrong size."
    _use_catalog(monkeypatch, tmp_path, [TINY])
    _make_folder(tmp_path / "dl", {"model.bin": 5, "config.json": 9})
    try:
        model_files.find_import_files(TINY, str(tmp_path / "dl"))
        raise AssertionError("expected FolderError")
    except model_files.FolderError as e:
        assert "config.json" in str(e) and "o/other" in str(e)


def test_import_job_installs_the_model(client, monkeypatch, tmp_path):
    "POST import copies the files into the cache and the model counts as installed."
    _use_catalog(monkeypatch, tmp_path, [TINY])
    _make_folder(tmp_path / "dl", {"model.bin": 5, "config.json": 2, "x/model.bin": 3})
    assert client.get("/ocarina/api/tts/models").json[0]["installed"] is False
    r = client.post("/ocarina/api/tts/models/tiny/import", json={"folder": str(tmp_path / "dl")})
    assert r.status_code == 202
    job = wait_for_job(client, r.json["id"])
    assert job["state"] == "done" and job["done"] == job["total"] == 10
    assert client.get("/ocarina/api/tts/models").json[0]["installed"] is True


def test_import_refuses_bad_folder_up_front(client, monkeypatch, tmp_path):
    "A folder with missing files is a 400 with a message, and no job starts."
    _use_catalog(monkeypatch, tmp_path, [TINY])
    (tmp_path / "empty").mkdir()
    r = client.post("/ocarina/api/tts/models/tiny/import", json={"folder": str(tmp_path / "empty")})
    assert r.status_code == 400 and r.json["code"] == "bad_folder"
    assert client.post("/ocarina/api/tts/models/nope/import", json={}).status_code == 404
