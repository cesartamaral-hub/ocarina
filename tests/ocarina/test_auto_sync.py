"""
Every recording added to a material is synced with its text, and a new material can be translated when it is saved (the models are faked).
"""

import io

import pytest

from ocarina import translate
from tests.conftest import _get_test_language
from tests.ocarina.helpers import make_dutch_book, wait_for_job

BOOKS = "/ocarina/api/books"
pytestmark = pytest.mark.autosync


def _upload(client, book_id):
    return client.post(f"{BOOKS}/{book_id}/audio/upload", data={"audio": (io.BytesIO(b"ID3x"), "eigen.mp3")}, content_type="multipart/form-data")


def test_a_recording_added_later_is_synced_at_once(app, client):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    with app.app_context():
        book_id = make_dutch_book("Later audio").id
    r = _upload(client, book_id)
    assert r.status_code == 201 and r.json["sync"]["state"] == "started"
    assert wait_for_job(client, r.json["sync"]["job"]["id"])["state"] == "done"
    assert client.get(f"{BOOKS}/{book_id}/sentences").json["hasTimings"]


def test_without_the_sync_model_the_pauses_are_used(app, client, monkeypatch):
    "No aligner downloaded: the recording is synced by its pauses instead (the job here fails on the fake audio, which is fine)."
    monkeypatch.setattr("ocarina.tts.models.is_installed", lambda model: False)
    with app.app_context():
        book_id = make_dutch_book("Zonder model").id
    r = _upload(client, book_id)
    assert r.status_code == 201
    assert r.json["sync"]["state"] == "started" and r.json["sync"]["job"]["method"] == "pauses"


def _save(client, **fields):
    with client.application.app_context():
        lang_id = _get_test_language("Dutch").id
    data = {"title": fields.pop("title", "Nieuw"), "text": "Dit is een zin. Dit is er nog een.", "languageId": str(lang_id), **fields}
    return client.post(BOOKS, data=data, content_type="multipart/form-data")


def test_a_recording_saved_with_the_material_is_synced_when_it_is_saved(app, client):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    r = _save(client, audio=(io.BytesIO(b"ID3x"), "eigen.mp3"))
    assert r.status_code == 201 and r.json["sync"]["state"] == "started"
    assert wait_for_job(client, r.json["sync"]["job"]["id"])["state"] == "done"
    assert client.get(f"{BOOKS}/{r.json['id']}/sentences").json["hasTimings"]
    assert "sync" not in _save(client, title="Zonder audio").json


def test_a_material_is_translated_when_it_is_saved_if_asked(app, client):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    client.put("/ocarina/api/translate/settings", json={"provider": "local", "target": "en"})
    try:
        r = _save(client, title="Vertaald", translate="1", translateProvider="local", translateModel="qwen3-4b-instruct-mlx")
        assert r.status_code == 201 and r.json["translation"]["state"] == "started"
        assert wait_for_job(client, r.json["translation"]["job"]["id"])["state"] == "done"
        done = client.get(f"{BOOKS}/{r.json['id']}/translation").json
        assert done["done"] == done["total"] > 0
        assert "translation" not in _save(client, title="Niet vertaald").json
    finally:
        translate.local_model.unload()


def test_a_translation_that_cannot_be_made_does_not_stop_the_material_being_saved(app, client):
    r = _save(client, title="Geen sleutel", translate="1", translateProvider="deepl")
    assert r.status_code == 201 and r.json["translation"]["state"] == "failed" and r.json["translation"]["error"]
    assert client.get(f"{BOOKS}/{r.json['id']}/sentences").status_code == 200
