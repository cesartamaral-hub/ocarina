"""
Reader JSON API.
"""

from lute.db import db
from lute.models.term import Term as DBTerm
from tests.conftest import _get_test_language
from tests.ocarina.helpers import make_dutch_book


def _words(page):
    return [i for para in page["paragraphs"] for s in para for i in s if i["isWord"]]


def test_page_has_paragraphs_sentences_and_unknown_terms(app, client):
    "Opening a page returns its text items; every word already has a term (status 0)."
    with app.app_context():
        book_id = make_dutch_book().id
    page = client.get(f"/ocarina/api/books/{book_id}/pages/1").json
    assert page["pageCount"] == 2 and page["language"]["name"] == "Dutch"
    # The blank line between the two paragraphs is a paragraph of its own.
    with_words = [p for p in page["paragraphs"] if any(i["isWord"] for s in p for i in s)]
    assert len(with_words) == 2
    words = _words(page)
    assert [w["text"] for w in words][:3] == ["Hallo", "Mijn", "naam"]
    assert all(w["termId"] and w["status"] == 0 for w in words)
    assert client.get(f"/ocarina/api/books/{book_id}/pages/9").status_code == 404


def test_save_term_updates_status_and_translation(app, client):
    "A word can be given a translation and status, and the page shows the new status."
    with app.app_context():
        book_id = make_dutch_book("Term").id
    words = _words(client.get(f"/ocarina/api/books/{book_id}/pages/1").json)
    carla = next(w for w in words if w["text"] == "Carla")

    term = client.get(f"/ocarina/api/terms/{carla['termId']}").json
    assert term["status"] == 0 and term["translation"] == ""

    r = client.post(
        "/ocarina/api/terms",
        json={"id": term["id"], "status": 2, "translation": "Carla (name)", "tags": ["name"]},
    )
    assert r.status_code == 200
    assert r.json["status"] == 2 and r.json["translation"] == "Carla (name)"
    assert r.json["tags"] == ["name"]

    again = _words(client.get(f"/ocarina/api/books/{book_id}/pages/1").json)
    assert next(w for w in again if w["text"] == "Carla")["status"] == 2


def test_set_status_and_bad_status(app, client):
    "PATCH changes only the status; invalid statuses are rejected."
    with app.app_context():
        book_id = make_dutch_book("Status").id
    carla = next(
        w
        for w in _words(client.get(f"/ocarina/api/books/{book_id}/pages/1").json)
        if w["text"] == "Carla"
    )
    url = f"/ocarina/api/terms/{carla['termId']}/status"
    assert client.patch(url, json={"status": 99}).json["status"] == 99
    assert client.patch(url, json={"status": 7}).status_code == 400
    assert client.get(f"/ocarina/api/terms/{carla['termId']}").json["status"] == 99


def test_finish_page_marks_rest_as_known(app, client):
    "Finishing a page with restAsKnown turns unknown words well-known."
    with app.app_context():
        book_id = make_dutch_book("Finish").id
    first = _words(client.get(f"/ocarina/api/books/{book_id}/pages/1").json)
    client.patch(f"/ocarina/api/terms/{first[0]['termId']}/status", json={"status": 1})
    r = client.post(f"/ocarina/api/books/{book_id}/pages/1/finish", json={"restAsKnown": True})
    assert r.status_code == 200
    statuses = {w["text"]: w["status"] for w in _words(client.get(f"/ocarina/api/books/{book_id}/pages/1").json)}
    assert statuses["Hallo"] == 1 and statuses["Carla"] == 99


def test_open_external_only_allows_web_links(client):
    "File and other schemes are refused."
    assert client.post("/ocarina/api/open-external", json={"url": "file:///etc/passwd"}).status_code == 400
    assert client.post("/ocarina/api/open-external", json={"url": "javascript:alert(1)"}).status_code == 400


def _carla_id(client, book_id):
    words = _words(client.get(f"/ocarina/api/books/{book_id}/pages/1").json)
    return next(w for w in words if w["text"] == "Carla")["termId"]


def test_lookup_new_multiword_then_save_and_components(app, client):
    "An unknown phrase looks up as unsaved; saving it makes a term that lists its known words."
    with app.app_context():
        book_id = make_dutch_book("Multi").id
    carla = _carla_id(client, book_id)
    client.post("/ocarina/api/terms", json={"id": carla, "status": 3, "translation": "name"})
    lang = client.get(f"/ocarina/api/books/{book_id}/pages/1").json["language"]["id"]

    new = client.get("/ocarina/api/terms/lookup", query_string={"languageId": lang, "text": "naam is Carla"}).json
    assert new["id"] is None and new["components"] == []

    saved = client.post(
        "/ocarina/api/terms",
        json={"languageId": lang, "text": "naam is Carla", "status": 1, "translation": "name is Carla"},
    ).json
    assert saved["id"] and saved["translation"] == "name is Carla"
    assert [c["text"] for c in saved["components"]] == ["Carla"]
    # The page now shows the phrase as one text item.
    items = [i for p in client.get(f"/ocarina/api/books/{book_id}/pages/1").json["paragraphs"] for s in p for i in s]
    assert any(i["text"] == "naam is Carla" for i in items)


def test_popup_references_and_bulk_status(app, client):
    "Hover data, references and bulk status work on saved terms."
    with app.app_context():
        book_id = make_dutch_book("Popup").id
    carla = _carla_id(client, book_id)
    client.post("/ocarina/api/terms", json={"id": carla, "status": 2, "translation": "name", "parents": ["Carla-parent"]})
    popup = client.get(f"/ocarina/api/terms/{carla}/popup").json
    assert popup["translation"] == "name" and popup["status"] == 2
    assert client.get("/ocarina/api/terms/999999/popup").status_code == 404

    client.post(f"/ocarina/api/books/{book_id}/pages/1/finish", json={})
    refs = client.get(f"/ocarina/api/terms/{carla}/references").json
    assert refs["term"] and any(p["bold"] for p in refs["term"][0]["sentence"])

    ids = [w["termId"] for w in _words(client.get(f"/ocarina/api/books/{book_id}/pages/1").json)][:3]
    r = client.post("/ocarina/api/terms/bulk-status", json={"termIds": ids, "status": 4})
    assert r.json["count"] == 3
    assert {client.get(f"/ocarina/api/terms/{i}").json["status"] for i in ids} == {4}
    assert client.post("/ocarina/api/terms/bulk-status", json={"termIds": ids, "status": 7}).status_code == 400


def test_page_text_edit(app, client):
    "Page text can be read and replaced."
    with app.app_context():
        book_id = make_dutch_book("Edit").id
    url = f"/ocarina/api/books/{book_id}/pages/2/text"
    assert client.get(url).json["text"].startswith("Elke ochtend")
    assert client.put(url, json={"text": "Een nieuwe zin."}).status_code == 200
    words = _words(client.get(f"/ocarina/api/books/{book_id}/pages/2").json)
    assert [w["text"] for w in words] == ["Een", "nieuwe", "zin"]
    assert client.put(url, json={"text": "  "}).status_code == 400


def test_term_image_upload_and_delete(app, client):
    "A picture can be attached, is served, and can be removed."
    import io  # pylint: disable=import-outside-toplevel

    with app.app_context():
        book_id = make_dutch_book("Image").id
    carla = _carla_id(client, book_id)
    url = f"/ocarina/api/terms/{carla}/image"
    bad = client.post(url, data={"file": (io.BytesIO(b"x"), "evil.exe")}, content_type="multipart/form-data")
    assert bad.status_code == 400
    ok = client.post(url, data={"file": (io.BytesIO(b"\x89PNG fake"), "pic.png")}, content_type="multipart/form-data")
    assert ok.status_code == 200 and ok.json["image"].startswith("/userimages/")
    assert client.get(ok.json["image"]).status_code == 200
    assert client.get(f"/ocarina/api/terms/{carla}").json["image"] == ok.json["image"]
    assert client.delete(url).json["image"] is None


def test_prefs_are_saved_in_the_data_folder_and_merged(client, monkeypatch, tmp_path):
    "Preferences survive between requests and new values merge into old ones."
    from ocarina import prefs  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(prefs, "path_for", lambda datapath: str(tmp_path / "prefs.json"))
    assert client.put("/ocarina/api/prefs", json={"speed.Dutch": 0.8}).json == {"speed.Dutch": 0.8}
    assert client.put("/ocarina/api/prefs", json={"follow": False}).json == {"speed.Dutch": 0.8, "follow": False}
    assert client.get("/ocarina/api/prefs").json["speed.Dutch"] == 0.8
    assert client.put("/ocarina/api/prefs", json=["not", "an", "object"]).status_code == 400



def test_bulk_status_by_text_creates_missing_terms(app, client):
    "Words you never opened have no term; setting their status by text creates one."
    with app.app_context():
        language_id = _get_test_language("Dutch").id
    r = client.post(
        "/ocarina/api/terms/bulk-status",
        json={"languageId": language_id, "texts": ["Woon", "kaas"], "status": 3},
    )
    assert r.status_code == 200 and r.json["count"] == 2
    with app.app_context():
        found = {t.text_lc: t.status for t in db.session.query(DBTerm).filter(DBTerm.text_lc.in_(["woon", "kaas"]))}
    assert found == {"woon": 3, "kaas": 3}
    assert client.post("/ocarina/api/terms/bulk-status", json={"texts": ["x"], "status": 3}).status_code == 400


def test_the_whole_text_is_read_and_replaced_page_by_page(app, client):
    with app.app_context():
        book_id = make_dutch_book("Alles bewerken").id
    url = f"/ocarina/api/books/{book_id}/text"
    assert client.get(url).json["pages"] == ["Hallo! Mijn naam is Carla.\n\nIk woon in Nederland.", "Elke ochtend sta ik op."]
    r = client.put(url, json={"pages": ["Een.", "Twee.", "Drie.", "  "]})  # a page left empty is dropped; a third one is added
    assert r.json == {"ok": True, "pageCount": 3}
    assert client.get(url).json["pages"] == ["Een.", "Twee.", "Drie."]
    assert client.get(f"/ocarina/api/books/{book_id}/pages/3").status_code == 200
    r = client.put(url, json={"pages": ["Alles in een."]})  # fewer pages: the rest go
    assert client.get(url).json["pages"] == ["Alles in een."]
    assert client.get(f"/ocarina/api/books/{book_id}/pages/2").status_code == 404
    assert client.put(url, json={"pages": [" "]}).status_code == 400
    assert client.put(url, json={"pages": "x"}).status_code == 400
    assert client.get("/ocarina/api/books/9999/text").status_code == 404
