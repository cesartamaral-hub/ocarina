"""
The sentence a word was saved from, shown on the Vocabulary page.

New words keep the sentence they were saved from in the reader (`remember`). Words saved before that have none: a background pass
(`backfill_in_background`) gives each the first sentence of the language's books that has it (TcFound says it was found, not
recorded). A word no book has stays without one, and is not looked for again.
"""

import re
import threading

from sqlalchemy import text as sql

from lute.db import db
from lute.models.term import Term as DBTerm

ZWS = chr(0x200B)
MAX_SENTENCE = 600
_lock = threading.Lock()
_running = False


def clean_sentence(sentence):
    "A sentence as plain text: no parser markers, spaces tidied, not too long."
    out = re.sub(r"\s+", " ", (sentence or "").replace(ZWS, "").replace("¶", " ")).strip()
    return out[:MAX_SENTENCE]


def remember(term_id, sentence, book_id=None, page=None):
    "Keep the sentence a word was saved from, unless it has one that was really recorded."
    text = clean_sentence(sentence)
    if not text or not term_id:
        return
    row = db.session.execute(sql("select TcFound from termcontexts where TcWoID = :w"), {"w": term_id}).first()
    if row is not None and not row[0]:
        return
    db.session.execute(sql("delete from termcontexts where TcWoID = :w"), {"w": term_id})
    db.session.execute(
        sql("insert into termcontexts (TcWoID, TcBkID, TcPage, TcSentence, TcFound) values (:w, :b, :p, :s, 0)"),
        {"w": term_id, "b": book_id, "p": page, "s": text},
    )
    db.session.commit()


def _first_sentence(term):
    "(book id, page, sentence) of the first sentence of the language's books that has the word; None when none does."
    pattern = f"%{ZWS}{term.text_lc}{ZWS}%"
    row = db.session.execute(
        sql(
            """
            SELECT texts.TxBkID, TxOrder, SeText FROM sentences
            INNER JOIN texts ON TxID = SeTxID
            INNER JOIN books ON BkID = texts.TxBkID
            WHERE SeText IS NOT NULL AND BkLgID = :lg
            AND CASE WHEN SeTextLC == '*' THEN SeText ELSE SeTextLC END LIKE :pattern
            ORDER BY (TxReadDate IS NULL), TxReadDate, TxID, SeOrder
            LIMIT 1
            """
        ),
        {"lg": term.language.id, "pattern": pattern},
    ).first()
    return (row[0], row[1], clean_sentence(row[2])) if row else None


def missing_term_ids():
    "Words with a status that have no sentence yet (and have not been looked for)."
    rows = db.session.execute(
        sql("select WoID from words left join termcontexts on TcWoID = WoID where TcWoID is null and WoStatus > 0 order by WoID")
    )
    return [r[0] for r in rows]


def backfill(batch=40):
    "Find a sentence for each word that has none; returns how many were found."
    found = 0
    ids = missing_term_ids()
    for start in range(0, len(ids), batch):
        for term_id in ids[start : start + batch]:
            term = db.session.get(DBTerm, term_id)
            if term is None:
                continue
            got = _first_sentence(term)
            db.session.execute(
                sql("insert or ignore into termcontexts (TcWoID, TcBkID, TcPage, TcSentence, TcFound) values (:w, :b, :p, :s, 1)"),
                {"w": term_id, "b": got[0] if got else None, "p": got[1] if got else None, "s": got[2] if got else ""},
            )
            found += bool(got)
        db.session.commit()
    return found


def backfill_in_background(app):
    "Do it on a separate thread (once at a time)."
    global _running  # pylint: disable=global-statement
    with _lock:
        if _running:
            return
        _running = True

    def work():
        global _running  # pylint: disable=global-statement
        try:
            with app.app_context():
                backfill()
        except Exception:  # pylint: disable=broad-exception-caught
            db.session.rollback()  # the words simply show no sentence; the next start tries again
        finally:
            with _lock:
                _running = False

    threading.Thread(target=work, name="term-context", daemon=True).start()


def wait_until_idle(seconds=10):
    "Wait for the background pass to finish (the tests do, so a thread never outlives the database it writes to)."
    import time  # pylint: disable=import-outside-toplevel

    end = time.time() + seconds
    while _running and time.time() < end:
        time.sleep(0.05)
