"""
Numbers written as digits are said as words: years, percents and units, ordinals, decimals, thousands, and what is left alone.
"""

import pytest

from ocarina import live_speech, numbers, pronounce
from tests.conftest import _get_test_language


@pytest.mark.parametrize(
    "text, code, expected",
    [
        ("In 1995 woonde ik daar.", "nl", "In negentien honderd vijfennegentig woonde ik daar."),
        ("Het is 3% van 2,5 miljoen.", "nl", "Het is drie procent van twee komma vijf miljoen."),
        ("De 3e keer, 21 jaar.", "nl", "De derde keer, eenentwintig jaar."),
        ("Het kost €5 of 1 euro.", "nl", "Het kost vijf euro of één euro."),
        ("Kost 2,50 euro", "nl", "Kost twee komma vijf nul euro"),
        ("Le 1er mai, 1 000 000 de gens, 25°C.", "fr", "Le premier mai, un million de gens, vingt-cinq degrés celsius."),
        ("Było 3 psy i 50%.", "pl", "Było trzy psy i pięćdziesiąt procent."),
    ],
)
def test_digits_are_said_as_words(text, code, expected):
    assert numbers.spoken(text, code) == expected


def test_ranges_of_years_are_said_but_phone_numbers_and_times_are_left_to_the_voice():
    assert numbers.spoken("van 1990-1995", "nl") == "van negentien honderd negentig-negentien honderd vijfennegentig"
    assert numbers.spoken("tel 06-12345678 om 12:30", "nl") == "tel 06-12345678 om 12:30"


def test_text_without_digits_or_in_an_unknown_language_is_unchanged():
    assert numbers.spoken("Geen cijfers hier.", "nl") == "Geen cijfers hier."
    assert numbers.spoken("In 1995", "xx") == "In 1995"
    assert numbers.spoken("", "nl") == ""


def test_a_year_is_a_year_only_without_a_unit():
    assert numbers.describe("1995", "nl") == {"words": "negentien honderd vijfennegentig", "kind": "year"}
    assert numbers.describe("1995%", "nl")["kind"] == "number"
    assert numbers.describe("3e", "nl") == {"words": "derde", "kind": "ordinal"}
    assert numbers.describe("hallo", "nl") is None and numbers.describe("3 vrienden", "nl") is None


def test_the_panel_asks_for_the_words_of_a_number(app, client):
    with app.app_context():
        language_id = _get_test_language("Dutch").id
    r = client.get(f"/ocarina/api/numbers/spoken?languageId={language_id}&text=3%25")
    assert r.json == {"words": "drie procent", "kind": "number"}
    assert client.get(f"/ocarina/api/numbers/spoken?languageId={language_id}&text=huis").json["words"] is None
    assert client.get("/ocarina/api/numbers/spoken?languageId=9999&text=3").status_code == 404


def test_reading_aloud_and_the_word_pronounce_say_the_words(app, client, monkeypatch):
    said = []
    monkeypatch.setattr(pronounce, "mac_voice", lambda code, chosen=None, locale=None: "Xander")
    monkeypatch.setattr(live_speech, "speak", lambda text, voice, wpm=None: said.append(text) or True)
    with app.app_context():
        language_id = _get_test_language("Dutch").id
    client.post("/ocarina/api/speak", json={"text": "Ik ben 21 jaar.", "languageId": language_id})
    assert said == ["Ik ben eenentwintig jaar."]
