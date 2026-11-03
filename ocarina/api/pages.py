"""
JSON API for reading a book page by page.

    GET  /ocarina/api/books/<id>/pages/<n>          a page as paragraphs of text items
    POST /ocarina/api/books/<id>/pages/<n>/finish   mark the page read (optionally rest as known)
    GET  /ocarina/api/books/<id>/pages/<n>/text     raw page text   (PUT replaces it)
"""

from flask import Blueprint, jsonify, request

from lute.db import db
from lute.models.repositories import BookRepository
from lute.read.service import Service as ReadService
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
    ReadService(db.session).mark_page_read(book_id, page, bool(body.get("restAsKnown")))
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
