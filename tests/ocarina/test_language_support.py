"""
What Ocarina can do for a language: the table behind Settings → Languages.
"""

from ocarina import language_support, pronounce
from ocarina.tts import models


def test_a_language_the_models_cover_is_full_once_meanings_are_here(monkeypatch):
    monkeypatch.setattr(models, "is_installed", lambda m: False)
    monkeypatch.setattr(pronounce, "mac_voices", lambda code, locale=None: [{"name": "Zosia"}])
    monkeypatch.setattr(language_support.registry, "active", lambda datapath, code: ["pack"])
    found = language_support.support("Polish", "/nowhere")
    assert found["code"] == "pl" and found["level"] == "full"
    assert (found["meanings"], found["aiVoice"], found["translation"], found["audioSync"], found["macVoice"]) == ("ready", "download", "download", "download", "ready")  # the aligner does not list Polish, but it was tried and works
    monkeypatch.setattr(models, "is_installed", lambda m: True)
    assert language_support.support("Polish", "/nowhere")["aiVoice"] == "ready"


def test_a_language_with_no_voice_model_is_basic(monkeypatch):
    monkeypatch.setattr(models, "is_installed", lambda m: False)  # whatever this Mac has downloaded
    monkeypatch.setattr(pronounce, "mac_voices", lambda code, locale=None: [{"name": "Alice"}])
    monkeypatch.setattr(language_support.registry, "active", lambda datapath, code: ["pack"])
    found = language_support.support("Albanian", "/nowhere")  # no voice model lists it, the translation models do
    assert found["code"] == "sq" and found["level"] == "basic"
    assert (found["aiVoice"], found["translation"], found["macVoice"]) == ("none", "download", "ready")
    assert language_support.support("Italian", "/nowhere")["level"] == "full"  # the makers list Italian for the voice, and it was measured for translation


def test_meanings_fall_back_to_online_and_unknown_languages_get_a_plain_answer(monkeypatch):
    monkeypatch.setattr(pronounce, "mac_voices", lambda code, locale=None: [])
    monkeypatch.setattr(language_support.registry, "active", lambda datapath, code: [])
    assert language_support.support("French", "/nowhere")["meanings"] == "online"
    found = language_support.support("Klingon", "/nowhere")
    assert found["code"] is None and found["level"] == "basic" and found["macVoice"] == "none"


def test_the_route_lists_the_library_or_the_names_asked(client, app):
    names = [r["language"] for r in client.get("/ocarina/api/languages/support").json]
    assert names == sorted(names)
    rows = client.get("/ocarina/api/languages/support?names=Italian,Dutch").json
    assert [r["language"] for r in rows] == ["Italian", "Dutch"]


def _book_in(app, language_name):
    from lute.db import db  # pylint: disable=import-outside-toplevel
    from tests.ocarina.helpers import make_dutch_book  # pylint: disable=import-outside-toplevel

    with app.app_context():
        book = make_dutch_book()
        book.language.name = language_name
        db.session.commit()
        return book.id


def test_a_book_in_a_language_no_voice_covers_cannot_be_voiced(app, client, monkeypatch):
    monkeypatch.setattr(pronounce, "mac_voices", lambda code, locale=None: [])  # this Mac has no Albanian voice either
    book_id = _book_in(app, "Albanian")
    options = client.get(f"/ocarina/api/books/{book_id}/audio/options")
    assert options.status_code == 400 and options.json["code"] == "unsupported_language"
    assert "Albanian" in options.json["error"] and "Mac voice" in options.json["error"]
    started = client.post(f"/ocarina/api/books/{book_id}/audio", json={})
    assert started.status_code == 400 and started.json["code"] == "unsupported_language"  # not voiced with another language's model


def test_a_book_is_read_by_the_mac_voice_when_no_model_covers_the_language(app, client, monkeypatch):
    monkeypatch.setattr(pronounce, "mac_voices", lambda code, locale=None: [{"name": "Alice (Albanian)", "novelty": False}])
    monkeypatch.setattr(pronounce, "mac_voice", lambda code, chosen=None, locale=None: "Alice (Albanian)")
    book_id = _book_in(app, "Albanian")
    options = client.get(f"/ocarina/api/books/{book_id}/audio/options").json
    assert options["defaultModel"] == "mac-voice"
    assert [m["id"] for m in options["models"]] == ["mac-voice"]
    assert {"id": "mac:Alice (Albanian)", "name": "Alice", "builtin": True, "model": "mac-voice"} in options["voices"]


def test_a_language_a_model_lists_can_be_voiced(monkeypatch):
    from ocarina.tts import book_audio  # pylint: disable=import-outside-toplevel

    class Lang:
        name = "Italian"

    assert not book_audio.tts_lang.__defaults__  # the function takes just the language
    monkeypatch.setattr(models, "speech_models", lambda: [{"languages": ["nl", "it"]}])
    assert book_audio.tts_lang(Lang()) == "it"


def test_command_output_is_read_as_utf8_whatever_the_process_locale(monkeypatch):
    "The packaged app starts Python in ASCII mode: voice names like Amélie must not break reading `say -v ?`."
    seen = {}

    class Done:
        stdout = "Amélie    fr_CA    # Bonjour!\n"

    def run(cmd, **kwargs):
        seen.update(kwargs)
        return Done()

    monkeypatch.setattr(pronounce.tools, "find", lambda name: "/usr/bin/say")
    monkeypatch.setattr(pronounce.subprocess, "run", run)
    monkeypatch.setitem(pronounce._voice_cache, "at", 0.0)  # pylint: disable=protected-access
    assert [v["name"] for v in pronounce.mac_voices("fr")] == ["Amélie"]
    assert seen["encoding"] == "utf-8" and seen["errors"] == "replace"
    monkeypatch.setitem(pronounce._voice_cache, "at", 0.0)  # pylint: disable=protected-access
