"""
Book audio generation and its JSON API, using the fake TTS engine.
"""

import os

from lute.db import db
from lute.models.repositories import BookRepository
from ocarina.tts.book_audio import book_sentences
from tests.ocarina.helpers import make_dutch_book, wait_for_job


def test_book_sentences_follow_pages_and_skip_paragraph_marks(app_context):
    "Sentences come from Lute's parser, page by page."
    b = make_dutch_book()
    got = [(s["page"], s["text"]) for s in book_sentences(b)]
    assert got == [
        (1, "Hallo!"),
        (1, "Mijn naam is Carla."),
        (1, "Ik woon in Nederland."),
        (2, "Elke ochtend sta ik op."),
    ]


def test_generate_audio_job_attaches_mp3_and_timings(app, client):
    "POST starts a job; when done the book has an mp3 and sentence times."
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    with app.app_context():
        book_id = make_dutch_book().id
    r = client.post(f"/ocarina/api/books/{book_id}/audio", json={})
    assert r.status_code == 202
    job = wait_for_job(client, r.json["id"])
    assert job["state"] == "done", job
    assert job["done"] == job["total"] == 4

    with app.app_context():
        name = BookRepository(db.session).find(book_id).audio_filename
        assert name.endswith(".mp3")
        assert os.path.exists(os.path.join(app.env_config.useraudiopath, name))

    t = client.get(f"/ocarina/api/books/{book_id}/audio/sentences").json
    starts = [s["start"] for s in t["sentences"]]
    assert starts[0] == 0 and starts == sorted(starts) and len(starts) == 4
    assert t["language"] == "nl"


def test_generating_for_a_book_with_own_audio_adds_a_version(app, client):
    "A user's own recording is kept: generated audio is added next to it, and both can be chosen."
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    with app.app_context():
        b = make_dutch_book("Own audio")
        b.audio_filename = "my_recording.mp3"
        db.session.add(b)
        db.session.commit()
        book_id = b.id
    r = client.post(f"/ocarina/api/books/{book_id}/audio", json={})
    assert r.status_code == 202
    assert wait_for_job(client, r.json["id"])["state"] == "done"
    versions = client.get(f"/ocarina/api/books/{book_id}/audio/versions").json
    assert [v["kind"] for v in versions] == ["own", "generated"]
    assert [v["selected"] for v in versions] == [False, True]


def test_books_and_sentences_api(app, client):
    "The book list and per-book sentences are served as JSON."
    with app.app_context():
        book_id = make_dutch_book("Api book").id
    books = client.get("/ocarina/api/books").json
    mine = next(b for b in books if b["id"] == book_id)
    assert mine["language"] == "Dutch" and mine["pages"] == 2 and not mine["hasAudio"]
    got = client.get(f"/ocarina/api/books/{book_id}/sentences").json
    assert got["hasTimings"] is False
    assert [s["text"] for s in got["sentences"]][0] == "Hallo!"
    assert client.get("/ocarina/api/books/99999/sentences").status_code == 404


def test_frontend_is_served_with_client_routes(client):
    "Any path under /ocarina/app/ gets the single-page app (when it has been built)."
    if not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ocarina", "web", "dist")):
        return
    assert client.get("/ocarina/app/").status_code == 200
    assert b"<div id=\"root\">" in client.get("/ocarina/app/book/1").data


def test_models_list_shows_install_status_and_size(client, monkeypatch):
    "The model list reports whether each model is installed."
    from ocarina.tts import models as model_files  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(model_files, "is_installed", lambda m: False)
    models = client.get("/ocarina/api/tts/models").json
    assert models[0]["installed"] is False
    assert models[0]["sizeBytes"] > 1_000_000_000
    assert models[0]["downloadJob"] is None


def test_audio_needs_installed_model(app, client, monkeypatch):
    "With the real engine, generating audio before the download is refused."
    from ocarina.tts import models as model_files  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(model_files, "is_installed", lambda m: False)
    with app.app_context():
        book_id = make_dutch_book("No model").id
    r = client.post(f"/ocarina/api/books/{book_id}/audio", json={})
    assert r.status_code == 409 and r.json["code"] == "model_not_installed"


def test_download_job_reports_progress_and_then_installs(client, monkeypatch):
    "A download runs as a job; the model counts as installed once it finishes."
    from ocarina.tts import models as model_files  # pylint: disable=import-outside-toplevel

    state = {"installed": False}
    monkeypatch.setattr(model_files, "is_installed", lambda m: state["installed"])

    def fake_download(model, on_progress):
        on_progress(50, 100)
        state["installed"] = True
        on_progress(100, 100)

    monkeypatch.setattr(model_files, "download", fake_download)
    model_id = client.get("/ocarina/api/tts/models").json[0]["id"]
    r = client.post(f"/ocarina/api/tts/models/{model_id}/download")
    assert r.status_code == 202
    job = wait_for_job(client, r.json["id"])
    assert job["state"] == "done" and job["done"] == 100
    assert client.get("/ocarina/api/tts/models").json[0]["installed"] is True
    again = client.post(f"/ocarina/api/tts/models/{model_id}/download")
    assert again.status_code == 409


def test_delete_model_calls_delete(client, monkeypatch):
    "DELETE removes the model files."
    from ocarina.tts import models as model_files  # pylint: disable=import-outside-toplevel

    deleted = []
    monkeypatch.setattr(model_files, "delete", lambda m: deleted.append(m["id"]))
    model_id = client.get("/ocarina/api/tts/models").json[0]["id"]
    assert client.delete(f"/ocarina/api/tts/models/{model_id}").status_code == 200
    assert deleted == [model_id]
    assert client.delete("/ocarina/api/tts/models/nope").status_code == 404
