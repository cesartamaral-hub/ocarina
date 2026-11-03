"""
Reference voices: adding, listing, deleting, previews, and which voice voices a book.
"""

import io
import os
import shutil

import numpy as np
import pytest
import soundfile as sf

from ocarina import prefs
from ocarina.tts import voices
from tests.ocarina.helpers import make_dutch_book, wait_for_job

VOICES = "/ocarina/api/tts/voices"


@pytest.fixture(autouse=True)
def clean_voices(app):
    "The test data folder is shared between tests: start and end without user voices."
    folder = os.path.join(app.env_config.datapath, "voices")
    shutil.rmtree(folder, ignore_errors=True)
    yield
    shutil.rmtree(folder, ignore_errors=True)


def _clip(seconds=5, rate=24000, channels=1, fmt="WAV"):
    t = np.arange(int(seconds * rate)) / rate
    wave = (0.3 * np.sin(2 * np.pi * 220 * t)).astype("float32")
    data = np.stack([wave] * channels, axis=1) if channels > 1 else wave
    out = io.BytesIO()
    sf.write(out, data, rate, format=fmt)
    return out.getvalue()


def _upload(client, filename, data, **form):
    return client.post(VOICES, data={"clip": (io.BytesIO(data), filename), **form}, content_type="multipart/form-data")


def test_builtin_voice_is_listed_first(client):
    "The shipped voice is always there and can't be removed."
    listed = client.get(VOICES).json
    assert listed[0]["id"] == "default" and listed[0]["builtin"] is True and listed[0]["seconds"] > 3
    assert client.delete(f"{VOICES}/default").status_code == 404


def test_add_list_and_delete_a_voice(client, app):
    "An uploaded clip becomes a mono wav under its name; stereo and mp3 are accepted."
    r = _upload(client, "Mijn stem.wav", _clip(channels=2))
    assert r.status_code == 201 and r.json["id"] == "Mijn-stem"
    saved = os.path.join(app.env_config.datapath, "voices", "Mijn-stem.wav")
    assert sf.info(saved).channels == 1
    assert [v["id"] for v in client.get(VOICES).json] == ["default", "Mijn-stem"]
    assert _upload(client, "x.mp3", _clip(fmt="MP3"), name="Als mp3").json["id"] == "Als-mp3"
    assert client.delete(f"{VOICES}/Mijn-stem").status_code == 200
    assert not os.path.exists(saved)
    assert client.delete(f"{VOICES}/Mijn-stem").status_code == 404


def test_bad_clips_are_refused_with_a_reason(client):
    "Too short, too long, wrong type, unreadable, duplicate and nameless clips."
    assert "seconds" in _upload(client, "kort.wav", _clip(1)).json["error"]
    assert "seconds" in _upload(client, "lang.wav", _clip(61, rate=8000)).json["error"]
    assert "wav, mp3" in _upload(client, "x.m4a", b"x").json["error"]
    assert "Can't read" in _upload(client, "kapot.wav", b"not audio at all").json["error"]
    assert "name" in _upload(client, "default.wav", _clip()).json["error"]
    assert _upload(client, "twee.wav", _clip()).status_code == 201
    assert "already exists" in _upload(client, "twee.wav", _clip()).json["error"]
    assert client.post(VOICES, data={}, content_type="multipart/form-data").status_code == 400


def test_voice_ids_cannot_escape_the_voices_folder(app):
    "path_of only finds clips inside the voices folder."
    datapath = app.env_config.datapath
    assert voices.path_of(datapath, "../config") is None
    assert voices.path_of(datapath, "nope") is None
    assert voices.path_of(datapath, None) == voices.path_of(datapath, "default")


def test_preview_job_makes_a_playable_wav(app, client):
    "A preview is a queued job; when done the wav can be fetched."
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    r = client.post(f"{VOICES}/preview", json={"language": "nl", "voice": "default"})
    assert r.status_code == 202
    job = wait_for_job(client, r.json["id"])
    assert job["state"] == "done" and job["preview"].endswith(".wav")
    got = client.get(f"/ocarina/api/tts/previews/{job['preview']}")
    assert got.status_code == 200 and got.mimetype == "audio/wav" and got.data[:4] == b"RIFF"
    assert client.get("/ocarina/api/tts/previews/..%2Fconfig.yml").status_code == 404


def test_preview_input_checks(client):
    "A language and an existing voice are needed; the text is limited."
    assert client.post(f"{VOICES}/preview", json={"language": "xx"}).status_code == 400
    assert client.post(f"{VOICES}/preview", json={"language": "nl", "voice": "nope"}).status_code == 400
    assert client.post(f"{VOICES}/preview", json={"language": "nl", "text": "x" * 301}).status_code == 400


def test_the_voice_for_a_language_is_used_for_its_books(app, client, monkeypatch, tmp_path):
    "voice.nl decides the voice of a Dutch book; a deleted voice falls back; the request can override."
    import ocarina.api.audio as audio  # pylint: disable=import-outside-toplevel

    app.config["OCARINA_TTS_ENGINE"] = "fake"
    monkeypatch.setattr(prefs, "path_for", lambda datapath: str(tmp_path / "prefs.json"))
    used = []

    def fake_run(app, job, check, book_id, model, voice, pause, ref_text=None):  # pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments
        used.append(os.path.basename(voice))

    monkeypatch.setattr(audio, "_run_job", fake_run)
    _upload(client, "mijn.wav", _clip())
    with app.app_context():
        book_id = make_dutch_book("Stemkeuze").id
    url = f"/ocarina/api/books/{book_id}/audio"

    def start(**body):
        r = client.post(url, json=body)
        wait_for_job(client, r.json["id"]) if r.status_code == 202 else None
        return r

    start()
    prefs.update(str(tmp_path / "prefs.json"), {"voice.nl": "mijn"})
    start()
    client.delete(f"{VOICES}/mijn")
    start()  # the chosen voice is gone: the default voice is used
    assert start(voice="nope").status_code == 400
    assert used == ["default.wav", "mijn.wav", "default.wav"]


def test_transcript_is_stored_with_the_voice_and_used_when_voicing(app, client, monkeypatch):
    "The words spoken in a clip are kept next to it, listed, passed on to the engine, and removed with the voice."
    import ocarina.api.audio as audio  # pylint: disable=import-outside-toplevel

    app.config["OCARINA_TTS_ENGINE"] = "fake"
    r = _upload(client, "stem.wav", _clip(), transcript="  Goedemorgen allemaal.  ")
    assert r.json["transcript"] == "Goedemorgen allemaal."
    assert [v["transcript"] for v in client.get(VOICES).json] == ["", "Goedemorgen allemaal."]
    seen = []

    def fake_run(app, job, check, book_id, model, voice, pause, ref_text=None):  # pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments
        seen.append(ref_text)

    monkeypatch.setattr(audio, "_run_job", fake_run)
    with app.app_context():
        book_id = make_dutch_book("Transcript").id
    url = f"/ocarina/api/books/{book_id}/audio"
    for body in ({"voice": "stem"}, {}):
        wait_for_job(client, client.post(url, json=body).json["id"])
    assert seen == ["Goedemorgen allemaal.", None]
    client.delete(f"{VOICES}/stem")
    assert not os.path.exists(os.path.join(app.env_config.datapath, "voices", "stem.txt"))


def test_voice_digest_changes_with_the_transcript(tmp_path):
    "The cache tells apart the same clip with and without the words spoken in it."
    from ocarina.tts.service import voice_digest  # pylint: disable=import-outside-toplevel

    clip = tmp_path / "v.wav"
    clip.write_bytes(_clip())
    assert voice_digest(str(clip)) != voice_digest(str(clip), "hallo")
    assert voice_digest(str(clip), "hallo") == voice_digest(str(clip), "hallo")
