"""
Work offline: with the switch on, nothing is asked of the internet. Every feature that would says so, and a safety net stops what was missed.
"""

import socket
import urllib.request

import pytest
import requests

from ocarina import dictionary, offline, pronounce
from ocarina.dictionaries import registry, setup
from tests.conftest import _get_test_language
from tests.ocarina.helpers import make_dutch_book
from tests.ocarina.test_dictionaries import make_pack  # noqa: F401  pylint: disable=unused-import

SWITCH = "/ocarina/api/offline"


@pytest.fixture(autouse=True)
def folders(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "BUILTIN_DIR", str(tmp_path / "builtin"))
    monkeypatch.setattr(registry, "user_dir", lambda datapath: str(tmp_path / "user"))
    registry._open.clear()  # pylint: disable=protected-access
    return tmp_path


@pytest.fixture
def offline_on(client):
    assert client.put(SWITCH, json={"offline": True}).json["offline"] is True
    yield
    client.put(SWITCH, json={"offline": False})


def test_the_switch_is_kept(client):
    assert client.get(SWITCH).json["offline"] is False
    assert client.put(SWITCH, json={"offline": True}).json["offline"] is True
    assert offline.is_on() is True
    assert client.put(SWITCH, json={"offline": False}).json["offline"] is False and offline.is_on() is False
    assert client.put(SWITCH, json={"offline": "yes"}).status_code == 400


def test_the_safety_net_stops_anything_that_reaches_another_computer(offline_on):
    with pytest.raises(offline.OfflineMode):
        requests.get("https://example.org", timeout=2)
    with pytest.raises(offline.OfflineMode):
        urllib.request.urlopen("https://example.org", timeout=2)
    with pytest.raises(offline.OfflineMode):
        socket.create_connection(("93.184.216.34", 80), timeout=2)
    # this Mac itself is not another computer: a refused connection is a plain one
    with pytest.raises(requests.exceptions.ConnectionError) as e:
        requests.get("http://127.0.0.1:9/", timeout=2)
    assert not isinstance(e.value, offline.OfflineMode)
    assert "Work offline" in str(offline.OfflineMode("Translation"))


def test_with_the_switch_off_nothing_is_stopped(client):
    with pytest.raises(requests.exceptions.ConnectionError) as e:
        requests.get("http://127.0.0.1:9/", timeout=2)
    assert not isinstance(e.value, offline.OfflineMode)


def test_a_word_is_looked_up_in_the_packs_and_never_on_the_internet(app, client, folders, offline_on, monkeypatch):
    make_pack(folders / "builtin", "a", "A", "nl", [("huis", "noun", ["house"])])
    monkeypatch.setattr(dictionary, "_fetch", lambda *a: pytest.fail("Wiktionary must not be asked while offline"))
    with app.app_context():
        lang_id = _get_test_language("Dutch").id
    got = client.get(f"/ocarina/api/dictionary/define?languageId={lang_id}&text=huis&online=true").json
    assert got["source"]["id"] == "a" and got["others"] == []  # the second opinion from Wiktionary is not asked for
    missing = client.get(f"/ocarina/api/dictionary/define?languageId={lang_id}&text=onbekend").json
    assert missing == {"found": False, "cacheMiss": True}


def test_only_a_model_on_this_mac_translates(app, client, offline_on):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    client.put("/ocarina/api/translate/settings", json={"provider": "mymemory", "target": "en"})
    settings = client.get("/ocarina/api/translate/settings").json
    assert settings["offline"] is True and settings["provider"] == "local"  # the choice of an online service is not used
    with app.app_context():
        lang_id = _get_test_language("Dutch").id
        book_id = make_dutch_book("Offline").id
    r = client.post("/ocarina/api/translate", json={"languageId": lang_id, "text": "Goedemorgen."})
    assert r.status_code == 200 and r.json["provider"] == "local"
    status = client.get(f"/ocarina/api/books/{book_id}/translation").json
    online = [m for m in status["methods"] if m["provider"] in ("mymemory", "deepl")]
    assert online and all(not m["available"] and m["reason"] == "Work offline is on" for m in online)
    refused = client.post(f"/ocarina/api/books/{book_id}/translation", json={"scope": "book", "provider": "mymemory"})
    assert refused.status_code == 409 and refused.json["code"] == "offline_mode"
    client.put("/ocarina/api/translate/settings", json={"provider": "local"})


def test_a_word_is_said_by_the_chosen_voice_not_by_a_server(app, client, offline_on, monkeypatch):
    "A source that needs the internet (chosen before the switch went on) gives way to the voice of the language, then to the Mac's."
    with app.app_context():
        lang_id = _get_test_language("Dutch").id
    made = lambda cfg, *a: __import__("os").path.join(cfg.datapath, "x.wav")
    monkeypatch.setattr(pronounce, "_from_voice", made)
    monkeypatch.setattr(pronounce, "_from_system", made)
    for source in ("google", "speaker"):
        r = client.post("/ocarina/api/pronounce", json={"text": "fiets", "languageId": lang_id, "source": source})
        assert r.status_code == 200 and r.json["source"] == "voice" and r.json["note"] is None

    def no_voice(*a):
        raise pronounce.Unavailable("No voice model is chosen.")

    monkeypatch.setattr(pronounce, "_from_voice", no_voice)
    r = client.post("/ocarina/api/pronounce", json={"text": "fiets", "languageId": lang_id, "source": "google"})
    assert r.status_code == 200 and r.json["source"] == "system"


def test_nothing_is_added_from_a_web_address(client, offline_on):
    for url in ("https://example.org/article", "https://youtu.be/dQw4w9WgXcQ"):
        r = client.post("/ocarina/api/books/extract", json={"url": url})
        assert r.status_code == 409 and r.json["code"] == "offline_mode" and "Work offline" in r.json["error"]


def test_nothing_is_downloaded(client, offline_on):
    r = client.post("/ocarina/api/dictionaries/wiktionary-nl-en/download")
    assert r.status_code == 409 and r.json["code"] == "offline_mode"
    model_id = client.get("/ocarina/api/tts/models").json[0]["id"]
    assert client.post(f"/ocarina/api/tts/models/{model_id}/download").status_code in (409,)  # (or already installed: 409 as well)
    assert client.post("/ocarina/api/tts/models/lookup", json={"repo": "a/b"}).status_code == 409
    assert client.post("/ocarina/api/tts/models/custom", json={"repo": "a/b", "engine": "mlx-audio8", "languages": ["nl"]}).status_code == 409


def test_a_new_language_does_not_start_a_download(app, offline_on):
    with app.app_context():
        assert setup.ensure_default(app.env_config.datapath, "Dutch") is None


def test_the_check_says_what_each_language_has_on_this_mac(app, client, folders):
    with app.app_context():
        _get_test_language("Dutch")
        _get_test_language("French")
    make_pack(folders / "builtin", "nl-pack", "Dutch pack", "nl", [("a", "", ["b"])])
    got = client.get(SWITCH).json
    by_code = {l["code"]: l for l in got["languages"]}
    assert by_code["nl"]["dictionary"] == {"ok": True, "names": ["Dutch pack"]}
    assert by_code["fr"]["dictionary"] == {"ok": False, "names": []}
    assert {"ok", "names"} <= set(by_code["nl"]["translation"]) and {"ok", "names"} <= set(by_code["nl"]["voice"])
    assert set(got["audioSync"]) == {"ok", "name"}
