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
