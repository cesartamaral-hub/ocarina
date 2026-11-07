"""
Hearing a word: the sources, the fallback to the voice of the Mac, and the cache (the network and `say` are faked).
"""

import os

import pytest
import requests

from lute.db import db
from ocarina import pronounce
from tests.conftest import _get_test_language

SAY = "/ocarina/api/pronounce"


def dutch_id(app):
    with app.app_context():
        return _get_test_language("Dutch").id


@pytest.fixture(autouse=True)
def fake_mac(monkeypatch):
    "The voice of the Mac: a file with the text in it (so the tests need no speech, no ffmpeg)."

    def system(cfg, text, code, locale=None):
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


LISTING = """\
Alice (Italian (Italy)) it_IT    # Ciao! Mi chiamo Alice.
Alice (Italian (Italy)) it_IT    # Ciao! Mi chiamo Alice.
Eddy (Italian (Italy)) it_IT    # Ciao! Mi chiamo Eddy.
Federica (Premium) it_IT    # Ciao! Mi chiamo Federica.
Luca (Enhanced) it_IT    # Ciao! Mi chiamo Luca.
Amélie              fr_CA    # Bonjour! Je m'appelle Amélie.
Zosia               pl_PL    # Dzień dobry!
"""


@pytest.fixture
def mac_listing(monkeypatch):
    class Done:
        stdout = LISTING

    monkeypatch.setattr(pronounce.tools, "find", lambda name: "/usr/bin/say")
    monkeypatch.setattr(pronounce.subprocess, "run", lambda *a, **k: Done())
    monkeypatch.setitem(pronounce._voice_cache, "at", 0.0)  # pylint: disable=protected-access
    yield
    monkeypatch.setitem(pronounce._voice_cache, "at", 0.0)  # pylint: disable=protected-access


def test_mac_voices_are_found_by_language_and_ranked(mac_listing):  # pylint: disable=unused-argument
    names = [v["name"] for v in pronounce.mac_voices("it")]
    assert names == ["Federica (Premium)", "Luca (Enhanced)", "Alice (Italian (Italy))", "Eddy (Italian (Italy))"]  # no duplicate, novelty last
    assert pronounce.mac_voice("it") == "Federica (Premium)"
    assert pronounce.mac_voice("fr") == "Amélie" and pronounce.mac_voice("pl") == "Zosia"
    assert pronounce.mac_voice("de") is None


def test_the_voice_you_chose_wins_when_it_is_installed(mac_listing):  # pylint: disable=unused-argument
    assert pronounce.mac_voice("it", "Alice (Italian (Italy))") == "Alice (Italian (Italy))"
    assert pronounce.mac_voice("it", "Gone (Italian (Italy))") == "Federica (Premium)"


def test_a_language_without_voice_models_still_gets_the_mac_voice(app, client, monkeypatch):
    "Italian: no AI model covers it, so the answer comes from the Mac and says why."
    monkeypatch.setattr("ocarina.tts.models.speech_models", lambda: [])
    with app.app_context():
        italian = _get_test_language("Dutch")
        italian.name = "Italian"
        db.session.add(italian)
        db.session.commit()
        language_id = italian.id
    r = client.post(SAY, json={"text": "ciao", "languageId": language_id})
    assert r.status_code == 200 and r.json["source"] == "system" and "do not cover" in r.json["note"]


def test_the_system_voices_are_listed_per_language(app, client, mac_listing):  # pylint: disable=unused-argument
    dutch_id(app)
    rows = client.get(SAY + "/system-voices").json
    dutch = next(r for r in rows if r["language"] == "Dutch")
    assert dutch["code"] == "nl" and dutch["voices"] == [] and dutch["chosen"] is None


def test_automatic_uses_the_first_source_that_works(app, client, monkeypatch):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    r = client.post(SAY, json={"text": "fiets", "languageId": dutch_id(app), "source": "auto"})
    assert r.json["source"] == "voice" and r.json["note"] is None
    monkeypatch.setattr("ocarina.tts.models.is_installed", lambda model: False)
    app.config["OCARINA_TTS_ENGINE"] = None
    r = client.post(SAY, json={"text": "fiets", "languageId": dutch_id(app), "source": "auto"})
    assert r.json["source"] == "system" and r.json["note"] is None  # no model: the Mac speaks, nothing to apologise for


def test_automatic_goes_on_to_a_recording_and_never_to_google(app, client, monkeypatch):
    monkeypatch.setattr("ocarina.tts.models.is_installed", lambda model: False)

    def no_mac(cfg, text, code, locale=None):
        raise pronounce.Unavailable(pronounce.NO_MAC_VOICE)

    monkeypatch.setattr(pronounce, "_from_system", no_mac)
    monkeypatch.setattr(pronounce, "_from_speaker", lambda cfg, text, code: pronounce.cache_path(cfg.datapath, "speaker\nx"))
    monkeypatch.setattr(pronounce, "_from_google", lambda *a: pytest.fail("Google must be chosen, not automatic"))
    path = pronounce.cache_path(client.application.env_config.datapath, "speaker\nx")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(b"RIFF")
    r = client.post(SAY, json={"text": "fiets", "languageId": dutch_id(app), "source": "auto"})
    assert r.json["source"] == "speaker"
    monkeypatch.setattr(pronounce, "_from_speaker", lambda cfg, text, code: (_ for _ in ()).throw(pronounce.Unavailable("Wiktionary has no recording of this word.")))
    r = client.post(SAY, json={"text": "fiets", "languageId": dutch_id(app), "source": "auto"})
    assert r.status_code == 503 and "Manage Voices" in r.json["error"] and "Settings → Models" in r.json["error"]


def test_a_mac_voice_can_be_previewed_and_unknown_ones_are_refused(app, client, mac_listing, monkeypatch):  # pylint: disable=unused-argument
    made = []

    def speak(cfg, voice, text):
        made.append((voice, text))
        out = pronounce.cache_path(cfg.datapath, f"system\n{voice}\n{text}")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "wb").write(b"RIFF")
        return out

    monkeypatch.setattr(pronounce, "_speak_with", speak)
    r = client.post(SAY + "/system-voices/preview", json={"name": "Luca (Enhanced)"})
    assert r.status_code == 200 and made == [("Luca (Enhanced)", "Ciao! Mi chiamo Luca.")]
    assert client.post(SAY + "/system-voices/preview", json={"name": "Nobody"}).status_code == 404


def test_system_settings_opens_at_spoken_content(client, monkeypatch):
    calls = []

    class Done:
        returncode = 0

    monkeypatch.setattr(pronounce.tools, "find", lambda name: "/usr/bin/open")
    monkeypatch.setattr(pronounce.subprocess, "run", lambda cmd, **k: (calls.append(cmd), Done())[1])
    assert client.post(SAY.replace("pronounce", "pronounce/open-voice-settings")).json == {"ok": True}
    assert calls == [["/usr/bin/open", pronounce.VOICE_SETTINGS_URL]]


PT_LISTING = """\
Joana               pt_PT    # Olá! Chamo-me Joana.
Luciana             pt_BR    # Olá! Meu nome é Luciana.
Catarina (Premium)  pt_PT    # Olá! Chamo-me Catarina.
"""


def test_each_portuguese_gets_the_voice_of_its_own_locale(monkeypatch):
    class Done:
        stdout = PT_LISTING

    monkeypatch.setattr(pronounce.tools, "find", lambda name: "/usr/bin/say")
    monkeypatch.setattr(pronounce.subprocess, "run", lambda *a, **k: Done())
    monkeypatch.setitem(pronounce._voice_cache, "at", 0.0)  # pylint: disable=protected-access
    assert [v["name"] for v in pronounce.mac_voices("pt", "pt_PT")] == ["Catarina (Premium)", "Joana", "Luciana"]
    assert [v["name"] for v in pronounce.mac_voices("pt", "pt_BR")] == ["Luciana", "Catarina (Premium)", "Joana"]
    assert pronounce.mac_voice("pt", None, "pt_BR") == "Luciana" and pronounce.mac_voice("pt") == "Catarina (Premium)"
    monkeypatch.setitem(pronounce._voice_cache, "at", 0.0)  # pylint: disable=protected-access
    from ocarina import translate  # pylint: disable=import-outside-toplevel

    assert translate.code_for("European Portuguese") == "pt" and translate.locale_of("Brazilian Portuguese") == "pt_BR" and translate.locale_of("Dutch") is None


def test_live_reading_speaks_with_the_chosen_mac_voice_and_can_be_stopped(app, client, monkeypatch):
    from ocarina import live_speech

    said = []
    monkeypatch.setattr(pronounce, "mac_voice", lambda code, chosen=None, locale=None: "Xander")
    monkeypatch.setattr(live_speech, "speak", lambda text, voice, wpm=None: said.append((text, voice, wpm)) or True)
    stopped = []
    monkeypatch.setattr(live_speech, "stop", lambda: stopped.append(1))
    r = client.post("/ocarina/api/speak", json={"text": " Hallo daar. ", "languageId": dutch_id(app), "rate": 2})
    assert r.json == {"finished": True, "voice": "Xander"} and said == [("Hallo daar.", "Xander", 350)]
    assert client.post("/ocarina/api/speak/stop").status_code == 200 and stopped == [1]


def test_live_reading_without_a_mac_voice_says_why(app, client, monkeypatch):
    monkeypatch.setattr(pronounce, "mac_voice", lambda code, chosen=None, locale=None: None)
    r = client.post("/ocarina/api/speak", json={"text": "Hallo", "languageId": dutch_id(app)})
    assert r.status_code == 409 and r.json["code"] == "no_mac_voice"
    assert client.post("/ocarina/api/speak", json={"text": "", "languageId": dutch_id(app)}).status_code == 400
