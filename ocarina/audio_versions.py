"""
Audio versions of a book: your own recordings and the audio Ocarina generated, kept side by side.

Lute keeps one audio file per book (books.BkAudioFilename). That column stays the *selected* version, so
the player, the stream route and sentence following keep working unchanged; the table bookaudios lists all
versions. Audio that existed before the table is added as a version the first time the book is looked at.
"""

import json
import os

from sqlalchemy import text as sql

from lute.db import db
from ocarina.tts import models as model_files
from ocarina.tts.book_audio import has_timings, is_ocarina_audio, timings_info, timings_path

OWN, GENERATED = "own", "generated"
MAX_LABEL = 100


def _json(row, selected_filename, audio_dir):
    "A version as the API shows it."
    exists = os.path.exists(os.path.join(audio_dir, row.BaFilename))
    model = model_files.find_model(row.BaModel) if row.BaModel else None
    return {
        "id": row.BaID,
        "label": row.BaLabel,
        "kind": row.BaKind,
        "model": row.BaModel,
        "modelName": model["name"] if model else row.BaModel,
        "voice": row.BaVoice,
        "pause": row.BaPause,
        "created": row.BaCreated,
        "selected": row.BaFilename == selected_filename,
        "hasTimings": has_timings(audio_dir, row.BaFilename),
        "synced": bool((timings_info(audio_dir, row.BaFilename) or {}).get("aligned")),
        "missing": not exists,
    }


def _rows(book_id):
    return db.session.execute(
        sql("select * from bookaudios where BaBkID = :b order by BaCreated, BaID"), {"b": book_id}
    ).all()


def sync(book, audio_dir):
    "Make sure the book's selected audio has a version row (books from before versions, or imported by Lute's code)."
    if not book.audio_filename:
        return
    known = db.session.execute(
        sql("select 1 from bookaudios where BaBkID = :b and BaFilename = :f"), {"b": book.id, "f": book.audio_filename}
    ).first()
    if known:
        return
    if is_ocarina_audio(audio_dir, book.audio_filename):
        try:
            with open(timings_path(os.path.join(audio_dir, book.audio_filename)), encoding="utf-8") as f:
                model_id = json.load(f).get("model")
        except (OSError, ValueError):
            model_id = None
        found = model_files.find_model(model_id) if model_id else None
        _insert(book.id, book.audio_filename, GENERATED, found["name"] if found else "Generated audio", model_id)
    else:
        _insert(book.id, book.audio_filename, OWN, "Original")
    db.session.commit()


def _insert(book_id, filename, kind, label, model=None, voice=None, pause=None):
    result = db.session.execute(
        sql(
            "insert into bookaudios (BaBkID, BaFilename, BaLabel, BaKind, BaModel, BaVoice, BaPause) "
            "values (:b, :f, :l, :k, :m, :v, :p)"
        ),
        {"b": book_id, "f": filename, "l": label[:MAX_LABEL], "k": kind, "m": model, "v": voice, "p": pause},
    )
    return result.lastrowid


def list_versions(book, audio_dir):
    "All versions of the book, oldest first."
    sync(book, audio_dir)
    return [_json(r, book.audio_filename, audio_dir) for r in _rows(book.id)]


def find(book, version_id):
    "The version's row (its BaFilename, BaKind, ...), or None if the book has no such version."
    return next((r for r in _rows(book.id) if r.BaID == version_id), None)


def add(book, filename, kind, label, model=None, voice=None, pause=None, select=True):
    "Add a version (and make it the selected one); returns its id."
    version_id = _insert(book.id, filename, kind, label, model, voice, pause)
    if select:
        _select(book, filename)
    db.session.add(book)
    db.session.commit()
    return version_id


def _select(book, filename):
    book.audio_filename = filename
    book.audio_current_pos = 0  # a position in one recording means nothing in another
    book.audio_bookmarks = None


def find_same_generated(book, model, voice, pause):
    "The generated version made with exactly these settings, or None."
    for r in _rows(book.id):
        if r.BaKind == GENERATED and r.BaModel == model and r.BaVoice == voice and r.BaPause is not None and abs(r.BaPause - pause) < 1e-6:
            return r
    return None


def select(book, version_id):
    "Make a version the book's audio; False if the book has no such version."
    row = next((r for r in _rows(book.id) if r.BaID == version_id), None)
    if row is None:
        return False
    _select(book, row.BaFilename)
    db.session.add(book)
    db.session.commit()
    return True


def rename(book, version_id, label):
    "Change a version's label; False if the book has no such version."
    if not any(r.BaID == version_id for r in _rows(book.id)):
        return False
    db.session.execute(sql("update bookaudios set BaLabel = :l where BaID = :i"), {"l": label[:MAX_LABEL], "i": version_id})
    db.session.commit()
    return True


def _delete_files(audio_dir, filename):
    for suffix in ("", ".sentences.json"):
        path = os.path.join(audio_dir, filename + suffix)
        if os.path.exists(path):
            os.remove(path)


def remove(book, version_id, audio_dir):
    """
    Remove a version. Generated audio is deleted from disk; your own recording stays in the audio folder
    (only the entry goes). If it was the selected one, the newest remaining version is selected, or none.
    Returns the removed version's json, or None if the book has no such version.
    """
    rows = _rows(book.id)
    row = next((r for r in rows if r.BaID == version_id), None)
    if row is None:
        return None
    shown = _json(row, book.audio_filename, audio_dir)
    db.session.execute(sql("delete from bookaudios where BaID = :i"), {"i": version_id})
    if row.BaFilename == book.audio_filename:
        rest = [r for r in rows if r.BaID != version_id]
        _select(book, rest[-1].BaFilename if rest else None)
        db.session.add(book)
    db.session.commit()
    if row.BaKind == GENERATED:
        _delete_files(audio_dir, row.BaFilename)
    else:
        drop_timings(audio_dir, row.BaFilename)  # the recording stays; timings we made for it do not
    return shown


def generated_filenames(book):
    "Files of the book's generated versions (to delete with the book)."
    return [r.BaFilename for r in _rows(book.id) if r.BaKind == GENERATED]


def drop_generated_file(audio_dir, filename):
    "Delete a generated audio file and its timings."
    _delete_files(audio_dir, filename)


def drop_timings(audio_dir, filename):
    "Delete the sentence timings of an audio file (your recording itself stays)."
    path = os.path.join(audio_dir, filename + ".sentences.json")
    if os.path.exists(path):
        os.remove(path)
