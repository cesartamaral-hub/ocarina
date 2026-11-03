"""
Managing tags: list with usage counts, rename, comment, delete.
"""

from lute.db import db
from lute.models.term import Term as DBTerm
from tests.conftest import _get_test_language
from tests.ocarina.helpers import make_dutch_book

LIST = "/ocarina/api/tag-list"


def _tagged_term(app, text="boom", tags=("natuur",)):
    with app.app_context():
        term = DBTerm(_get_test_language("Dutch"), text)
        db.session.add(term)
        db.session.commit()
        return term.id, list(tags)


def test_term_tags_are_listed_with_uses_and_can_be_renamed(app, client):
    "A tag shows how many terms use it; renaming keeps the terms tagged."
    term_id, tags = _tagged_term(app)
    client.post("/ocarina/api/terms", json={"id": term_id, "status": 1, "tags": tags})
    listed = client.get(f"{LIST}/term").json
    tag = next(t for t in listed if t["text"] == "natuur")
    assert tag["uses"] == 1 and tag["comment"] == ""
    r = client.patch(f"{LIST}/term/{tag['id']}", json={"text": "planten", "comment": "alles wat groeit"})
    assert r.status_code == 200 and (r.json["text"], r.json["comment"], r.json["uses"]) == ("planten", "alles wat groeit", 1)
    assert client.get(f"/ocarina/api/terms/{term_id}").json["tags"] == ["planten"]


def test_book_tags_work_the_same(app, client):
    "Book tags are managed in their own list."
    with app.app_context():
        book_id = make_dutch_book("Getagd").id
    client.patch(f"/ocarina/api/books/{book_id}", json={"tags": ["A2"]})
    tag = next(t for t in client.get(f"{LIST}/book").json if t["text"] == "A2")
    assert tag["uses"] == 1
    assert client.patch(f"{LIST}/book/{tag['id']}", json={"text": "B1"}).json["text"] == "B1"


def test_rename_validation(app, client):
    "Empty, too long and duplicate names are refused; unknown kinds and ids are 404."
    _, tags = _tagged_term(app, "bloem", ("een", "twee"))
    term_id = _tagged_term(app, "tak", ())[0]
    client.post("/ocarina/api/terms", json={"id": term_id, "status": 1, "tags": ["een", "twee"]})
    listed = {t["text"]: t["id"] for t in client.get(f"{LIST}/term").json}
    assert client.patch(f"{LIST}/term/{listed['een']}", json={"text": " "}).status_code == 400
    assert client.patch(f"{LIST}/term/{listed['een']}", json={"text": "x" * 21}).status_code == 400
    assert client.patch(f"{LIST}/term/{listed['een']}", json={"comment": "c" * 201}).status_code == 400
    assert client.patch(f"{LIST}/term/{listed['een']}", json={"text": "twee"}).status_code == 409
    assert client.patch(f"{LIST}/term/99999", json={"text": "x"}).status_code == 404
    assert client.get(f"{LIST}/zin").status_code == 404


def test_delete_takes_the_tag_off_its_terms(app, client):
    "Deleting a tag removes it from the terms that had it, but keeps the terms."
    term_id, tags = _tagged_term(app, "struik", ("tuin",))
    client.post("/ocarina/api/terms", json={"id": term_id, "status": 1, "tags": tags})
    tag = next(t for t in client.get(f"{LIST}/term").json if t["text"] == "tuin")
    assert client.delete(f"{LIST}/term/{tag['id']}").json == {"deleted": tag["id"], "uses": 1}
    assert client.get(f"/ocarina/api/terms/{term_id}").json["tags"] == []
    assert client.delete(f"{LIST}/term/{tag['id']}").status_code == 404
