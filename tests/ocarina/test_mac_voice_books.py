"""
Books read by the Mac voice: the default when no downloaded model covers the language, with `say` faked (a short tone per sentence).
"""

import math
import uuid

import numpy as np
import pytest
import soundfile as sf

from ocarina import pronounce
from ocarina.tts import models as model_files
from ocarina.tts import system_voice
from tests.ocarina.helpers import make_dutch_book, wait_for_job

BOOKS = "/ocarina/api/books"


class Done:
    returncode = 0
    stdout = ""
    stderr = ""


@pytest.fixture
def fake_say(monkeypatch):
    spoken = []

    def run(cmd, **kwargs):
        out = cmd[cmd.index("-o") + 1]
        voice = cmd[cmd.index("-v") + 1]
        spoken.append((voice, kwargs.get("input")))
        t = np.arange(int(0.3 * 24000)) / 24000
        sf.write(out, 0.3 * np.sin(2 * math.pi * 220 * t), 24000, format="WAV")
        return Done()

    monkeypatch.setattr(system_voice.tools, "find", lambda name: "/usr/bin/say")
    monkeypatch.setattr(system_voice.subprocess, "run", run)
    monkeypatch.setattr(model_files, "is_installed", lambda m: model_files.is_builtin(m))  # no neural model is downloaded
    name = f"Xander {uuid.uuid4().hex[:8]}"  # a new voice each time: the sentence cache outlives a test
    monkeypatch.setattr(pronounce, "mac_voices", lambda code, locale=None: [{"name": name, "novelty": False}])
    monkeypatch.setattr(pronounce, "mac_voice", lambda code, chosen=None, locale=None: name)
    spoken.append(name)
    return spoken


def test_a_book_is_read_by_the_mac_voice_by_default(app, client, fake_say):
    with app.app_context():
        book_id = make_dutch_book("Mac stem").id
    options = client.get(f"{BOOKS}/{book_id}/audio/options").json
    assert options["defaultModel"] == "mac-voice"
    job = client.post(f"{BOOKS}/{book_id}/audio", json={}).json
    assert wait_for_job(client, job["id"])["state"] == "done"
    name, calls = fake_say[0], fake_say[1:]
    assert {voice for voice, _ in calls} == {name} and len(calls) >= 3
    versions = client.get(f"{BOOKS}/{book_id}/audio/versions").json
    assert versions[0]["kind"] == "generated" and versions[0]["hasTimings"]
    assert versions[0]["label"].startswith(f"Mac voice (built in) · {name}")
    assert client.get(f"{BOOKS}/{book_id}/sentences").json["hasTimings"]


def test_another_mac_voice_does_not_reuse_the_sentences_of_the_first(tmp_path):
    a = system_voice.marker(str(tmp_path), "Xander")
    b = system_voice.marker(str(tmp_path), "Ellen")
    assert a != b and open(a, encoding="utf-8").read() == "Xander"
    assert system_voice.marker(str(tmp_path), "Xander") == a  # the same voice, the same marker


def test_without_a_mac_voice_for_the_language_the_answer_says_what_to_do(app, client, fake_say, monkeypatch):
    monkeypatch.setattr(pronounce, "mac_voice", lambda code, chosen=None, locale=None: None)
    with app.app_context():
        book_id = make_dutch_book("Zonder stem").id
    r = client.post(f"{BOOKS}/{book_id}/audio", json={"model": "mac-voice"})
    assert r.status_code == 409 and r.json["code"] == "no_mac_voice" and "Manage Voices" in r.json["error"]


def test_the_mac_voice_is_never_tested_or_deleted(client):
    assert client.post("/ocarina/api/tts/models/mac-voice/check").status_code == 400
    assert client.delete("/ocarina/api/tts/models/mac-voice").status_code == 400
    assert client.post("/ocarina/api/tts/models/mac-voice/download").status_code == 409  # already installed
