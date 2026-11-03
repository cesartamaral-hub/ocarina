"""
The term list: filters, sorting, paging, bulk changes, export.
"""

from lute.db import db
from lute.models.term import Term as DBTerm
from tests.conftest import _get_test_language

LIST = "/ocarina/api/term-list"


def _terms(app):
    "Three Dutch terms and a French one; returns their ids by text."
    with app.app_context():
        dutch, french = _get_test_language("Dutch"), _get_test_language("French")
        data = [
            (dutch, "huis", "house", 1),
            (dutch, "Hond", "dog", 3),
            (dutch, "kat", "cat", 98),
            (french, "chat", "cat", 2),
        ]
        ids = {}
        for lang, text, translation, status in data:
            t = DBTerm(lang, text)
            t.translation, t.status = translation, status
            db.session.add(t)
            db.session.flush()
            ids[text] = t.id
        db.session.commit()
        return ids


def _texts(client, query=""):
    return [r["text"] for r in client.get(f"{LIST}?{query}").json["rows"]]


def test_list_hides_ignored_and_sorts_by_text(app, client):
    "By default ignored terms are left out and rows sort by text, case-insensitive."
    _terms(app)
    assert _texts(client, "language=0") == ["chat", "Hond", "huis"]
    assert _texts(client, "includeIgnored=true") == ["chat", "Hond", "huis", "kat"]
    assert _texts(client, "sort=status&order=desc") == ["Hond", "chat", "huis"]


def test_filters_search_and_paging(app, client):
    "Language, status range, text or translation search, and paging."
    ids = _terms(app)
    with app.app_context():
        dutch_id = _get_test_language("Dutch").id
    assert _texts(client, f"language={dutch_id}") == ["Hond", "huis"]
    assert _texts(client, "statusMin=2&statusMax=3") == ["chat", "Hond"]
    assert _texts(client, "q=DOG") == ["Hond"]  # matches the translation, ignoring case
    assert _texts(client, "q=hu") == ["huis"]
    assert _texts(client, "q=%25") == []  # a percent sign is not a wildcard
    page = client.get(f"{LIST}?pageSize=25").json
    assert page["total"] == 3 and page["pageSize"] == 25
    assert len(ids) == 4


def test_bulk_status_tags_and_delete(app, client):
    "Bulk change the status, add and remove a tag, then delete."
    ids = _terms(app)
    two = [ids["huis"], ids["Hond"]]
    assert client.post("/ocarina/api/terms/bulk", json={"ids": two, "status": 5, "addTags": ["dieren"]}).status_code == 200
    rows = {r["text"]: r for r in client.get(f"{LIST}?sort=text").json["rows"]}
    assert rows["huis"]["status"] == 5 and rows["huis"]["tags"] == ["dieren"]
    assert _texts(client, "tag=dieren") == ["Hond", "huis"]
    assert "dieren" in client.get("/ocarina/api/tags").json
    client.post("/ocarina/api/terms/bulk", json={"ids": two, "removeTags": ["dieren"]})
    assert _texts(client, "tag=dieren") == []
    assert client.post("/ocarina/api/terms/bulk", json={"ids": [ids["huis"]], "delete": True}).json == {"deleted": 1}
    assert "huis" not in _texts(client)


def test_bulk_parent_and_mixed_languages(app, client):
    "A parent can be set in bulk; terms of two languages are refused."
    ids = _terms(app)
    r = client.post("/ocarina/api/terms/bulk", json={"ids": [ids["huis"]], "parent": "gebouw"})
    assert r.status_code == 200
    rows = {x["text"]: x for x in client.get(f"{LIST}?includeIgnored=true").json["rows"]}
    assert rows["huis"]["parents"] == ["gebouw"]
    assert _texts(client, "parentsOnly=true&q=hond") == ["Hond"]
    mixed = client.post("/ocarina/api/terms/bulk", json={"ids": [ids["huis"], ids["chat"]], "status": 4})
    assert mixed.status_code == 400 and "same language" in mixed.json["error"]


def test_bulk_rejects_bad_input(client):
    "Bad ids and bad statuses are a 400."
    assert client.post("/ocarina/api/terms/bulk", json={"ids": []}).status_code == 400
    assert client.post("/ocarina/api/terms/bulk", json={"ids": ["x"]}).status_code == 400
    assert client.post("/ocarina/api/terms/bulk", json={"ids": [1], "status": 7}).status_code == 400


def test_export_is_csv_of_all_matching_rows(app, client):
    "The export has a header and one line per matching term."
    _terms(app)
    r = client.get(f"{LIST}/export?q=cat")
    assert r.mimetype == "text/csv"
    lines = r.get_data(as_text=True).strip().splitlines()
    assert lines[0].startswith("term,parent,translation") and len(lines) == 2
    assert lines[1].startswith("chat,")
