"""
Hearing a word: the sources, the fallback to the voice of the Mac, and the cache (the network and `say` are faked).
"""

import os

import pytest
import requests

from ocarina import pronounce
from tests.conftest import _get_test_language

SAY = "/ocarina/api/pronounce"


def dutch_id(app):
    with app.app_context():
        return _get_test_language("Dutch").id


@pytest.fixture(autouse=True)
def fake_mac(monkeypatch):
    "The voice of the Mac: a file with the text in it (so the tests need no speech, no ffmpeg)."

    def system(cfg, text, code):
        out = pronounce.cache_path(cfg.datapath, f"system\nTest\n{text}")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(b"RIFF" + text.encode())
        return out

    monkeypatch.setattr(pronounce, "_from_system", system)


def test_the_voice_of_the_model_says_a_word_and_it_is_cached(app, client):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    r = client.post(SAY, json={"text": "fiets", "languageId": dutch_id(app)})
    assert r.status_code == 200 and r.json["source"] == "voice" and r.json["note"] is None
    audio = client.get(r.json["url"])
    assert audio.status_code == 200 and audio.mimetype == "audio/wav" and len(audio.data) > 44
    again = client.post(SAY, json={"text": "fiets", "languageId": dutch_id(app)})
    assert again.json["url"] == r.json["url"]  # the same file, not made again


def test_several_words_are_one_text(app, client):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    r = client.post(SAY, json={"text": "  mijn   naam is\nCarla ", "languageId": dutch_id(app)})
    assert r.status_code == 200 and r.json["source"] == "voice"


def test_without_a_model_the_mac_speaks_and_says_why(app, client, monkeypatch):
    monkeypatch.setattr("ocarina.tts.models.is_installed", lambda model: False)
    r = client.post(SAY, json={"text": "fiets", "languageId": dutch_id(app)})
    assert r.status_code == 200 and r.json["source"] == "system" and "not downloaded" in r.json["note"]


def test_a_busy_model_gives_way_to_the_mac(app, client, monkeypatch):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    monkeypatch.setattr("ocarina.api.jobs.active", lambda **kw: [{"id": "x"}] if kw.get("kind") == "audio" else [])
    r = client.post(SAY, json={"text": "fiets", "languageId": dutch_id(app)})
    assert r.json["source"] == "system" and "busy" in r.json["note"]


def test_a_recording_of_a_person_is_for_single_words(app, client, monkeypatch):
    r = client.post(SAY, json={"text": "twee woorden", "languageId": dutch_id(app), "source": "speaker"})
    assert r.json["source"] == "system" and "single words" in r.json["note"]


def test_a_recording_is_found_through_wiktionary(app, client, monkeypatch):
    monkeypatch.setattr(pronounce, "speaker_file", lambda word, code: "Nl-fiets.ogg" if word == "fiets" else None)

    class Reply:
        content = b"ogg"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "get", lambda *a, **k: Reply())
    monkeypatch.setattr(pronounce, "_convert", lambda src, dst: (os.makedirs(os.path.dirname(dst), exist_ok=True), open(dst, "wb").write(b"RIFFwav")))
    r = client.post(SAY, json={"text": "fiets", "languageId": dutch_id(app), "source": "speaker"})
    assert r.json["source"] == "speaker" and r.json["note"] is None
    missing = client.post(SAY, json={"text": "onbekend", "languageId": dutch_id(app), "source": "speaker"})
    assert missing.json["source"] == "system" and "no recording" in missing.json["note"]


def test_google_voice_and_its_failure(app, client, monkeypatch):
    class Reply:
        content = b"ID3mp3"
        headers = {"Content-Type": "audio/mpeg"}

        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "get", lambda *a, **k: Reply())
    r = client.post(SAY, json={"text": "fiets", "languageId": dutch_id(app), "source": "google"})
    assert r.json["source"] == "google" and r.json["url"].endswith(".mp3")
    assert client.get(r.json["url"]).mimetype == "audio/mpeg"

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError()

    monkeypatch.setattr(requests, "get", boom)
    failed = client.post(SAY, json={"text": "andere", "languageId": dutch_id(app), "source": "google"})
    assert failed.json["source"] == "system" and "could not be reached" in failed.json["note"]


def test_google_takes_short_texts_only(app, client):
    r = client.post(SAY, json={"text": "woord " * 60, "languageId": dutch_id(app), "source": "google"})
    assert r.json["source"] == "system" and "190" in r.json["note"]


def test_bad_requests(app, client):
    assert client.post(SAY, json={"text": "", "languageId": dutch_id(app)}).status_code == 400
    assert client.post(SAY, json={"text": "x", "languageId": 99999}).status_code == 400
    assert client.get("/ocarina/api/pronounce/audio/../../etc/passwd").status_code == 404
    assert client.get("/ocarina/api/pronounce/audio/" + "0" * 64 + ".wav").status_code == 404
