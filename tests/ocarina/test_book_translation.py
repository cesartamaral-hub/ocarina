"""
The translated version of a book: making it (a page or all), keeping it per sentence, noticing edits, correcting by hand.
The translation service is the fake local model (it answers "[fake translation] <sentence>").
"""

import pytest

from lute.db import db
from lute.models.repositories import BookRepository
from ocarina import translate
from tests.ocarina.helpers import make_dutch_book, wait_for_job

BOOKS = "/ocarina/api/books"


@pytest.fixture(autouse=True)
def fake_model(app, client):
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    client.put("/ocarina/api/translate/settings", json={"provider": "local", "target": "en"})
    yield
    translate.local_model.unload()


def _book(app, name):
    with app.app_context():
        return make_dutch_book(name).id


def _get(client, book_id):
    return client.get(f"{BOOKS}/{book_id}/translation").json


def _make(client, book_id, **body):
    r = client.post(f"{BOOKS}/{book_id}/translation", json=body)
    assert r.status_code == 202, r.json
    return wait_for_job(client, r.json["id"])


def test_a_new_book_has_nothing_translated_and_says_how_much_there_is(app, client):
    status = _get(client, _book(app, "Leeg"))
    assert status["total"] == 4 and status["done"] == 0 and status["remainingChars"] > 40
    assert [(s["page"], s["index"]) for s in status["sentences"]] == [(1, 0), (1, 1), (1, 2), (2, 0)]
    assert all(s["translation"] is None and not s["stale"] for s in status["sentences"])
    assert set(status["remainingByPage"]) == {"1", "2"} and sum(status["remainingByPage"].values()) == status["remainingChars"]
    assert status["target"] == "en" and status["targetName"] == "English" and status["provider"] == "local"


def test_a_page_can_be_translated_alone(app, client):
    book_id = _book(app, "Een pagina")
    job = _make(client, book_id, scope="page", page=2)
    assert job["state"] == "done" and job["done"] == job["total"] == 1
    sentences = _get(client, book_id)["sentences"]
    assert [s["translation"] for s in sentences] == [None, None, None, "[fake translation] Elke ochtend sta ik op."]


def test_the_whole_book_is_translated_and_a_second_run_has_nothing_to_do(app, client):
    book_id = _book(app, "Alles")
    assert _make(client, book_id, scope="book")["state"] == "done"
    status = _get(client, book_id)
    assert status["done"] == 4 and status["remainingChars"] == 0
    assert status["sentences"][1]["translation"] == "[fake translation] Mijn naam is Carla."
    again = _make(client, book_id, scope="book")
    assert again["state"] == "done" and again["total"] == 0  # nothing was left


def test_only_the_sentence_you_edit_is_translated_again(app, client):
    book_id = _book(app, "Bewerkt")
    _make(client, book_id, scope="book")
    page = client.get(f"{BOOKS}/{book_id}/pages/2/text").json["text"]
    client.put(f"{BOOKS}/{book_id}/pages/2/text", json={"text": page.replace("sta ik op", "ga ik naar bed")})
    status = _get(client, book_id)
    assert status["done"] == 3 and status["stale"] == 1
    assert [s["stale"] for s in status["sentences"]] == [False, False, False, True]
    assert status["sentences"][3]["translation"].startswith("[fake")  # the old one stays visible until replaced
    _make(client, book_id, scope="book")
    status = _get(client, book_id)
    assert status["stale"] == 0 and "ga ik naar bed" in status["sentences"][3]["translation"]


def test_a_correction_of_your_own_is_kept(app, client):
    book_id = _book(app, "Eigen woorden")
    _make(client, book_id, scope="book")
    r = client.put(f"{BOOKS}/{book_id}/translation/1/1", json={"text": "My name is Carla."})
    assert r.status_code == 200
    _make(client, book_id, scope="book")  # a new run does not replace it
    assert _get(client, book_id)["sentences"][1]["translation"] == "My name is Carla."
    assert client.put(f"{BOOKS}/{book_id}/translation/1/1", json={"text": "  "}).status_code == 400
    assert client.put(f"{BOOKS}/{book_id}/translation/9/9", json={"text": "x"}).status_code == 404


def test_the_book_must_be_in_another_language_than_the_target(app, client):
    book_id = _book(app, "Zelfde taal")
    client.put("/ocarina/api/translate/settings", json={"target": "nl"})
    r = client.post(f"{BOOKS}/{book_id}/translation", json={"scope": "book"})
    assert r.status_code == 400 and r.json["code"] == "bad_input"
    assert client.post(f"{BOOKS}/{book_id}/translation", json={"scope": "page"}).status_code == 400  # a page needs its number


def test_a_service_problem_stops_the_job_and_keeps_what_was_done(app, client, monkeypatch):
    book_id = _book(app, "Limiet")
    real, calls = translate.translate, []

    def limited(*args, **kwargs):
        calls.append(1)
        if len(calls) == 3:
            raise translate.TranslateError("MyMemory's free limit for today is used up.", "quota")
        return real(*args, **kwargs)

    monkeypatch.setattr(translate, "translate", limited)
    job = _make(client, book_id, scope="book")
    assert job["state"] == "error" and "limit" in job["error"]
    assert _get(client, book_id)["done"] == 2  # the two before it are kept


def test_removing_the_translation(app, client):
    book_id = _book(app, "Weg")
    _make(client, book_id, scope="book")
    assert client.delete(f"{BOOKS}/{book_id}/translation").status_code == 200
    assert _get(client, book_id)["done"] == 0
    assert client.get(f"{BOOKS}/99999/translation").status_code == 404


def test_deleting_the_book_deletes_its_translation(app, client):
    book_id = _book(app, "Meegenomen")
    _make(client, book_id, scope="book")
    client.delete(f"{BOOKS}/{book_id}")
    with app.app_context():
        assert db.session.execute(db.text("select count(*) from booktranslations where BtBkID = :b"), {"b": book_id}).scalar() == 0
        assert BookRepository(db.session).find(book_id) is None


def test_the_ways_to_translate_are_listed_with_the_default_marked(app, client):
    methods = _get(client, _book(app, "Methoden"))["methods"]
    names = [m["name"] for m in methods]
    assert "MyMemory" in names and "DeepL" in names and any("Qwen3" in n for n in names) and any("TranslateGemma" in n for n in names)
    assert [m["provider"] for m in methods if m["isDefault"]] == ["local"]
    assert next(m for m in methods if m["provider"] == "deepl")["available"] is False  # no key saved
    assert "key" in next(m for m in methods if m["provider"] == "deepl")["reason"]
    assert all(m["available"] for m in methods if m["provider"] != "deepl")  # the test engine counts models as downloaded


def test_another_method_can_be_used_for_one_run_without_changing_the_default(app, client):
    book_id = _book(app, "Andere")
    job = _make(client, book_id, scope="page", page=2, provider="local", model="translategemma-4b-mlx")
    assert job["state"] == "done"
    assert _get(client, book_id)["sentences"][3]["translation"].startswith("[fake translategemma")
    assert client.get("/ocarina/api/translate/settings").json["localModel"]["id"] == "qwen3-4b-instruct-mlx"  # the default stays


def test_a_method_that_cannot_be_used_is_refused_with_the_reason(app, client):
    book_id = _book(app, "Geen sleutel")
    r = client.post(f"{BOOKS}/{book_id}/translation", json={"scope": "book", "provider": "deepl"})
    assert r.status_code == 409 and "key" in r.json["error"]
    assert client.post(f"{BOOKS}/{book_id}/translation", json={"scope": "book", "provider": "nope"}).status_code == 400
    assert client.post(f"{BOOKS}/{book_id}/translation", json={"scope": "book", "provider": "local", "model": "x"}).status_code == 400
