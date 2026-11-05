"""
Offline dictionaries: the pack format, packs made from WikDict, Wiktextract and StarDict data, the order and switches, and what a lookup returns.
"""

import gzip
import hashlib
import io
import json
import os
import sqlite3
import struct

import pytest

from ocarina import dictionary, prefs
from ocarina.dictionaries import install, pack, registry, stardict, wikdict, wiktextract
from tests.conftest import _get_test_language
from tests.ocarina.helpers import wait_for_job

DICT = "/ocarina/api/dictionaries"


@pytest.fixture(autouse=True)
def folders(tmp_path, monkeypatch, app):
    "Built-in packs and the user's live in temporary folders; the saved choice is reset."
    monkeypatch.setattr(registry, "BUILTIN_DIR", str(tmp_path / "builtin"))
    monkeypatch.setattr(registry, "user_dir", lambda datapath: str(tmp_path / "user"))
    path = prefs.path_for(app.env_config.datapath)
    prefs.update(path, {"dictionaries.order": [], "dictionaries.off": []})
    registry._open.clear()  # pylint: disable=protected-access
    yield tmp_path
    registry._open.clear()  # pylint: disable=protected-access
    prefs.update(path, {"dictionaries.order": [], "dictionaries.off": []})


def make_pack(folder, pack_id, name, code, entries, kind="builtin", forms=()):
    db = pack.create(os.path.join(folder, f"{pack_id}.sqlite"), {"id": pack_id, "name": name, "language": code, "meaning": "en", "license": "CC BY-SA", "kind": kind})
    for word, pos, senses in entries:
        db.execute("insert into entry (word, word_lc, pos, importance, senses) values (?, ?, ?, 1, ?)", (word, pack.fold(word), pos, json.dumps([{"text": s} for s in senses])))
    db.executemany("insert into form values (?, ?)", forms)
    pack.finish(db)


def test_a_pack_gives_entries_by_word_ignoring_case_and_zero_width_spaces(folders):
    make_pack(folders / "builtin", "a", "A", "nl", [("Huis", "noun", ["house", "home"]), ("huis", "noun", ["building"])])
    p = pack.Pack(str(folders / "builtin" / "a.sqlite"))
    got = p.entries("​HUIS")
    assert len(got) == 2 and got[0]["partOfSpeech"] == "Noun"
    assert p.info()["entries"] == 2 and p.info()["language"] == "nl"
    assert p.entries("onbekend") == []


def test_inflected_forms_lead_to_their_base_form(folders):
    make_pack(folders / "builtin", "a", "A", "nl", [("hebben", "verb", ["to have"])], forms=[("heeft", "hebben")])
    found = dictionary.define("x", "Dutch", "heeft")
    assert found["entries"] == [] and found["lemmas"][0]["word"] == "hebben"
    assert found["lemmas"][0]["entries"][0]["definitions"][0]["text"] == "to have"


def test_define_uses_the_packs_in_the_users_order_and_lists_the_others(app, folders):
    make_pack(folders / "builtin", "first", "First", "nl", [("huis", "noun", ["house"])])
    make_pack(folders / "user", "second", "Second", "nl", [("huis", "noun", ["home"])], kind="stardict")
    make_pack(folders / "builtin", "polish", "Polish", "pl", [("huis", "noun", ["wrong language"])])
    datapath = app.env_config.datapath
    # a pack of the user's comes before the built-in ones until the order is chosen
    got = dictionary.define(datapath, "Dutch", "huis")
    assert got["source"]["id"] == "second" and [o["source"]["id"] for o in got["others"]] == ["first"]
    registry.save_choice(datapath, order=["first", "second"])
    got = dictionary.define(datapath, "Dutch", "huis")
    assert got["source"]["id"] == "first" and got["entries"][0]["definitions"][0]["text"] == "house"
    registry.save_choice(datapath, off=["first"])
    assert dictionary.define(datapath, "Dutch", "huis")["source"]["id"] == "second"


def test_without_a_pack_the_word_goes_to_wiktionary(app, monkeypatch):
    monkeypatch.setattr(dictionary, "define_online", lambda *a, **k: {"found": True, "word": "x", "entries": [], "lemmas": [], "url": "u", "cached": False, "stale": False})
    got = dictionary.define(app.env_config.datapath, "Dutch", "x")
    assert got["source"]["id"] == "wiktionary" and got["others"] == []


def test_wiktionary_comes_as_a_second_opinion_when_asked(app, folders, monkeypatch):
    make_pack(folders / "builtin", "a", "A", "nl", [("huis", "noun", ["house"])])
    monkeypatch.setattr(dictionary, "define_online", lambda *a, **k: {"found": True, "word": "huis", "entries": [], "lemmas": [], "url": "u", "cached": False, "stale": False})
    assert dictionary.define(app.env_config.datapath, "Dutch", "huis")["others"] == []
    assert [o["source"]["id"] for o in dictionary.define(app.env_config.datapath, "Dutch", "huis", online=True)["others"]] == ["wiktionary"]
    assert dictionary.define(app.env_config.datapath, "Dutch", "huis", cache_only=True, online=True)["others"] == []  # cache only never goes online


def test_a_wikdict_pair_becomes_a_pack(tmp_path):
    src = sqlite3.connect(tmp_path / "nl-en.sqlite3")
    src.execute("create table translation(lexentry, sense_num, sense, written_rep, trans_list, score, is_good, importance)")
    src.executemany(
        "insert into translation values (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("nld/hebben__verb__1", 1, "", "hebben", "have | stand", 100, 1, 2.0),
            ("nld/hebben__verb__1", 2, "bezitten", "hebben", "own", 90, 1, 2.0),
            ("nld/acht__num__1", 1, "1. het getal 8", "acht", "eight", 200, 1, 1.0),
            ("nld/leeg__adjc__1", 1, "", "leeg", "", 10, 1, 0.1),
        ],
    )
    src.commit()
    out = str(tmp_path / "out.sqlite")
    assert wikdict.convert(str(tmp_path / "nl-en.sqlite3"), out, "nl") == 2
    p = pack.Pack(out)
    assert p.id == "wikdict-nl-en" and p.meta["kind"] == "builtin"
    verb = p.entries("hebben")[0]
    assert verb["partOfSpeech"] == "Verb" and [d["text"] for d in verb["definitions"]] == ["have; stand", "own (bezitten)"]
    assert p.entries("acht")[0]["partOfSpeech"] == "Numeral"
    assert p.entries("acht")[0]["definitions"][0]["text"] == "eight (het getal 8)"
    assert p.entries("leeg") == []  # no translations: no entry


WIKTEXTRACT = [
    {"word": "huis", "pos": "noun", "lang_code": "nl", "senses": [{"glosses": ["house", "building"], "examples": [{"text": "Dit is mijn huis.", "english": "This is my house."}]}, {"glosses": ["home"], "tags": ["informal"]}],
     "forms": [{"form": "huizen", "tags": ["plural"]}, {"form": "no-table-tags", "tags": ["table-tags"]}, {"form": "huis", "tags": ["singular"]}]},
    {"word": "huizen", "pos": "noun", "lang_code": "nl", "senses": [{"glosses": ["plural of huis"], "tags": ["form-of"], "form_of": [{"word": "huis"}]}]},
    {"word": "house", "pos": "noun", "lang_code": "en", "senses": [{"glosses": ["not dutch"]}]},
    {"word": "leeg", "pos": "adj", "lang_code": "nl", "senses": [{"glosses": []}]},
]


def test_wiktextract_lines_become_a_pack_with_forms(tmp_path):
    out = str(tmp_path / "w.sqlite")
    seen = []
    n = wiktextract.convert_lines([json.dumps(x).encode() for x in WIKTEXTRACT] + [b"not json"], out, "nl", {"id": "wiktionary-nl-en", "name": "Wiktionary"}, seen.append)
    assert n == 2 and len(seen) == 5
    p = pack.Pack(out)
    huis = p.entries("huis")[0]
    assert huis["definitions"][0] == {"text": "building (house)", "examples": ["Dit is mijn huis. — This is my house."]}
    assert huis["definitions"][1]["text"] == "(informal) home"
    assert p.lemmas("huizen") == ["huis"]  # from the form list and from the form-of sense, once
    assert p.entries("house") == []  # another language


def stardict_files(folder, words, name="Test dict"):
    articles, index, offset = b"", b"", 0
    for word, text in words:
        data = text.encode()
        index += word.encode() + b"\0" + struct.pack(">II", offset, len(data))
        articles += data
        offset += len(data)
    (folder / "t.ifo").write_text(f"StarDict's dict ifo file\nversion=2.4.2\nwordcount={len(words)}\nidxfilesize={len(index)}\nbookname={name}\nsametypesequence=m\n")
    (folder / "t.idx").write_bytes(index)
    with gzip.open(folder / "t.dict.dz", "wb") as f:
        f.write(articles)


def test_a_stardict_dictionary_becomes_a_pack(tmp_path):
    folder = tmp_path / "sd"
    folder.mkdir()
    stardict_files(folder, [("fiets", "bicycle\nbike"), ("Kat", "<b>cat</b><br>a small animal")])
    out = str(tmp_path / "s.sqlite")
    assert stardict.convert(str(folder), out, "nl") == 2
    p = pack.Pack(out)
    assert p.id == "stardict-nl-test-dict" and p.name == "Test dict" and p.meta["kind"] == "stardict"
    assert [d["text"] for d in p.entries("fiets")[0]["definitions"]] == ["bicycle", "bike"]
    assert [d["text"] for d in p.entries("kat")[0]["definitions"]] == ["cat", "a small animal"]


def test_stardict_files_that_are_not_a_dictionary_are_refused(tmp_path):
    with pytest.raises(stardict.StarDictError, match="no .ifo"):
        stardict.convert(str(tmp_path), str(tmp_path / "x.sqlite"), "nl")
    (tmp_path / "a.ifo").write_text("not a stardict file\n")
    with pytest.raises(stardict.StarDictError, match="not a StarDict"):
        stardict.convert(str(tmp_path), str(tmp_path / "x.sqlite"), "nl")


def test_the_page_lists_packs_and_remembers_the_choice(app, client, folders):
    with app.app_context():
        _get_test_language("Dutch")
    make_pack(folders / "builtin", "built", "Built in", "nl", [("a", "", ["x"])])
    make_pack(folders / "user", "mine", "Mine", "nl", [("a", "", ["y"])], kind="stardict")
    listed = client.get(DICT).json
    assert [p["id"] for p in listed["packs"]] == ["mine", "built"]
    assert {p["id"]: p["removable"] for p in listed["packs"]} == {"mine": True, "built": False}
    # for the languages of the library only: Dutch has WikDict, the full Wiktionary and the Dutch edition
    assert [a["id"] for a in listed["available"]] == ["wikdict-nl-en", "wiktionary-nl-en", "wiktionary-nl-nl"]
    assert {a["languageName"] for a in listed["available"]} == {"Dutch"}
    assert client.put(f"{DICT}/choice", json={"order": ["built", "mine"], "off": ["mine"]}).status_code == 200
    again = client.get(DICT).json["packs"]
    assert [(p["id"], p["on"]) for p in again] == [("built", True), ("mine", False)]
    assert client.put(f"{DICT}/choice", json={"order": "x"}).status_code == 400


def test_only_your_own_packs_can_be_deleted(client, folders):
    make_pack(folders / "builtin", "built", "Built in", "nl", [("a", "", ["x"])])
    make_pack(folders / "user", "mine", "Mine", "nl", [("a", "", ["y"])], kind="stardict")
    assert client.delete(f"{DICT}/built").status_code == 404
    assert client.delete(f"{DICT}/mine").json == {"deleted": "mine"}
    assert [p["id"] for p in client.get(DICT).json["packs"]] == ["built"]


def test_importing_stardict_files_as_a_job(app, client, folders):
    with app.app_context():
        _get_test_language("Dutch")
    src = folders / "sd"
    src.mkdir()
    stardict_files(src, [("fiets", "bicycle")])
    data = {"language": "nl", "name": "Mijn woordenboek", "meaning": "nl", "files": [(io.BytesIO((src / n).read_bytes()), n) for n in ("t.ifo", "t.idx", "t.dict.dz")]}
    r = client.post(f"{DICT}/import", data=data, content_type="multipart/form-data")
    assert r.status_code == 202
    assert wait_for_job(client, r.json["id"])["state"] == "done"
    mine = next(p for p in client.get(DICT).json["packs"] if p["kind"] == "stardict")
    assert mine["name"] == "Mijn woordenboek" and mine["language"] == "nl" and mine["meaning"] == "nl" and mine["entries"] == 1
    assert dictionary.define(app.env_config.datapath, "Dutch", "fiets")["source"]["name"] == "Mijn woordenboek"


def test_importing_needs_files_a_language_and_a_real_dictionary(app, client, folders):
    with app.app_context():
        _get_test_language("Dutch")
    assert client.post(f"{DICT}/import", data={"language": "xx"}, content_type="multipart/form-data").status_code == 400
    assert client.post(f"{DICT}/import", data={"language": "nl"}, content_type="multipart/form-data").status_code == 400
    bad = client.post(f"{DICT}/import", data={"language": "nl", "files": [(io.BytesIO(b"junk"), "x.ifo")]}, content_type="multipart/form-data")
    assert wait_for_job(client, bad.json["id"])["state"] == "error"


def test_downloading_a_wiktionary_pack_converts_it_as_it_arrives(app, client, folders, monkeypatch):
    with app.app_context():
        _get_test_language("Dutch")
    lines = [json.dumps(x).encode() for x in WIKTEXTRACT]
    monkeypatch.setattr(wiktextract, "stream", lambda url, check=None: (1000, iter(lines)))
    r = client.post(f"{DICT}/wiktionary-nl-en/download")
    assert r.status_code == 202
    assert wait_for_job(client, r.json["id"])["state"] == "done"
    mine = next(p for p in client.get(DICT).json["packs"] if p["id"] == "wiktionary-nl-en")
    assert mine["kind"] == "wiktionary" and mine["entries"] == 2 and mine["removable"]
    assert next(a for a in client.get(DICT).json["available"] if a["id"] == "wiktionary-nl-en")["installed"]
    assert dictionary.define(app.env_config.datapath, "Dutch", "huizen")["lemmas"][0]["word"] == "huis"
    assert client.post(f"{DICT}/nope/download").status_code == 404


def test_the_catalog_knows_each_language_of_the_app():
    from ocarina import translate

    everything = install.catalog()
    known = {p["language"] for p in everything}
    assert {"nl", "pl", "fr", "es", "de", "it", "pt", "ru", "ja"} <= known and "en" not in known
    assert len(known) > 30  # most of the languages the app has a code for
    only = install.catalog({"pl"})
    assert [p["id"] for p in only] == ["wikdict-pl-en", "wiktionary-pl-en", "wiktionary-pl-pl"]
    assert [p["meaning"] for p in only] == ["en", "en", "pl"] and all(p["download"] > 0 and p["bytes"] > 0 for p in only)
    # a language without a WikDict dictionary or an edition simply has fewer
    assert [p["id"] for p in install.catalog({"ko"})] == ["wiktionary-ko-en", "wiktionary-ko-ko"]
    assert [p["id"] for p in install.catalog({"hu"})] == ["wiktionary-hu-en"]
    assert install.catalog({"xx"}) == [] and install.find("wiktionary-nl-nl")["url"].endswith("nl-extract.jsonl")
    assert set(translate.CODES.values()) >= known - {"zh", "ms", "ku"}
    from ocarina.dictionaries import languages

    assert languages.bundled() == ["nl", "pl", "fr", "es", "de", "it", "pt"] and languages.name("de") == "German"


def test_an_edition_with_every_language_gives_only_the_wanted_one(tmp_path):
    "The Dutch Wiktionary holds words of all languages, defined in Dutch: only the Dutch ones are made into the pack."
    lines = [
        json.dumps({"word": "huis", "pos": "noun", "lang_code": "nl", "senses": [{"glosses": ["gebouw om in te wonen"]}]}).encode(),
        json.dumps({"word": "house", "pos": "noun", "lang_code": "en", "senses": [{"glosses": ["huis"]}]}).encode(),
    ]
    out = str(tmp_path / "w.sqlite")
    assert wiktextract.convert_lines(lines, out, "nl", {"id": "wiktionary-nl-nl", "name": "Wiktionary NL", "meaning": "nl"}) == 1
    p = pack.Pack(out)
    assert p.info()["meaning"] == "nl" and p.entries("huis")[0]["definitions"][0]["text"] == "gebouw om in te wonen" and p.entries("house") == []


def _gz_pack(tmp_path, entry_id="wiktionary-nl-en"):
    make_pack(tmp_path, entry_id, "Ready made", "nl", [("huis", "noun", ["house"])], kind="wiktionary")
    raw = (tmp_path / f"{entry_id}.sqlite").read_bytes()
    out = tmp_path / f"{entry_id}.sqlite.gz"
    out.write_bytes(gzip.compress(raw))
    return out, hashlib.sha256(out.read_bytes()).hexdigest()


class _Reply:
    def __init__(self, data):
        self.data, self.headers = data, {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, size):
        yield self.data


def test_a_ready_made_pack_is_fetched_and_checked(app, client, folders, monkeypatch):
    gz, digest = _gz_pack(folders)
    monkeypatch.setattr(install, "catalog", lambda *a: [{"id": "wiktionary-nl-en", "name": "Ready made", "language": "nl", "meaning": "en", "bytes": 10, "download": 5, "kaikki": "Dutch", "description": "", "prebuilt": "https://example.org/p.gz", "sha256": digest}])
    monkeypatch.setattr(install.requests, "get", lambda *a, **k: _Reply(gz.read_bytes()))
    monkeypatch.setattr(wiktextract, "stream", lambda *a, **k: pytest.fail("the data it is made from must not be read when the ready-made pack is there"))
    r = client.post(f"{DICT}/wiktionary-nl-en/download")
    assert wait_for_job(client, r.json["id"])["state"] == "done"
    assert dictionary.define(app.env_config.datapath, "Dutch", "huis")["source"]["name"] == "Ready made"


def test_when_the_ready_made_pack_cannot_be_had_it_is_made_from_the_data(app, client, folders, monkeypatch):
    import requests

    entry = {"id": "wiktionary-nl-en", "name": "Wiktionary NL", "language": "nl", "meaning": "en", "bytes": 10, "download": 5, "kaikki": "Dutch", "description": "", "prebuilt": "https://example.org/missing.gz", "sha256": "0" * 64}
    monkeypatch.setattr(install, "catalog", lambda *a: [entry])

    def gone(*a, **k):
        raise requests.exceptions.HTTPError("404")

    monkeypatch.setattr(install.requests, "get", gone)
    monkeypatch.setattr(wiktextract, "stream", lambda url, check=None: (100, iter([json.dumps(x).encode() for x in WIKTEXTRACT])))
    r = client.post(f"{DICT}/wiktionary-nl-en/download")
    assert wait_for_job(client, r.json["id"])["state"] == "done"
    assert next(p for p in client.get(DICT).json["packs"] if p["id"] == "wiktionary-nl-en")["entries"] == 2


def test_a_ready_made_pack_with_the_wrong_sum_is_not_used(app, client, folders, monkeypatch):
    gz, _ = _gz_pack(folders)
    entry = {"id": "wiktionary-nl-en", "name": "Wiktionary NL", "language": "nl", "meaning": "en", "bytes": 10, "download": 5, "kaikki": "Dutch", "description": "", "prebuilt": "https://example.org/p.gz", "sha256": "0" * 64}
    monkeypatch.setattr(install, "catalog", lambda *a: [entry])
    monkeypatch.setattr(install.requests, "get", lambda *a, **k: _Reply(gz.read_bytes()))
    monkeypatch.setattr(wiktextract, "stream", lambda url, check=None: (100, iter([json.dumps(x).encode() for x in WIKTEXTRACT])))
    r = client.post(f"{DICT}/wiktionary-nl-en/download")
    assert wait_for_job(client, r.json["id"])["state"] == "done"
    assert next(p for p in client.get(DICT).json["packs"] if p["id"] == "wiktionary-nl-en")["entries"] == 2  # made from the data instead


def test_a_downloaded_wikdict_pack_is_made_from_its_pair_file(app, client, folders, monkeypatch, tmp_path):
    with app.app_context():
        _get_test_language("Dutch")
    src = sqlite3.connect(tmp_path / "pair.sqlite3")
    src.execute("create table translation(lexentry, sense_num, sense, written_rep, trans_list, score, is_good, importance)")
    src.execute("insert into translation values ('nld/huis__noun__1', 1, '', 'huis', 'house | home', 100, 1, 1.0)")
    src.commit()
    src.close()
    pair = (tmp_path / "pair.sqlite3").read_bytes()
    monkeypatch.setattr(install.requests, "get", lambda *a, **k: _Reply(pair))
    r = client.post(f"{DICT}/wikdict-nl-en/download")
    assert wait_for_job(client, r.json["id"])["state"] == "done"
    got = next(p for p in client.get(DICT).json["packs"] if p["id"] == "wikdict-nl-en")
    assert got["kind"] == "wikdict" and got["removable"] and got["entries"] == 1


@pytest.mark.dictionary_setup
def test_a_new_language_gets_its_small_dictionary(app, client, folders, monkeypatch):
    started = []
    monkeypatch.setattr(install, "download", lambda entry, datapath, progress, check: started.append(entry["id"]))
    from ocarina.dictionaries import setup

    with app.app_context():
        job = setup.ensure_default(app.env_config.datapath, "Dutch")
    assert job is not None and wait_for_job(client, job["id"])["state"] == "done" and started == ["wikdict-nl-en"]
    with app.app_context():  # one that has a dictionary already, a language with none, an unknown language
        make_pack(folders / "user", "wikdict-pl-en", "x", "pl", [("a", "", ["b"])])
        assert setup.ensure_default(app.env_config.datapath, "Polish") is None
        assert setup.ensure_default(app.env_config.datapath, "Klingon") is None
        assert setup.ensure_default(app.env_config.datapath, "Korean") is None  # no WikDict for it: the page offers the others


def test_adding_a_language_asks_for_its_small_dictionary(client, monkeypatch):
    asked = []
    monkeypatch.setattr("ocarina.dictionaries.setup.ensure_default", lambda datapath, name: asked.append(name))
    r = client.post("/ocarina/api/languages/predefined", json={"names": ["Dutch"]})
    assert r.status_code == 201 and asked == ["Dutch"]
