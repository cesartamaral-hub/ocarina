"""
Syncing your own recording with the text (the aligner is faked: every word takes 0.3 s of a 60 s recording).
"""

import io
import os

from tests.ocarina.helpers import make_dutch_book, wait_for_job

BOOKS = "/ocarina/api/books"


def _upload(client, book_id, name="eigen.mp3"):
    r = client.post(f"{BOOKS}/{book_id}/audio/upload", data={"audio": (io.BytesIO(b"ID3x"), name)}, content_type="multipart/form-data")
    return r.json["audio_filename"], r.json["versionId"]


def _sync(client, book_id, version_id):
    r = client.post(f"{BOOKS}/{book_id}/audio/versions/{version_id}/sync")
    return r, (wait_for_job(client, r.json["id"]) if r.status_code == 202 else None)


def test_syncing_your_recording_makes_sentences_follow_it(app, client):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    with app.app_context():
        book_id = make_dutch_book("Sync API").id
    filename, version_id = _upload(client, book_id)
    before = client.get(f"{BOOKS}/{book_id}/sentences").json
    assert before["hasAudio"] and not before["hasTimings"]

    response, job = _sync(client, book_id, version_id)
    assert response.status_code == 202 and job["state"] == "done", job
    assert job["done"] == job["total"] and job["suspect"] == 0

    after = client.get(f"{BOOKS}/{book_id}/sentences").json
    assert after["hasTimings"] and all(s["start"] is not None for s in after["sentences"])
    assert after["sentences"][0]["start"] == 0.0
    starts = [s["start"] for s in after["sentences"]]
    assert starts == sorted(starts)

    version = client.get(f"{BOOKS}/{book_id}/audio/versions").json[0]
    assert version["kind"] == "own" and version["hasTimings"] and version["synced"]
    listed = next(b for b in client.get(BOOKS).json if b["id"] == book_id)
    assert listed["hasAudio"] and listed["ocarinaAudio"] is False  # still your own recording, not Ocarina's


def test_removing_the_version_keeps_the_recording_but_not_the_timings(app, client):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    with app.app_context():
        book_id = make_dutch_book("Sync remove").id
        audio_dir = app.env_config.useraudiopath
    filename, version_id = _upload(client, book_id)
    _sync(client, book_id, version_id)
    assert os.path.exists(os.path.join(audio_dir, filename + ".sentences.json"))
    assert client.delete(f"{BOOKS}/{book_id}/audio/versions/{version_id}").status_code == 200
    assert os.path.exists(os.path.join(audio_dir, filename))
    assert not os.path.exists(os.path.join(audio_dir, filename + ".sentences.json"))


def test_audio_made_by_ocarina_is_not_synced(app, client):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    with app.app_context():
        book_id = make_dutch_book("Sync generated").id
    job = client.post(f"{BOOKS}/{book_id}/audio", json={}).json
    assert wait_for_job(client, job["id"])["state"] == "done"
    generated = next(v for v in client.get(f"{BOOKS}/{book_id}/audio/versions").json if v["kind"] == "generated")
    r = client.post(f"{BOOKS}/{book_id}/audio/versions/{generated['id']}/sync")
    assert r.status_code == 400


def test_unknown_version_and_a_second_sync_while_one_runs(app, client):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    with app.app_context():
        book_id = make_dutch_book("Sync twice").id
    _, version_id = _upload(client, book_id)
    assert client.post(f"{BOOKS}/{book_id}/audio/versions/999/sync").status_code == 404
    assert client.post(f"/ocarina/api/books/99999/audio/versions/1/sync").status_code == 404
    r, _ = _sync(client, book_id, version_id)
    assert r.status_code == 202
    r2, _ = _sync(client, book_id, version_id)  # syncing again is fine once the first has finished
    assert r2.status_code == 202


def test_syncing_needs_the_downloaded_model(app, client, monkeypatch):
    "With the real engine, syncing before the download is refused, and the reply says which model to get."
    from ocarina.tts import models as model_files  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(model_files, "is_installed", lambda m: False)
    with app.app_context():
        book_id = make_dutch_book("Sync no model").id
    _, version_id = _upload(client, book_id)
    r = client.post(f"{BOOKS}/{book_id}/audio/versions/{version_id}/sync", json={"method": "aligner"})
    assert r.status_code == 409 and r.json["code"] == "model_not_installed" and r.json["model"] == "qwen3-forced-aligner-mlx"
