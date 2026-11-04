"""
Adding a book from a YouTube link: captions at once, Whisper (faked) as a job, the video's sound kept as the book's audio.
"""

import os

from ocarina import youtube
from tests.conftest import _get_test_language
from tests.ocarina.helpers import wait_for_job

EXTRACT = "/ocarina/api/books/extract"
URL = "https://youtu.be/dQw4w9WgXcQ"


def _fake_youtube(monkeypatch, captions):
    monkeypatch.setattr(youtube, "video_title", lambda url, vid: "Een video")
    monkeypatch.setattr(youtube, "_captions", lambda vid, lang: captions)

    def download(url, folder, check=None, as_m4a=False):
        path = os.path.join(folder, "audio.m4a")
        with open(path, "wb") as f:
            f.write(b"sound")
        return path

    monkeypatch.setattr(youtube, "_download_audio", download)


def test_captions_answer_at_once(client, monkeypatch):
    _fake_youtube(monkeypatch, ("Ondertitels.", "note", [[0, 1.0]]))
    r = client.post(EXTRACT, json={"url": URL})
    assert r.status_code == 200
    assert r.json == {"title": "Een video", "text": "Ondertitels.", "sourceUri": URL, "note": "note", "audioToken": None, "videoId": "dQw4w9WgXcQ", "anchors": [[0, 1.0]]}


def test_no_captions_and_no_model_says_which_model(client, monkeypatch):
    _fake_youtube(monkeypatch, (None, "The video has no captions.", None))
    monkeypatch.setattr("ocarina.tts.models.is_installed", lambda model: False)  # whatever this Mac has downloaded
    r = client.post(EXTRACT, json={"url": URL})
    assert r.status_code == 409 and r.json["code"] == "model_not_installed"


def test_no_captions_is_transcribed_as_a_job(app, client, monkeypatch):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    _fake_youtube(monkeypatch, (None, "no captions", None))
    r = client.post(EXTRACT, json={"url": URL, "languageId": None})
    assert r.status_code == 202
    job = wait_for_job(client, r.json["id"])
    assert job["state"] == "done", job
    assert job["result"]["text"].startswith("Gehoord") and "Whisper" in job["result"]["note"]
    assert job["result"]["audioToken"] is None


def test_kept_sound_becomes_the_books_audio(app, client, monkeypatch):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    _fake_youtube(monkeypatch, ("Ondertitels.", None, [[0, 1.0]]))
    r = client.post(EXTRACT, json={"url": URL, "keepAudio": True})
    job = wait_for_job(client, r.json["id"])
    token = job["result"]["audioToken"]
    assert job["state"] == "done" and token and job["result"]["text"] == "Ondertitels."
    with app.app_context():
        lang_id = _get_test_language("Dutch").id
    saved = client.post(
        "/ocarina/api/books",
        data={"title": "Uit video", "text": "Ondertitels.", "languageId": str(lang_id), "importAudio": token},
        content_type="multipart/form-data",
    )
    assert saved.status_code == 201
    book = next(b for b in client.get("/ocarina/api/books").json if b["id"] == saved.json["id"])
    assert book["hasAudio"]
    gone = client.post(
        "/ocarina/api/books",
        data={"title": "Nog eens", "text": "Tekst.", "languageId": str(lang_id), "importAudio": token},
        content_type="multipart/form-data",
    )
    assert gone.status_code == 400  # the sound was used up


def test_a_bad_sound_token_is_refused(client):
    r = client.post(
        "/ocarina/api/books",
        data={"title": "X", "text": "Tekst.", "languageId": "1", "importAudio": "../../etc/passwd"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 400


def test_automatic_captions_are_transcribed_when_whisper_is_there(app, client, monkeypatch):
    _fake_youtube(monkeypatch, ("zonder leestekens", youtube.AUTOMATIC, [[0, 1.0]]))
    monkeypatch.setattr("ocarina.tts.models.is_installed", lambda model: False)
    plain = client.post(EXTRACT, json={"url": URL})
    assert plain.status_code == 200 and plain.json["text"] == "zonder leestekens"  # no model: the captions as they are
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    r = client.post(EXTRACT, json={"url": URL})
    assert r.status_code == 202
    assert wait_for_job(client, r.json["id"])["result"]["text"].startswith("Gehoord")
