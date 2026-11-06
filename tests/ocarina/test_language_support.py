"""
What Ocarina can do for a language: the table behind Settings → Languages.
"""

from ocarina import language_support, pronounce
from ocarina.tts import models


def test_a_language_the_models_cover_is_full_once_meanings_are_here(monkeypatch):
    monkeypatch.setattr(models, "is_installed", lambda m: False)
    monkeypatch.setattr(pronounce, "mac_voices", lambda code: [{"name": "Zosia"}])
    monkeypatch.setattr(language_support.registry, "active", lambda datapath, code: ["pack"])
    found = language_support.support("Polish", "/nowhere")
    assert found["code"] == "pl" and found["level"] == "full"
    assert (found["meanings"], found["aiVoice"], found["translation"], found["audioSync"], found["macVoice"]) == ("ready", "download", "download", "download", "ready")
    monkeypatch.setattr(models, "is_installed", lambda m: True)
    assert language_support.support("Polish", "/nowhere")["aiVoice"] == "ready"


def test_italian_has_no_ai_models_yet_so_it_is_basic(monkeypatch):
    monkeypatch.setattr(pronounce, "mac_voices", lambda code: [{"name": "Alice"}])
    monkeypatch.setattr(language_support.registry, "active", lambda datapath, code: ["pack"])
    found = language_support.support("Italian", "/nowhere")
    assert found["code"] == "it" and found["level"] == "basic"
    assert (found["aiVoice"], found["translation"], found["macVoice"]) == ("none", "none", "ready")


def test_meanings_fall_back_to_online_and_unknown_languages_get_a_plain_answer(monkeypatch):
    monkeypatch.setattr(pronounce, "mac_voices", lambda code: [])
    monkeypatch.setattr(language_support.registry, "active", lambda datapath, code: [])
    assert language_support.support("French", "/nowhere")["meanings"] == "online"
    found = language_support.support("Klingon", "/nowhere")
    assert found["code"] is None and found["level"] == "basic" and found["macVoice"] == "none"


def test_the_route_lists_the_library_or_the_names_asked(client, app):
    names = [r["language"] for r in client.get("/ocarina/api/languages/support").json]
    assert names == sorted(names)
    rows = client.get("/ocarina/api/languages/support?names=Italian,Dutch").json
    assert [r["language"] for r in rows] == ["Italian", "Dutch"]


def test_a_book_in_a_language_no_voice_model_covers_cannot_be_voiced(app, client):
    from lute.db import db  # pylint: disable=import-outside-toplevel
    from tests.ocarina.helpers import make_dutch_book  # pylint: disable=import-outside-toplevel

    with app.app_context():
        book = make_dutch_book()
        book.language.name = "Italian"
        db.session.commit()
        book_id = book.id
    options = client.get(f"/ocarina/api/books/{book_id}/audio/options")
    assert options.status_code == 400 and options.json["code"] == "unsupported_language"
    assert "Italian" in options.json["error"] and "Mac voice" in options.json["error"]
    started = client.post(f"/ocarina/api/books/{book_id}/audio", json={})
    assert started.status_code == 400 and started.json["code"] == "unsupported_language"  # not voiced with another language's model


def test_a_language_a_model_lists_can_be_voiced(monkeypatch):
    from ocarina.tts import book_audio  # pylint: disable=import-outside-toplevel

    class Lang:
        name = "Italian"

    assert not book_audio.tts_lang.__defaults__  # the function takes just the language
    monkeypatch.setattr(models, "speech_models", lambda: [{"languages": ["nl", "it"]}])
    assert book_audio.tts_lang(Lang()) == "it"
