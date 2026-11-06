"""
Language settings: list, read, create, change, delete.
"""

from tests.conftest import _get_test_language
from tests.ocarina.helpers import make_dutch_book

URL = "/ocarina/api/languages"

SETTINGS = {
    "name": "Testtaal",
    "parserType": "spacedel",
    "showRomanization": False,
    "rightToLeft": False,
    "characterSubstitutions": "´='",
    "regexpSplitSentences": ".!?",
    "exceptionsSplitSentences": "Mr.",
    "wordCharacters": "a-zA-Z",
    "dictionaries": [
        {"useFor": "terms", "dictType": "embeddedhtml", "url": "https://example.com/?q=[LUTE]", "active": True},
        {"useFor": "sentences", "dictType": "popuphtml", "url": "https://translate.example/?q=[LUTE]", "active": True},
    ],
}


def _with(**changes):
    return {**SETTINGS, **changes}


def test_list_has_counts_and_get_has_all_settings(app, client):
    "The list shows how much each language holds; one language shows all its settings."
    with app.app_context():
        book = make_dutch_book("Telling")
        dutch_id = book.language.id
    row = next(r for r in client.get(URL).json if r["id"] == dutch_id)
    assert row["name"] == "Dutch" and row["books"] >= 1
    one = client.get(f"{URL}/{dutch_id}").json
    assert one["parserType"] == "spacedel" and one["dictionaries"]
    assert {"useFor", "dictType", "url", "active"} <= set(one["dictionaries"][0])
    assert client.get(f"{URL}/99999").status_code == 404


def test_create_then_update_keeps_dictionary_order(client):
    "A new language is saved with its dictionaries in the order sent; an update replaces them."
    created = client.post(URL, json=SETTINGS)
    assert created.status_code == 201
    language_id = created.json["id"]
    assert [d["url"] for d in created.json["dictionaries"]] == [d["url"] for d in SETTINGS["dictionaries"]]
    flipped = list(reversed(SETTINGS["dictionaries"])) + [
        {"useFor": "terms", "dictType": "popuphtml", "url": "https://other.example/[LUTE]", "active": False}
    ]
    updated = client.put(f"{URL}/{language_id}", json=_with(name="Nieuwe naam", dictionaries=flipped))
    assert updated.status_code == 200 and updated.json["name"] == "Nieuwe naam"
    assert [d["useFor"] for d in updated.json["dictionaries"]] == ["sentences", "terms", "terms"]
    assert updated.json["dictionaries"][2]["active"] is False


def test_validation_messages(client):
    "Bad settings are a 400 that says what to fix; a duplicate name is a 409."
    assert "name is required" in client.post(URL, json=_with(name=" ")).json["error"]
    assert "parsed" in client.post(URL, json=_with(parserType="nope")).json["error"]
    only_terms = SETTINGS["dictionaries"][:1]
    assert "sentences" in client.post(URL, json=_with(dictionaries=only_terms)).json["error"]
    inactive = [{**only_terms[0], "active": False}, SETTINGS["dictionaries"][1]]
    assert "terms" in client.post(URL, json=_with(dictionaries=inactive)).json["error"]
    bad_url = [{**SETTINGS["dictionaries"][0], "url": " "}, SETTINGS["dictionaries"][1]]
    assert "web address" in client.post(URL, json=_with(dictionaries=bad_url)).json["error"]
    bad_type = [{**SETTINGS["dictionaries"][0], "dictType": "frame"}, SETTINGS["dictionaries"][1]]
    assert client.post(URL, json=_with(dictionaries=bad_type)).status_code == 400
    assert client.post(URL, json=SETTINGS).status_code == 201
    assert client.post(URL, json=SETTINGS).status_code == 409


def test_template_blank_and_predefined(app_context, client):
    "A blank template has defaults; a predefined language comes with its own settings."
    blank = client.get(f"{URL}/template").json
    assert blank["language"]["id"] is None and blank["language"]["parserType"] == "spacedel"
    assert "Dutch" in blank["predefined"] or "Dutch" in [l["name"] for l in client.get(URL).json]
    name = blank["predefined"][0]
    assert client.get(f"{URL}/template?name={name}").json["language"]["name"] == name
    assert client.get(f"{URL}/template?name=Klingon").status_code == 404
    assert any(p["type"] == "spacedel" for p in client.get(f"{URL}/parsers").json)


def test_delete_needs_force_when_the_language_has_books(app, client):
    "An empty language is deleted at once; one with books only with force, taking the books along."
    empty_id = client.post(URL, json=SETTINGS).json["id"]
    assert client.delete(f"{URL}/{empty_id}").json["deleted"] == empty_id
    with app.app_context():
        dutch_id = _get_test_language("Dutch").id
        make_dutch_book("Weg")
    refused = client.delete(f"{URL}/{dutch_id}")
    assert refused.status_code == 409 and refused.json["books"] >= 1
    forced = client.delete(f"{URL}/{dutch_id}?force=true")
    assert forced.status_code == 200
    assert client.get(f"{URL}/{dutch_id}").status_code == 404
    assert client.delete(f"{URL}/{dutch_id}").status_code == 404


def test_first_run_adds_predefined_languages_with_or_without_stories(client):
    "Picking languages adds them (and optionally Lute's sample stories); names that don't exist or are taken are skipped."
    names = client.get(f"{URL}/template").json["predefined"]
    first, second = names[0], names[1]
    plain = client.post(f"{URL}/predefined", json={"names": [first, "Klingon"]})
    assert plain.status_code == 201 and [a["name"] for a in plain.json["added"]] == [first]
    assert plain.json["skipped"] == ["Klingon"]
    row = next(r for r in client.get(URL).json if r["name"] == first)
    assert row["books"] == 0
    with_books = client.post(f"{URL}/predefined", json={"names": [second, first], "books": True})
    assert [a["name"] for a in with_books.json["added"]] == [second] and with_books.json["skipped"] == [first]
    assert next(r for r in client.get(URL).json if r["name"] == second)["books"] >= 1
    assert first not in client.get(f"{URL}/template").json["predefined"]
    assert client.post(f"{URL}/predefined", json={"names": []}).status_code == 400
    assert client.post(f"{URL}/predefined", json={"names": ["Klingon"]}).status_code == 400


def _names(client):
    return client.get("/ocarina/api/languages/template").json["predefined"]


def test_portuguese_is_offered_as_european_and_brazilian(client):
    names = _names(client)
    assert "European Portuguese" in names and "Brazilian Portuguese" in names and "Portuguese" not in names


def test_the_template_says_which_languages_have_a_sample_story(client):
    data = client.get("/ocarina/api/languages/template").json
    assert {"Dutch", "French", "European Portuguese", "Brazilian Portuguese"} <= set(data["withStory"])
    assert set(data["withStory"]) <= set(data["predefined"])


def test_a_portuguese_language_is_added_with_its_own_story(app, client):
    from lute.db import db  # pylint: disable=import-outside-toplevel
    from sqlalchemy import text as sql  # pylint: disable=import-outside-toplevel

    r = client.post("/ocarina/api/languages/predefined", json={"names": ["European Portuguese", "Brazilian Portuguese"], "books": True})
    assert r.status_code in (200, 201) and len(r.json["added"]) == 2
    with app.app_context():
        titles = {t for (t,) in db.session.execute(sql("select BkTitle from books"))}
    assert {"A Padaria da Dona Rosa", "A Maldição"} <= titles
    assert "Portuguese" not in _names(client)


def test_plain_portuguese_cannot_be_added_but_an_old_one_can_be_renamed(client):
    assert client.post("/ocarina/api/languages/predefined", json={"names": ["Portuguese"]}).json["skipped"] == ["Portuguese"]
    assert client.get("/ocarina/api/languages/legacy-portuguese").json is None
    assert client.post(URL, json={**SETTINGS, "name": "Portuguese"}).status_code in (200, 201)  # a library from before the two kinds
    found = client.get("/ocarina/api/languages/legacy-portuguese").json
    assert found["name"] == "Portuguese"
    assert client.post(f"/ocarina/api/languages/{found['id']}/portuguese", json={"kind": "x"}).status_code == 400
    r = client.post(f"/ocarina/api/languages/{found['id']}/portuguese", json={"kind": "brazilian"})
    assert r.json["name"] == "Brazilian Portuguese" and client.get("/ocarina/api/languages/legacy-portuguese").json is None
    assert client.post(f"/ocarina/api/languages/{found['id']}/portuguese", json={"kind": "brazilian"}).status_code == 404  # no longer the plain one
