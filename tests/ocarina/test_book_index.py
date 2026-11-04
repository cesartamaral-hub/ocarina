import time

from lute.db import db
from lute.models.term import Term
from ocarina import book_index
from tests.conftest import _get_test_language
from tests.ocarina.helpers import make_dutch_book


def _know(word, status):
    term = Term(_get_test_language("Dutch"), word)
    term.status = status
    db.session.add(term)
    db.session.commit()


def test_index_counts_each_word(app):
    with app.app_context():
        book = make_dutch_book()
        book_index.build(book)
        stats = book_index.stats_by_book()[book.id]
        assert stats["words"] == 14  # hallo mijn naam is carla ik woon in nederland elke ochtend sta ik op
        assert stats["unique"] == 13  # "ik" twice
        assert stats["new"] == 14 and stats["known"] == 0
        assert stats["knownPercent"] == 0.0


def test_statuses_are_read_live(app):
    with app.app_context():
        book = make_dutch_book()
        book_index.build(book)
        _know("ik", 5)  # twice in the book
        _know("woon", 2)
        _know("elke", 98)
        stats = book_index.stats_by_book()[book.id]
        assert (stats["known"], stats["learning"], stats["ignored"], stats["new"]) == (2, 1, 1, 10)
        assert stats["newUnique"] == 10
        assert stats["knownPercent"] == round(100 * 2 / 13, 1)  # the ignored word is left out


def test_changed_text_makes_the_index_stale(app):
    with app.app_context():
        book = make_dutch_book()
        assert book.id in book_index.stale_book_ids()
        book_index.build(book)
        assert book.id not in book_index.stale_book_ids()
        book.texts[0].text = "Iets anders."
        db.session.commit()
        assert book.id in book_index.stale_book_ids()
        book_index.build(book)
        assert book_index.stats_by_book()[book.id]["words"] == 2 + 5


def test_list_shows_stats_after_background_build(app, client):
    with app.app_context():
        book_id = make_dutch_book().id
    book_index.build_in_background(app, [book_id])
    for _ in range(100):
        if not book_index.is_building(book_id):
            break
        time.sleep(0.05)
    listed = client.get("/ocarina/api/books").json
    mine = next(b for b in listed if b["id"] == book_id)
    assert mine["stats"]["words"] == 14
    assert mine["indexing"] is False
