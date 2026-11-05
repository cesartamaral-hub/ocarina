from lute.db import db
from lute.models.term import Term as DBTerm
from tests.conftest import _get_test_language


def test_vocabulary_counts_per_language(app, client):
    "Known is status 4, 5 and 99; learning 1 to 3; the rest is not counted."
    with app.app_context():
        dutch = _get_test_language("Dutch")
        for text, status in [("a", 1), ("b", 3), ("c", 4), ("d", 5), ("e", 99), ("f", 98), ("g", 0)]:
            t = DBTerm(dutch, text)
            t.status = status
            db.session.add(t)
        db.session.commit()
    got = client.get("/ocarina/api/stats/vocabulary").json
    dutch = next(r for r in got if r["name"] == "Dutch")
    assert (dutch["known"], dutch["learning"]) == (3, 2)
