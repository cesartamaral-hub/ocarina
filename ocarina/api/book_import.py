"""
JSON API for adding a book.

    GET  /ocarina/api/languages      languages to choose from
    POST /ocarina/api/books/extract  text of an uploaded file (txt, epub, pdf, srt, vtt)
                                     or of a web page ({"url": ...}); nothing is saved
    POST /ocarina/api/books          save a book (form fields: title, languageId, text,
                                     sourceUri, optional audio file)

Reading the file formats and the web page is Lute's own code (lute/book/service.py).
"""

import os

from flask import Blueprint, jsonify, request
from sqlalchemy import text as sql

from lute.book.forms import ALLOWED_AUDIO_EXTENSIONS
from lute.book.model import Book
from lute.book.service import BookImportException, FileTextExtraction, Service
from lute.db import db
from lute.models.repositories import BookRepository

bp = Blueprint("ocarina_book_import", __name__, url_prefix="/ocarina/api")

MAX_TITLE = 255
MAX_SOURCE = 1000
PDF_NOTE = "PDF text can be inaccurate because of how PDFs are encoded. Check it before saving."


def _error(message, status=400, **extra):
    return jsonify({"error": message, **extra}), status


@bp.route("/languages", methods=["GET"])
def languages():
    "Languages that books can be written in."
    rows = db.session.execute(sql("select LgID, LgName from languages order by LgName"))
    return jsonify([{"id": r[0], "name": r[1]} for r in rows])


@bp.route("/books/extract", methods=["POST"])
def extract():
    "Text of an uploaded file or a web page, for the user to check before saving."
    try:
        upload = request.files.get("file")
        if upload:
            name = upload.filename or ""
            content = FileTextExtraction().get_file_content(name, upload.stream)
            title = os.path.splitext(os.path.basename(name))[0]
            note = PDF_NOTE if name.lower().endswith(".pdf") else None
            return jsonify({"title": title, "text": content, "sourceUri": "", "note": note})
        url = (request.get_json(silent=True) or {}).get("url", "").strip()
        if not url.startswith(("http://", "https://")):
            return _error("Choose a file, or give a web address starting with http:// or https://")
        page = Service().book_data_from_url(url)
        return jsonify(
            {"title": page.title, "text": page.text, "sourceUri": page.source_uri, "note": None}
        )
    except BookImportException as e:
        return _error(e.message)
    except ValueError as e:  # an unknown file extension
        return _error(str(e))


@bp.route("/books", methods=["POST"])
def create_book():
    "Save a new book (and its own audio file, if one is sent); returns its id."
    form = request.form
    title = form.get("title", "").strip()
    body = form.get("text", "").strip()
    try:
        language_id = int(form.get("languageId", ""))
    except ValueError:
        return _error("Choose a language")
    if not title or len(title) > MAX_TITLE:
        return _error(f"The title is required and at most {MAX_TITLE} characters")
    if not body:
        return _error("The text is empty")
    if len(form.get("sourceUri", "")) > MAX_SOURCE:
        return _error(f"The source address is at most {MAX_SOURCE} characters")
    known = db.session.execute(
        sql("select 1 from languages where LgID = :i"), {"i": language_id}
    ).first()
    if not known:
        return _error("Unknown language")
    if BookRepository(db.session).find_by_title(title, language_id):
        return _error("A book with this title already exists in this language", 409)

    book = Book()
    book.language_id, book.title, book.text = language_id, title, body
    book.source_uri = form.get("sourceUri", "").strip() or None
    audio = request.files.get("audio")
    if audio and audio.filename:
        if audio.filename.rsplit(".", 1)[-1].lower() not in ALLOWED_AUDIO_EXTENSIONS:
            return _error("Audio must be one of: " + ", ".join(ALLOWED_AUDIO_EXTENSIONS))
        book.audio_stream, book.audio_stream_filename = audio.stream, audio.filename
    try:
        saved = Service().import_book(book, db.session)
    except BookImportException as e:
        db.session.rollback()
        return _error(e.message)
    return jsonify({"id": saved.id}), 201
