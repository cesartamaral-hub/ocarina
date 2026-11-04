"""
Trying a model once: the check job, stored results, flagging models that fail, and the automatic check after a
model you added has downloaded.
"""

import os

import pytest

from ocarina import model_check
from ocarina.tts import models as model_files
from ocarina.tts.supervisor import Supervisor, TtsError
from tests.ocarina.helpers import make_dutch_book, wait_for_job

MODELS = "/ocarina/api/tts/models"
SPEECH = "chatterbox-multilingual-v3-mlx"


@pytest.fixture(autouse=True)
def fresh(app, monkeypatch):
    "Fake engine, models 'installed', and no stored results or user catalog before and after."
    datapath = app.env_config.datapath
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    monkeypatch.setattr(model_files, "is_installed", lambda m: True)

    def clean():
        for name in (model_check.FILE, "models.json"):
            path = os.path.join(datapath, name)
            if os.path.exists(path):
                os.remove(path)

    clean()
    yield
    clean()


def _check(client, model_id):
    r = client.post(f"{MODELS}/{model_id}/check")
    assert r.status_code == 202, r.json
    return wait_for_job(client, r.json["id"])


def _listed(client, model_id):
    return next(m for m in client.get(MODELS).json if m["id"] == model_id)


def test_a_working_speech_model_passes_and_the_numbers_are_kept(client):
    "The check loads the model, asks for two short sentences, and stores load time and speed."
    assert _listed(client, SPEECH)["check"] is None
    job = _check(client, SPEECH)
    assert job["state"] == "done" and job["title"].startswith("Chatterbox")
    result = _listed(client, SPEECH)["check"]
    assert result["ok"] is True and result["secondsPerSecondOfAudio"] is not None and result["revision"] and result["at"]


def test_a_text_model_is_checked_with_a_translation(client):
    "The translation model is tried with one sentence."
    assert _check(client, "qwen3-4b-instruct-mlx")["state"] == "done"
    assert _listed(client, "qwen3-4b-instruct-mlx")["check"]["ok"] is True


def test_a_failing_model_gets_a_plain_reason_and_the_original_detail(client, monkeypatch):
    "The reason is a sentence; the Python error is kept as detail."
    def boom(self, *a, **k):  # pylint: disable=unused-argument
        raise TtsError("ModuleNotFoundError: No module named 'torch'")

    monkeypatch.setattr(Supervisor, "synth", boom)
    _check(client, SPEECH)
    result = _listed(client, SPEECH)["check"]
    assert result["ok"] is False and "needs the Python package “torch”" in result["error"]
    assert "No module named 'torch'" in result["detail"]


def test_a_failing_model_is_not_chosen_and_is_flagged_in_the_options(app, client, monkeypatch):
    "Voicing skips it, asking for it by name says why, and the options list marks it."
    with app.app_context():
        book_id = make_dutch_book("Mislukt").id
    monkeypatch.setattr(Supervisor, "synth", lambda self, *a, **k: (_ for _ in ()).throw(TtsError("ModuleNotFoundError: No module named 'torch'")))
    _check(client, SPEECH)
    options = client.get(f"/ocarina/api/books/{book_id}/audio/options").json
    by_id = {m["id"]: m for m in options["models"]}
    assert by_id[SPEECH]["problem"] and not by_id["audio8-realistic-mlx"]["problem"]
    assert options["defaultModel"] == "audio8-realistic-mlx"  # the working one is the default now
    blocked = client.post(f"/ocarina/api/books/{book_id}/audio", json={"model": SPEECH})
    assert blocked.status_code == 409 and blocked.json["code"] == "model_failed" and "torch" in blocked.json["error"]


def test_passing_the_check_again_clears_the_flag(client, monkeypatch):
    "A later success replaces the failure."
    monkeypatch.setattr(Supervisor, "synth", lambda self, *a, **k: (_ for _ in ()).throw(TtsError("TTS worker died or timed out")))
    _check(client, SPEECH)
    assert _listed(client, SPEECH)["check"]["ok"] is False
    monkeypatch.undo()
    monkeypatch.setattr(model_files, "is_installed", lambda m: True)
    _check(client, SPEECH)
    assert _listed(client, SPEECH)["check"]["ok"] is True


def test_deleting_a_model_forgets_its_check(client, monkeypatch):
    "The stored result goes with the model's files."
    _check(client, SPEECH)
    monkeypatch.setattr(model_files, "delete", lambda m: None)
    assert client.delete(f"{MODELS}/{SPEECH}").status_code == 200
    assert model_check.failing_ids(client.application.env_config.datapath) == set()
    assert model_check._load(client.application.env_config.datapath).get(SPEECH) is None  # pylint: disable=protected-access


def test_a_model_you_added_is_checked_automatically_after_its_download(app, client, monkeypatch):
    "The download job ends with a test, so you know right away; shipped models are not retested."
    import json  # pylint: disable=import-outside-toplevel

    entry = {
        "id": "custom-x-y", "name": "X Y", "engine": "mlx-audio8", "languages": ["pl"], "license": "mit",
        "repositories": [{"id": "x/y", "revision": "abc", "files": {"model.safetensors": 10}}],
    }
    with open(os.path.join(app.env_config.datapath, "models.json"), "w", encoding="utf-8") as f:
        json.dump({"schema": 1, "models": [entry]}, f)
    state = {"installed": False}
    monkeypatch.setattr(model_files, "is_installed", lambda m: state["installed"])
    monkeypatch.setattr(model_files, "download", lambda m, cb: (state.update(installed=True), cb(10, 10)))
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    job = wait_for_job(client, client.post(f"{MODELS}/custom-x-y/download").json["id"])
    assert job["state"] == "done" and job["phase"] == "testing"
    assert _listed(client, "custom-x-y")["check"]["ok"] is True
    assert _listed(client, SPEECH)["check"] is None


def test_checking_needs_an_installed_model(client, monkeypatch):
    "Without the files (and without the test engine) the answer says to download first."
    client.application.config.pop("OCARINA_TTS_ENGINE")
    monkeypatch.setattr(model_files, "is_installed", lambda m: False)
    assert client.post(f"{MODELS}/{SPEECH}/check").status_code == 409
    assert client.post(f"{MODELS}/nope/check").status_code == 404
