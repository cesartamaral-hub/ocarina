"""
Sentence translation: providers, cache, settings, the DeepL key, and every kind of failure. The network is faked.
"""

import os
import shutil
import stat

import pytest
import requests

from ocarina import keystore, prefs, translate
from tests.conftest import _get_test_language

URL = "/ocarina/api/translate"


class Reply:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def mymemory_ok(text="Why did we let them go?"):
    return Reply(200, {"responseData": {"translatedText": text, "match": 0.9}, "responseStatus": 200})


@pytest.fixture(autouse=True)
def net(app, monkeypatch):
    "A fake translation service that records its calls, and clean settings, cache and key around each test."
    datapath = app.env_config.datapath

    def clean():
        shutil.rmtree(os.path.join(datapath, "translation_cache"), ignore_errors=True)
        for name in (prefs.path_for(datapath), keystore.path_for(datapath)):
            if os.path.exists(name):
                os.remove(name)

    clean()
    state = {"calls": [], "mymemory": mymemory_ok(), "deepl": Reply(200, {"translations": [{"text": "Why did we let them go?"}]}), "down": False}

    def fake_get(url, headers=None, timeout=None, params=None):  # pylint: disable=unused-argument
        state["calls"].append(("mymemory", params))
        if state["down"]:
            raise requests.exceptions.ConnectionError("offline")
        return state["mymemory"]

    def fake_post(url, headers=None, json=None, timeout=None):  # pylint: disable=unused-argument,redefined-outer-name
        state["calls"].append(("deepl", url, headers["Authorization"], json))
        if state["down"]:
            raise requests.exceptions.ConnectionError("offline")
        return state["deepl"]

    monkeypatch.setattr(translate.model_files, "is_installed", lambda m: False)  # the real cache of this Mac must not matter
    monkeypatch.setattr(translate.requests, "get", fake_get)
    monkeypatch.setattr(translate.requests, "post", fake_post)
    yield state
    clean()


def _dutch(app):
    with app.app_context():
        return _get_test_language("Dutch").id


def _ask(client, app, text="Waarom hebben we ze eigenlijk laten gaan?"):
    return client.post(URL, json={"languageId": _dutch(app), "text": text})


def test_default_settings_and_choices(client):
    "Out of the box: MyMemory, into English, no key."
    s = client.get(f"{URL}/settings").json
    assert (s["provider"], s["target"], s["hasDeeplKey"], s["email"]) == ("mymemory", "en", False, "")
    assert [p["id"] for p in s["providers"]] == ["local", "mymemory", "deepl"] and "en" in [t["code"] for t in s["targets"]]
    assert s["localModel"]["id"] == "qwen3-4b-instruct-mlx" and s["localModel"]["installed"] is False


def test_mymemory_translates_and_the_second_time_comes_from_the_cache(app, client, net):
    "The service is asked once; the same sentence is then answered from the cache."
    first = _ask(client, app)
    assert first.status_code == 200 and first.json["translation"] == "Why did we let them go?"
    assert (first.json["provider"], first.json["source"], first.json["target"], first.json["cached"]) == ("mymemory", "nl", "en", False)
    assert net["calls"][0][1] == {"q": "Waarom hebben we ze eigenlijk laten gaan?", "langpair": "nl|en"}
    again = _ask(client, app).json
    assert again["cached"] is True and len(net["calls"]) == 1


def test_an_email_is_sent_to_mymemory_for_the_bigger_quota(app, client, net):
    "The optional email goes along as MyMemory's 'de' parameter."
    assert client.put(f"{URL}/settings", json={"email": "ik@example.com"}).status_code == 200
    _ask(client, app)
    assert net["calls"][0][1]["de"] == "ik@example.com"


def test_deepl_needs_a_key_and_uses_the_right_server(app, client, net):
    "Without a key DeepL says so; with a free key (ending :fx) the free server is used; English means EN-GB."
    client.put(f"{URL}/settings", json={"provider": "deepl"})
    refused = _ask(client, app)
    assert refused.status_code == 400 and refused.json["code"] == "no_key" and net["calls"] == []
    client.put(f"{URL}/settings", json={"deeplKey": "abc-123:fx"})
    ok = _ask(client, app)
    assert ok.status_code == 200 and ok.json["provider"] == "deepl"
    _, url, auth, body = net["calls"][0]
    assert url == "https://api-free.deepl.com/v2/translate" and auth == "DeepL-Auth-Key abc-123:fx"
    assert body == {"text": ["Waarom hebben we ze eigenlijk laten gaan?"], "source_lang": "NL", "target_lang": "EN-GB"}
    client.put(f"{URL}/settings", json={"deeplKey": "paid-key"})
    _ask(client, app, "Een andere zin.")
    assert net["calls"][1][1] == "https://api.deepl.com/v2/translate"


def test_the_key_is_never_sent_back_and_its_file_is_private(app, client):
    "The page learns only that a key exists and its last characters; the file is readable by you alone."
    client.put(f"{URL}/settings", json={"provider": "deepl", "deeplKey": "secret-key-1234:fx"})
    s = client.get(f"{URL}/settings")
    assert s.json["hasDeeplKey"] is True and s.json["deeplKeyHint"] == "…4:fx"
    assert "secret-key" not in s.get_data(as_text=True) and "secret-key" not in client.get("/ocarina/api/prefs").get_data(as_text=True)
    path = keystore.path_for(app.env_config.datapath)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert client.put(f"{URL}/settings", json={"deeplKey": ""}).json["hasDeeplKey"] is False
    assert keystore.get(app.env_config.datapath, "deepl") is None


def test_settings_are_validated(client):
    "Unknown services and targets, bad emails and keys with spaces are refused; nothing is half-saved."
    assert client.put(f"{URL}/settings", json={"provider": "nope"}).status_code == 400
    assert client.put(f"{URL}/settings", json={"target": "xx"}).status_code == 400
    assert client.put(f"{URL}/settings", json={"email": "not an email"}).status_code == 400
    assert client.put(f"{URL}/settings", json={"deeplKey": "has space"}).status_code == 400
    assert client.put(f"{URL}/settings", json={"target": "nl", "provider": "deepl"}).json["target"] == "nl"


def test_failures_are_explained(app, client, net):
    "Offline, quota, bad key and a broken answer each give their own code and a readable message."
    net["down"] = True
    off = _ask(client, app)
    assert off.status_code == 502 and off.json["code"] == "offline" and "connection" in off.json["error"]
    net["down"] = False
    net["mymemory"] = Reply(200, {"responseData": {"translatedText": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY"}, "responseStatus": 200})
    quota = _ask(client, app, "Een zin.")
    assert quota.status_code == 429 and quota.json["code"] == "quota"
    net["mymemory"] = Reply(200, None)
    assert _ask(client, app, "Nog een zin.").json["code"] == "failed"
    client.put(f"{URL}/settings", json={"provider": "deepl", "deeplKey": "k:fx"})
    net["deepl"] = Reply(403)
    assert _ask(client, app, "Zin A.").json["code"] == "bad_key"
    net["deepl"] = Reply(456)
    assert _ask(client, app, "Zin B.").json["code"] == "quota"
    net["deepl"] = Reply(500)
    assert _ask(client, app, "Zin C.").status_code == 502


def test_nothing_is_cached_when_it_fails(app, client, net):
    "A failure is not remembered: the next try asks the service again."
    net["down"] = True
    _ask(client, app)
    net["down"] = False
    assert _ask(client, app).json["cached"] is False and len(net["calls"]) == 2


def test_input_is_checked(app, client):
    "Empty and too long text, an unknown language, an unknown language code and same-language targets."
    assert _ask(client, app, "   ").json["code"] == "bad_input"
    assert _ask(client, app, "x" * 501).json["code"] == "too_long"
    assert client.post(URL, json={"languageId": 99999, "text": "hoi"}).status_code == 404
    assert client.post(URL, json={"text": "hoi"}).status_code == 404
    client.put(f"{URL}/settings", json={"target": "nl"})
    assert _ask(client, app).json["code"] == "bad_input"  # Dutch into Dutch
    assert translate.code_for("Polski") == "pl" and translate.code_for("Klingon") is None


def test_the_test_button_really_asks_the_service(app, client, net):
    "The trial translation skips the cache, so a wrong key shows up."
    ok = client.post(f"{URL}/test")
    assert ok.status_code == 200 and ok.json["cached"] is False
    client.post(f"{URL}/test")
    assert len([c for c in net["calls"] if c[0] == "mymemory"]) == 2
    client.put(f"{URL}/settings", json={"provider": "deepl", "deeplKey": "bad:fx"})
    net["deepl"] = Reply(403)
    assert client.post(f"{URL}/test").json["code"] == "bad_key"


def test_the_local_model_translates_through_its_worker(app, client, net, monkeypatch):
    "With the model on this Mac, nothing goes over the network; the answer is cached like any other."
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    client.put(f"{URL}/settings", json={"provider": "local"})
    first = _ask(client, app, "Hoe gaat het?")
    assert first.status_code == 200 and first.json["provider"] == "local"
    assert first.json["translation"] == "[fake translation] Hoe gaat het?"
    assert net["calls"] == []
    asked = []
    real = translate.local_model.complete
    monkeypatch.setattr(translate.local_model, "complete", lambda *a, **k: (asked.append(1), real(*a, **k))[1])
    assert _ask(client, app, "Hoe gaat het?").json["cached"] is True and asked == []
    translate.local_model.unload()


def test_the_local_model_must_be_downloaded_first(app, client):
    "Without the files (and without the test engine) the answer says to download it."
    client.put(f"{URL}/settings", json={"provider": "local"})
    r = _ask(client, app)
    assert r.status_code == 400 and r.json["code"] == "no_model" and "Download" in r.json["error"]


def test_local_becomes_the_default_once_it_is_downloaded(client, monkeypatch):
    "Before the model is installed the default is MyMemory; after, the model on this Mac, unless you chose."
    assert client.get(f"{URL}/settings").json["provider"] == "mymemory"
    monkeypatch.setattr(translate.model_files, "is_installed", lambda m: True)
    assert client.get(f"{URL}/settings").json["provider"] == "local"
    client.put(f"{URL}/settings", json={"provider": "deepl"})
    assert client.get(f"{URL}/settings").json["provider"] == "deepl"


def test_text_models_are_not_offered_for_voicing_books(client):
    "Speech choices ignore the translation model, and a text model cannot be asked to voice a book."
    from ocarina.tts import models as model_files  # pylint: disable=import-outside-toplevel

    assert model_files.choose_model("qwen3-4b-instruct-mlx") is None
    assert all(model_files.kind_of(m) == "speech" for m in model_files.speech_models())
    listed = {m["id"]: m["kind"] for m in client.get("/ocarina/api/tts/models").json}
    assert listed["qwen3-4b-instruct-mlx"] == "text" and listed["chatterbox-multilingual-v3-mlx"] == "speech"


def test_the_local_model_unloads_after_a_quiet_spell(app):
    "It stays loaded between requests and gives its memory back when idle."
    import time  # pylint: disable=import-outside-toplevel
    from ocarina.localllm import LocalModel  # pylint: disable=import-outside-toplevel
    from ocarina.tts import models as model_files  # pylint: disable=import-outside-toplevel

    model = model_files.find_model("qwen3-4b-instruct-mlx")
    runner = LocalModel(idle_seconds=0.3)
    assert runner.complete(model, "system", "Dutch sentence:\nHallo", engine="fake") == "[fake translation] Hallo"
    first = runner._supervisor  # pylint: disable=protected-access
    runner.complete(model, "system", "Dutch sentence:\nTot ziens", engine="fake")
    assert runner._supervisor is first  # pylint: disable=protected-access
    time.sleep(0.8)
    assert runner._supervisor is None  # pylint: disable=protected-access
