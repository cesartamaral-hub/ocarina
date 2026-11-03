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
