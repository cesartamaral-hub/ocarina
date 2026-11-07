"""
JSON API for reading a book page by page.

    GET  /ocarina/api/books/<id>/pages/<n>          a page as paragraphs of text items
    POST /ocarina/api/books/<id>/pages/<n>/finish   mark the page read (optionally rest as known)
    GET  /ocarina/api/books/<id>/pages/<n>/text     raw page text   (PUT replaces it)
    GET  /ocarina/api/books/<id>/text               the text of every page   (PUT {"pages": [...]} replaces all of it: pages are added or removed to match)
"""

from flask import Blueprint, jsonify, request

from lute.db import db
from lute.models.book import Text
from lute.models.language import Language
from lute.models.repositories import BookRepository
from lute.read.service import Service as ReadService
from ocarina import status_log
from ocarina.api.common import ZWS

bp = Blueprint("ocarina_pages", __name__, url_prefix="/ocarina/api")


def _item_json(item):
    return {
        "text": item.text.replace(ZWS, ""),
        "display": item.html_display_text,
        "isWord": bool(item.is_word),
        "termId": item.wo_id,
        "status": item.wo_status if item.wo_id is not None else 0,
        "sentence": item.sentence_number,
        "index": item.index,
    }


def _language_json(language):
    return {
        "id": language.id,
        "name": language.name,
        "rightToLeft": bool(language.right_to_left),
        "showRomanization": bool(language.show_romanization),
        "dictionaries": language.active_dict_uris("terms"),
        "sentenceDictionaries": language.sentence_dict_uris,
    }


@bp.route("/languages/<int:language_id>/reading", methods=["GET"])
def language_for_reading(language_id):
    "What the word panel needs of a language: its dictionaries, and whether it reads right to left or shows romanisation."
    language = db.session.get(Language, language_id)
    if language is None:
        return jsonify({"error": "No such language"}), 404
    return jsonify(_language_json(language))


@bp.route("/books/<int:book_id>/pages/<int:page>", methods=["GET"])
def get_page(book_id, page):
    "Open a page for reading: records the start date, creates unknown-word terms."
    book = BookRepository(db.session).find(book_id)
    if book is None or not 1 <= page <= book.page_count:
        return jsonify({"error": "No such page"}), 404
    paragraphs = ReadService(db.session).start_reading(book, page)
    return jsonify(
        {
            "bookId": book.id,
            "title": book.title,
            "language": _language_json(book.language),
            "page": page,
            "pageCount": book.page_count,
            "paragraphs": [
                [[_item_json(item) for item in sentence] for sentence in para]
                for para in paragraphs
            ],
        }
    )


@bp.route("/books/<int:book_id>/pages/<int:page>/finish", methods=["POST"])
def finish_page(book_id, page):
    "Mark the page as read; with restAsKnown, unknown words become well-known."
    body = request.get_json(silent=True) or {}
    book = BookRepository(db.session).find(book_id)
    if book is None or not 1 <= page <= book.page_count:
        return jsonify({"error": "No such page"}), 404
    if body.get("restAsKnown"):
        with status_log.skipping(db.session):  # words marked known here were not learned: they do not count as progress
            ReadService(db.session).mark_page_read(book_id, page, True)
    else:
        ReadService(db.session).mark_page_read(book_id, page, False)
    return jsonify({"ok": True})


@bp.route("/books/<int:book_id>/pages/<int:page>/text", methods=["GET", "PUT"])
def page_text(book_id, page):
    "The raw text of a page, or replace it."
    book = BookRepository(db.session).find(book_id)
    if book is None or not 1 <= page <= book.page_count:
        return jsonify({"error": "No such page"}), 404
    text = book.text_at_page(page)
    if request.method == "GET":
        return jsonify({"text": text.text})
    new_text = (request.get_json(silent=True) or {}).get("text")
    if not isinstance(new_text, str) or not new_text.strip():
        return jsonify({"error": "text is required"}), 400
    text.text = new_text
    db.session.add(text)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/books/<int:book_id>/text", methods=["GET", "PUT"])
def book_text(book_id):
    "The text of the whole book as a list of pages, or replace all of it (pages are added or removed to match; a page left empty is dropped)."
    book = BookRepository(db.session).find(book_id)
    if book is None:
        return jsonify({"error": "No such book"}), 404
    if request.method == "GET":
        return jsonify({"pages": [t.text for t in book.texts]})
    pages = (request.get_json(silent=True) or {}).get("pages")
    if not isinstance(pages, list) or not all(isinstance(p, str) for p in pages):
        return jsonify({"error": "pages must be a list of texts"}), 400
    pages = [p for p in pages if p.strip()]
    if not pages:
        return jsonify({"error": "The text cannot be empty"}), 400
    current = list(book.texts)
    for i, new_text in enumerate(pages):
        if i < len(current):
            if current[i].text != new_text:
                current[i].text = new_text
        else:
            db.session.add(Text(book, new_text, i + 1))
    for extra in current[len(pages) :]:
        book.texts.remove(extra)  # the book deletes a page that is taken out of it
    db.session.commit()
    return jsonify({"ok": True, "pageCount": len(pages)})
