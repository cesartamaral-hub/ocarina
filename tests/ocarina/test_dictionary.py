"""
Word definitions from Wiktionary: parsing, cache, offline behaviour. The network is faked.
"""

import json
import os
import shutil
import time

import pytest
import requests

from ocarina import dictionary
from tests.conftest import _get_test_language

DEFINE = "/ocarina/api/dictionary/define"

HUIS = {
    "nl": [
        {
            "partOfSpeech": "Noun",
            "language": "Dutch",
            "definitions": [
                {
                    "definition": 'a <a rel="mw:WikiLink" href="/wiki/house" title="house">house</a>, <i>home</i> &amp; shelter',
                    "parsedExamples": [{"example": "Ik woon in een <b>huis</b>."}],
                },
                {"definition": "  ", "examples": []},
            ],
        },
        {"partOfSpeech": "Verb", "language": "Dutch", "definitions": [{"definition": "<span>first-person singular of <i>huizen</i></span>"}]},
    ],
    "de": [{"partOfSpeech": "Noun", "language": "German", "definitions": [{"definition": "not this one"}]}],
}


class Reply:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


@pytest.fixture(autouse=True)
def net(app, monkeypatch):
    "A fake Wiktionary that records which words were asked, and a clean cache before and after each test."
    cache = os.path.join(app.env_config.datapath, "cache", "dictionary")
    shutil.rmtree(cache, ignore_errors=True)
    state = {"asked": [], "answers": {"huis": Reply(200, HUIS)}, "down": False}

    def fake_get(url, headers=None, timeout=None):  # pylint: disable=unused-argument
        word = requests.utils.unquote(url.rsplit("/", 1)[1])
        state["asked"].append(word)
        if state["down"]:
            raise requests.exceptions.ConnectionError("offline")
        return state["answers"].get(word, Reply(404, {"type": "not_found"}))

    monkeypatch.setattr(dictionary.requests, "get", fake_get)
    yield state
    shutil.rmtree(cache, ignore_errors=True)


def _language(app, name="Dutch"):
    with app.app_context():
        return _get_test_language(name).id


def test_parse_keeps_one_language_and_plain_text():
    "Only the language's entries are kept; HTML becomes text; empty definitions and other languages are dropped."
    entries = dictionary.parse(HUIS, "Dutch")
    assert [e["partOfSpeech"] for e in entries] == ["Noun", "Verb"]
    assert entries[0]["definitions"] == [{"text": "a house, home & shelter", "examples": ["Ik woon in een huis."]}]
    assert entries[1]["definitions"][0]["text"] == "first-person singular of huizen"
    assert dictionary.parse(HUIS, "German")[0]["definitions"][0]["text"] == "not this one"
    assert dictionary.parse(HUIS, "French") == []


def test_define_api_returns_definitions_and_a_link(app, client):
    "The endpoint gives the definitions, the matched word and a link to the full entry."
    r = client.get(f"{DEFINE}?languageId={_language(app)}&text=huis")
    assert r.status_code == 200
    assert r.json["found"] is True and r.json["word"] == "huis" and r.json["cached"] is False
    assert r.json["entries"][0]["definitions"][0]["text"].startswith("a house")
    assert r.json["url"] == "https://en.wiktionary.org/wiki/huis#Dutch"
    assert "fetched" not in r.json


def test_a_second_lookup_comes_from_the_cache(app, client, net):
    "The network is asked once; the second answer is cached."
    url = f"{DEFINE}?languageId={_language(app)}&text=huis"
    client.get(url)
    again = client.get(url).json
    assert net["asked"] == ["huis"] and again["cached"] is True and again["stale"] is False


def test_lower_case_is_tried_when_the_exact_spelling_is_missing(app, client, net):
    "A capitalised word at the start of a sentence still finds its entry."
    r = client.get(f"{DEFINE}?languageId={_language(app)}&text=Huis").json
    assert net["asked"] == ["Huis", "huis"] and r["found"] is True and r["word"] == "huis"


def test_unknown_words_are_remembered_for_a_while(app, client, net):
    "A word without an entry is not found, and is not asked again right away."
    url = f"{DEFINE}?languageId={_language(app)}&text=bestaatniet"
    first = client.get(url).json
    assert first["found"] is False and first["entries"] == []
    client.get(url)
    assert net["asked"].count("bestaatniet") == 1


def test_offline_uses_old_cache_or_says_so(app, client, net):
    "Without a connection an expired answer is still used; a word never looked up gives a clear error."
    language = _language(app)
    client.get(f"{DEFINE}?languageId={language}&text=huis")
    path = dictionary._cache_path(app.env_config.datapath, "Dutch", "huis")  # pylint: disable=protected-access
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["fetched"] = time.time() - dictionary.FOUND_TTL - 10
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    net["down"] = True
    stale = client.get(f"{DEFINE}?languageId={language}&text=huis").json
    assert stale["found"] is True and stale["stale"] is True and stale["cached"] is True
    fresh = client.get(f"{DEFINE}?languageId={language}&text=nooit")
    assert fresh.status_code == 502 and fresh.json["code"] == "offline" and "connection" in fresh.json["error"]


def test_server_errors_count_as_unreachable(app, client, net):
    "A Wiktionary failure (500) is reported like being offline, and is not cached as 'no entry'."
    net["answers"]["kapot"] = Reply(500, None)
    r = client.get(f"{DEFINE}?languageId={_language(app)}&text=kapot")
    assert r.status_code == 502 and r.json["code"] == "offline"
    net["answers"]["kapot"] = Reply(200, HUIS)
    assert client.get(f"{DEFINE}?languageId={_language(app)}&text=kapot").json["found"] is True


def test_cache_only_never_uses_the_network(app, client, net):
    "cacheOnly answers from the cache, or says it is not there."
    language = _language(app)
    miss = client.get(f"{DEFINE}?languageId={language}&text=huis&cacheOnly=true").json
    assert miss == {"found": False, "cacheMiss": True} and net["asked"] == []
    client.get(f"{DEFINE}?languageId={language}&text=huis")
    hit = client.get(f"{DEFINE}?languageId={language}&text=huis&cacheOnly=true").json
    assert hit["found"] is True and len(net["asked"]) == 1


def test_input_is_checked(app, client):
    "Empty or very long text, and an unknown language are refused."
    language = _language(app)
    assert client.get(f"{DEFINE}?languageId={language}&text=").status_code == 400
    assert client.get(f"{DEFINE}?languageId={language}&text={'x' * 101}").status_code == 400
    assert client.get(f"{DEFINE}?languageId=99999&text=huis").status_code == 404
    assert client.get(f"{DEFINE}?text=huis").status_code == 404


def test_lute_language_names_map_to_wiktionary_sections():
    "Languages named in their own language still find their section."
    assert dictionary.section_name("Polski") == "Polish" and dictionary.section_name("Nederlands") == "Dutch"
    assert dictionary.section_name("Spanish") == "Spanish"


HUIZEN = {
    "nl": [
        {
            "partOfSpeech": "Noun",
            "language": "Dutch",
            "definitions": [
                {
                    "definition": '<span class="form-of-definition use-with-mention"><span class="form-of-definition-non-gloss">plural of</span> '
                    '<span class="form-of-definition-link"><i class="Latn mention" lang="nl"><a rel="mw:WikiLink" href="/wiki/huis#Dutch" title="huis">huis</a></i></span></span>'
                }
            ],
        }
    ]
}


def test_an_inflected_form_also_shows_its_base_form(app, client, net):
    "huizen says 'plural of huis'; the lookup follows the link and adds what huis means."
    net["answers"]["huizen"] = Reply(200, HUIZEN)
    entries = dictionary.parse(HUIZEN, "Dutch")
    assert entries[0]["definitions"][0]["lemma"] == "huis"
    url = f"{DEFINE}?languageId={_language(app)}&text=huizen"
    r = client.get(url).json
    assert r["found"] is True and r["lemmas"][0]["word"] == "huis"
    assert r["lemmas"][0]["entries"][0]["definitions"][0]["text"].startswith("a house")
    assert net["asked"] == ["huizen", "huis"]
    client.get(url)
    assert net["asked"] == ["huizen", "huis"]  # both parts come from the cache the second time


def test_a_missing_base_form_does_not_break_the_lookup(app, client, net):
    "If the base form can't be found, the inflected word's own entry is still returned."
    net["answers"]["huizen"] = Reply(200, HUIZEN)
    del net["answers"]["huis"]  # the base form is not in the fake Wiktionary: 404
    r = client.get(f"{DEFINE}?languageId={_language(app)}&text=huizen").json
    assert r["found"] is True and r["lemmas"] == []


def test_an_old_cache_entry_without_base_forms_is_refreshed(app, client, net):
    "Entries saved before base forms existed are fetched again, and still serve as the offline fallback."
    language = _language(app)
    path = dictionary._cache_path(app.env_config.datapath, "Dutch", "huis")  # pylint: disable=protected-access
    dictionary._write_cache(path, {"found": True, "word": "huis", "entries": [], "url": "u", "fetched": time.time()})  # pylint: disable=protected-access
    net["down"] = True
    assert client.get(f"{DEFINE}?languageId={language}&text=huis").json["stale"] is True
    net["down"] = False
    fresh = client.get(f"{DEFINE}?languageId={language}&text=huis").json
    assert fresh["stale"] is False and "lemmas" in fresh and net["asked"].count("huis") == 2


def test_nested_sub_senses_do_not_run_into_the_main_gloss():
    "A definition with a nested list keeps only its own text."
    payload = {"nl": [{"partOfSpeech": "Noun", "language": "Dutch", "definitions": [{"definition": "a school<ol><li>an institution"}]}]}
    assert dictionary.parse(payload, "Dutch")[0]["definitions"][0]["text"] == "a school"
