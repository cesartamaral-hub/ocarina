"""
Words learned in Ocarina: the status log (written by triggers), what counts, and the numbers the Books page shows.
"""

import pytest
from sqlalchemy import text as sql

from lute.db import db
from ocarina import prefs, status_log
from tests.conftest import _get_test_language
from tests.ocarina.helpers import make_dutch_book


@pytest.fixture
def lang(app):
    with app.app_context():
        yield _get_test_language("Dutch").id


def add_word(language_id, text, status):
    db.session.execute(
        sql("insert into words (WoLgID, WoText, WoTextLC, WoStatus, WoTokenCount, WoStatusChanged) values (:l, :t, :t, :s, 1, current_timestamp)"),
        {"l": language_id, "t": text, "s": status},
    )
    db.session.commit()
    return db.session.execute(sql("select WoID from words where WoText = :t and WoLgID = :l"), {"t": text, "l": language_id}).scalar()


def set_status(word_id, status):
    db.session.execute(sql("update words set WoStatus = :s where WoID = :i"), {"s": status, "i": word_id})
    db.session.commit()


def learned(language_id, prior=()):
    return status_log.learned_counts(db.session, prior).get(language_id, 0)


def test_a_word_you_worked_on_and_reached_known_counts(lang):
    unseen = add_word(lang, "huis", 0)  # seen, not started: not logged
    assert db.session.execute(sql("select count(*) from statuslog")).scalar() == 0
    set_status(unseen, 1)
    set_status(unseen, 3)
    assert learned(lang) == 0
    set_status(unseen, 4)
    assert learned(lang) == 1
    set_status(unseen, 5)  # Known to Known is not a second word
    assert learned(lang) == 1
    set_status(add_word(lang, "boom", 0), 99)  # set straight to well known by hand
    assert learned(lang) == 2


def test_a_word_that_fell_back_is_not_counted_until_it_is_known_again(lang):
    word = add_word(lang, "fiets", 1)
    set_status(word, 4)
    assert learned(lang) == 1
    set_status(word, 2)
    assert learned(lang) == 0
    set_status(word, 5)
    assert learned(lang) == 1


def test_words_marked_known_in_bulk_do_not_count(lang):
    with status_log.skipping(db.session):
        skipped = add_word(lang, "tafel", 99)
        set_status(add_word(lang, "stoel", 0), 99)
    assert learned(lang) == 0
    assert db.session.execute(sql("select how from statuscontext")).scalar() == "hand"  # the context is put back
    set_status(skipped, 2)  # work on it afterwards...
    set_status(skipped, 4)  # ...and it counts
    assert learned(lang) == 1


def test_what_was_known_before_counts_only_when_you_choose(lang):
    add_word(lang, "oud", 99)
    db.session.execute(sql("delete from statuslog"))  # as if it was known before the app kept a log
    db.session.commit()
    with status_log.skipping(db.session):
        add_word(lang, "ouder", 5)
    set_status(add_word(lang, "nieuw", 1), 4)
    assert learned(lang) == 1
    assert learned(lang, prior=[lang]) == 3
    series = status_log.learned_growth(db.session, [lang])[lang]
    assert series[-1]["learned"] == 3


def test_finishing_a_page_with_the_rest_as_known_is_not_progress(app, client, lang):
    book = make_dutch_book("Voortgang")
    assert client.get(f"/ocarina/api/books/{book.id}/pages/1").status_code == 200  # unseen words get terms (status 0)
    r = client.post(f"/ocarina/api/books/{book.id}/pages/1/finish", json={"restAsKnown": True})
    assert r.status_code == 200
    assert db.session.execute(sql("select count(*) from words where WoStatus = 99")).scalar() > 0
    assert learned(lang) == 0


def test_the_book_list_gets_the_learned_count_goal_and_choice(app, client, lang):
    set_status(add_word(lang, "werk", 2), 4)
    prefs.update(prefs.path_for(app.env_config.datapath), {f"learned.goal.{lang}": 250, f"learned.prior.{lang}": True})
    row = next(r for r in client.get("/ocarina/api/stats/vocabulary").json if r["id"] == lang)
    assert row["learned"] == 1 and row["goal"] == 250 and row["countsPrior"] is True
    prefs.update(prefs.path_for(app.env_config.datapath), {f"learned.goal.{lang}": None, f"learned.prior.{lang}": False})
    row = next(r for r in client.get("/ocarina/api/stats/vocabulary").json if r["id"] == lang)
    assert row["goal"] is None and row["countsPrior"] is False
