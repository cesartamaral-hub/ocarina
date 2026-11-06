"""
A translated version of a book, kept per sentence so the reader can show it next to the text.

Sentences are the ones the audio timings use: the sentences of each page that contain a word, numbered from 0 on each page.
Translations come from the service chosen under Translation (a model on this Mac, MyMemory or DeepL); each one remembers a hash of
the sentence it was made from, so a sentence you edit later is the only one that is translated again.
"""

import hashlib

from sqlalchemy import text as sql

from lute.db import db
from ocarina import translate
from ocarina.tts.book_audio import book_sentences

FATAL = ("offline", "quota", "bad_key", "no_key", "no_model", "unsupported_language")
MAX_IN_A_ROW = 3  # sentences that fail one after another before the job gives up


def source_hash(text):
    "What a sentence looked like when it was translated."
    return hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]


def sentences_of(book):
    "[{page, index, text}] for every sentence of the book, in reading order."
    seen, found = {}, []
    for s in book_sentences(book):
        index = seen.get(s["page"], 0)
        seen[s["page"]] = index + 1
        found.append({"page": s["page"], "index": index, "text": s["text"]})
    return found


def _rows(book_id, lang):
    rows = db.session.execute(
        sql("select BtPage, BtIndex, BtText, BtSource, BtProvider from booktranslations where BtBkID = :b and BtLang = :l"),
        {"b": book_id, "l": lang},
    ).all()
    return {(r.BtPage, r.BtIndex): r for r in rows}


def status(book, lang):
    """
    Where the translation of a book stands: every sentence with its translation (None while missing), whether the
    translation is out of date (the sentence changed since), and how much is left to translate.
    """
    saved = _rows(book.id, lang)
    out, todo_chars, done, stale, by_page = [], 0, 0, 0, {}
    for s in sentences_of(book):
        row = saved.get((s["page"], s["index"]))
        old = bool(row) and row.BtSource != source_hash(s["text"]) and row.BtProvider != "manual"
        out.append({"page": s["page"], "index": s["index"], "translation": row.BtText if row else None, "stale": old})
        if row and not old:
            done += 1
        else:
            todo_chars += len(s["text"])
            by_page[str(s["page"])] = by_page.get(str(s["page"]), 0) + len(s["text"])
            stale += 1 if old else 0
    return {"sentences": out, "total": len(out), "done": done, "stale": stale, "remainingChars": todo_chars, "remainingByPage": by_page}


def save(book_id, page, index, lang, text, source_text, provider):
    "Keep one sentence's translation (replacing an earlier one)."
    db.session.execute(
        sql(
            "insert or replace into booktranslations (BtBkID, BtPage, BtIndex, BtLang, BtText, BtSource, BtProvider) "
            "values (:b, :p, :i, :l, :t, :s, :v)"
        ),
        {"b": book_id, "p": page, "i": index, "l": lang, "t": text, "s": source_hash(source_text), "v": provider},
    )
    db.session.commit()


def clear(book_id, lang=None):
    "Delete a book's translations (of one language, or all)."
    if lang:
        db.session.execute(sql("delete from booktranslations where BtBkID = :b and BtLang = :l"), {"b": book_id, "l": lang})
    else:
        db.session.execute(sql("delete from booktranslations where BtBkID = :b"), {"b": book_id})
    db.session.commit()


def provider_label(settings, models):
    "How the service is named when a translation is saved and shown."
    if settings["provider"] == "local":
        return next((m["name"] for m in models if m["id"] == settings.get("localModel")), "Local model")
    return translate.PROVIDERS[settings["provider"]]["name"]


def translate_book(book, datapath, settings, lang, scope, page, label, check, on_progress, engine=None):  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    """
    Translate the sentences that have no (current) translation: of one page, or of the whole book. Each is saved as soon as it is
    done, so cancelling or an error keeps what was finished. Returns how many sentences were translated.
    """
    saved = _rows(book.id, lang)
    todo = [
        s
        for s in sentences_of(book)
        if (scope == "book" or s["page"] == page)
        and not ((row := saved.get((s["page"], s["index"]))) and (row.BtSource == source_hash(s["text"]) or row.BtProvider == "manual"))
    ]
    done, failed = 0, 0
    for i, s in enumerate(todo):
        check()
        try:
            result = translate.translate(datapath, settings, book.language.name, s["text"], local_engine=engine)
            failed = 0
        except translate.TranslateError as e:
            if e.code in FATAL:
                raise
            failed += 1  # one sentence the service cannot take (too long, odd input): the rest go on
            if failed >= MAX_IN_A_ROW:
                raise
            on_progress(i + 1, len(todo))
            continue
        save(book.id, s["page"], s["index"], lang, result["translation"], s["text"], label)
        done += 1
        on_progress(i + 1, len(todo))
    return done


def clean_stored():
    "Translations saved with end-of-turn marks at their end (an old fault of one model) lose them; returns how many were cleaned."
    cleaned = 0
    for mark in translate.END_MARKS:
        found = db.session.execute(sql("select BtBkID, BtPage, BtIndex, BtLang, BtText from booktranslations where instr(BtText, :m) > 0"), {"m": mark}).all()
        for book, page, index, lang, text in found:
            db.session.execute(
                sql("update booktranslations set BtText = :t where BtBkID = :b and BtPage = :p and BtIndex = :i and BtLang = :l"),
                {"t": translate.strip_marks(text), "b": book, "p": page, "i": index, "l": lang},
            )
            cleaned += 1
    if cleaned:
        db.session.commit()
    return cleaned
