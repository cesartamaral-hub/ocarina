"""
Book audio generation and its JSON API, using the fake TTS engine.
"""

import os
import time

from lute.db import db
from lute.models.book import Book, Text
from lute.models.repositories import BookRepository
from ocarina.tts.book_audio import book_sentences
from tests.conftest import _get_test_language


def _dutch_book(title="Carla"):
    lang = _get_test_language("Dutch")
    b = Book(title, lang)
    b.texts = []
    Text(b, "Hallo! Mijn naam is Carla.\n\nIk woon in Nederland.", 1)
    Text(b, "Elke ochtend sta ik op.", 2)
    db.session.add(b)
    db.session.commit()
    return b


def _wait(client, job_id, seconds=20):
    end = time.time() + seconds
    while time.time() < end:
        job = client.get(f"/ocarina/api/jobs/{job_id}").json
        if job["state"] != "running":
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish")


def test_book_sentences_follow_pages_and_skip_paragraph_marks(app_context):
    "Sentences come from Lute's parser, page by page."
    b = _dutch_book()
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
        book_id = _dutch_book().id
    r = client.post(f"/ocarina/api/books/{book_id}/audio", json={})
    assert r.status_code == 202
    job = _wait(client, r.json["id"])
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


def test_book_with_own_audio_needs_replace(app, client):
    "A user's own recording is not overwritten unless replace=true."
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    with app.app_context():
        b = _dutch_book("Own audio")
        b.audio_filename = "my_recording.mp3"
        db.session.add(b)
        db.session.commit()
        book_id = b.id
    r = client.post(f"/ocarina/api/books/{book_id}/audio", json={})
    assert r.status_code == 409 and r.json["code"] == "has_user_audio"
    r = client.post(f"/ocarina/api/books/{book_id}/audio", json={"replace": True})
    assert r.status_code == 202
    assert _wait(client, r.json["id"])["state"] == "done"


def test_books_and_sentences_api(app, client):
    "The book list and per-book sentences are served as JSON."
    with app.app_context():
        book_id = _dutch_book("Api book").id
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
