"""
A word index per book, and the reading statistics taken from it.

The index (table bookwords: each distinct word of a book and how often it occurs) is built once in the
background and rebuilt when the book's text changes (bookindex keeps a signature of the text it was built from).
Statistics are then one SQL join with the words you know, so they are exact and never stale: change a word's
status and the next list shows it. Only single words count; a multi-word phrase does not change the numbers.
"""

import hashlib
import threading
import time
from collections import Counter

from sqlalchemy import text as sql

from lute.db import db
from lute.models.book import Book

KNOWN = (4, 5, 99)
LEARNING = (1, 2, 3)
IGNORED = 98
WORDS_PER_MINUTE = 150

_lock = threading.Lock()
_building = set()


def signature(book):
    "Changes whenever the text of any page changes."
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(str(book.language_id).encode())
    for page in book.texts:
        digest.update(b"\0")
        digest.update(page.text.encode("utf-8"))
    return digest.hexdigest()


def build(book):
    "(Re)build the index of one book."
    language = book.language
    counts = Counter()
    for page in book.texts:
        for token in language.get_parsed_tokens(page.text):
            if token.is_word:
                counts[language.get_lowercase(token.token)[:250]] += 1
    sig = signature(book)
    db.session.execute(sql("delete from bookwords where BwBkID = :b"), {"b": book.id})
    if counts:
        db.session.execute(
            sql("insert into bookwords (BwBkID, BwWord, BwCount) values (:b, :w, :c)"),
            [{"b": book.id, "w": w, "c": c} for w, c in counts.items()],
        )
    db.session.execute(
        sql("insert or replace into bookindex (BiBkID, BiSignature, BiTotal) values (:b, :s, :t)"),
        {"b": book.id, "s": sig, "t": sum(counts.values())},
    )
    db.session.commit()


def stale_book_ids():
    "Books with no index, or an index built from other text."
    done = dict(db.session.execute(sql("select BiBkID, BiSignature from bookindex")).all())
    return [b.id for b in db.session.query(Book).all() if done.get(b.id) != signature(b)]


def build_in_background(app, book_ids):
    "Index the given books on a separate thread; books already being indexed are skipped."
    with _lock:
        todo = [i for i in book_ids if i not in _building]
        _building.update(todo)
    if not todo:
        return

    def work():
        with app.app_context():
            for book_id in todo:
                try:
                    book = db.session.get(Book, book_id)
                    if book is not None:
                        build(book)
                except Exception:  # pylint: disable=broad-exception-caught
                    db.session.rollback()  # a book that cannot be indexed shows no numbers; the rest go on
                finally:
                    with _lock:
                        _building.discard(book_id)

    threading.Thread(target=work, name="book-index", daemon=True).start()


def is_building(book_id):
    with _lock:
        return book_id in _building


def stats_by_book():
    """
    Reading statistics of every indexed book: {book id: dict}. Counts are of running words, except the
    "new" figure, which is distinct words. Ignored words are left out of the known share.
    """
    rows = db.session.execute(
        sql(
            """
            select b.BiBkID as book, w.BwWord as word, w.BwCount as n, coalesce(t.WoStatus, 0) as status
            from bookindex b
            join books k on k.BkID = b.BiBkID
            join bookwords w on w.BwBkID = b.BiBkID
            left join words t on t.WoLgID = k.BkLgID and t.WoTextLC = w.BwWord and t.WoTokenCount = 1
            """
        )
    ).all()
    totals = {i: t for i, t in db.session.execute(sql("select BiBkID, BiTotal from bookindex")).all()}
    result = {
        i: {"words": t, "unique": 0, "known": 0, "learning": 0, "ignored": 0, "new": 0, "newUnique": 0}
        for i, t in totals.items()
    }
    for row in rows:
        s = result[row.book]
        s["unique"] += 1
        if row.status in KNOWN:
            s["known"] += row.n
        elif row.status in LEARNING:
            s["learning"] += row.n
        elif row.status == IGNORED:
            s["ignored"] += row.n
        else:
            s["new"] += row.n
            s["newUnique"] += 1
    for s in result.values():
        counted = s["words"] - s["ignored"]
        s["knownPercent"] = round(100 * s["known"] / counted, 1) if counted > 0 else 100.0
        s["minutes"] = round(s["words"] / WORDS_PER_MINUTE)
    return result


def wait_until_idle(seconds=10):
    "Wait for background indexing to finish (the tests do, so a thread never outlives the database it writes to)."
    end = time.time() + seconds
    while time.time() < end:
        with _lock:
            if not _building:
                return True
        time.sleep(0.02)
    return False
