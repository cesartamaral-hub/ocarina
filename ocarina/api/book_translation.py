"""
JSON API for the translated version of a book (see ocarina/book_translation.py).

    GET    /ocarina/api/books/<id>/translation                    every sentence with its translation, and what is left
    POST   /ocarina/api/books/<id>/translation                    {"scope": "page" | "book", "page": n}: start a job
    PUT    /ocarina/api/books/<id>/translation/<page>/<index>     {"text": ...}: correct one sentence by hand
    DELETE /ocarina/api/books/<id>/translation                    remove the translation of the book
"""

from flask import Blueprint, current_app, jsonify, request

from lute.db import db
from lute.models.repositories import BookRepository
from ocarina import book_translation, translate
from ocarina.api import jobs
from ocarina.api import translate as translate_api
from ocarina.tts import models as model_files

bp = Blueprint("ocarina_book_translation", __name__, url_prefix="/ocarina/api")


def _book(book_id):
    return BookRepository(db.session).find(book_id)


def _info(settings):
    "Who translates and into what, for the page to show."
    return {
        "target": settings["target"],
        "targetName": translate.TARGETS[settings["target"]],
        "provider": settings["provider"],
        "providerName": book_translation.provider_label(settings, model_files.text_models()),
        "dailyLimit": 5000 if settings["provider"] == "mymemory" and not settings.get("email") else (50000 if settings["provider"] == "mymemory" else None),
    }


@bp.route("/books/<int:book_id>/translation", methods=["GET"])
def get_translation(book_id):
    "Every sentence of the book with its translation (null while there is none), and what is left to do."
    book = _book(book_id)
    if book is None:
        return jsonify({"error": "No such book"}), 404
    settings = translate_api._settings()  # pylint: disable=protected-access
    found = book_translation.status(book, settings["target"])
    return jsonify({**_info(settings), **found, "running": bool(jobs.active(kind="translate", book_id=book_id))})


def _run(app, job, check, book_id, scope, page, settings, label):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    def progress(done, total):
        job["done"], job["total"] = done, total

    with app.app_context():
        book = BookRepository(db.session).find(book_id)
        try:
            job["translated"] = book_translation.translate_book(
                book, app.env_config.datapath, settings, settings["target"], scope, page, label, check, progress, app.config.get("OCARINA_TTS_ENGINE")
            )
        except translate.TranslateError as e:
            raise RuntimeError(str(e)) from e  # the job shows the message as it is


@bp.route("/books/<int:book_id>/translation", methods=["POST"])
def start_translation(book_id):
    "Translate a page or the whole book with the service chosen under Translation; returns the job."
    book = _book(book_id)
    if book is None:
        return jsonify({"error": "No such book"}), 404
    body = request.get_json(silent=True) or {}
    scope, page = body.get("scope", "book"), body.get("page")
    if scope not in ("page", "book") or (scope == "page" and not isinstance(page, int)):
        return jsonify({"error": "Choose a page or the whole book"}), 400
    settings = translate_api._settings()  # pylint: disable=protected-access
    source = translate.code_for(book.language.name)
    if source is None:
        return jsonify({"error": f"Ocarina does not know the language code for {book.language.name} yet.", "code": "unsupported_language"}), 400
    if source == settings["target"]:
        return jsonify({"error": f"This book is already in {translate.TARGETS[source]}. Pick another language under Translation.", "code": "bad_input"}), 400
    if jobs.active(kind="translate", book_id=book_id):
        return jsonify({"error": "This book is already being translated.", "code": "already_queued"}), 409
    app = current_app._get_current_object()  # pylint: disable=protected-access
    label = book_translation.provider_label(settings, model_files.text_models())
    job = jobs.submit(
        "translate",
        lambda job, check: _run(app, job, check, book_id, scope, page, settings, label),
        book_id=book_id,
        title=book.title,
    )
    return jsonify(job), 202


@bp.route("/books/<int:book_id>/translation/<int:page>/<int:index>", methods=["PUT"])
def correct_sentence(book_id, page, index):
    "Replace one sentence's translation with your own wording; it is not translated again when the service or model changes."
    book = _book(book_id)
    text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
    sentence = next((s for s in book_translation.sentences_of(book) if (s["page"], s["index"]) == (page, index)), None) if book else None
    if sentence is None:
        return jsonify({"error": "No such sentence"}), 404
    if not text or len(text) > 2000:
        return jsonify({"error": "The translation is required, at most 2000 characters"}), 400
    book_translation.save(book_id, page, index, translate_api._settings()["target"], text, sentence["text"], "manual")  # pylint: disable=protected-access
    return jsonify({"page": page, "index": index, "translation": text})


@bp.route("/books/<int:book_id>/translation", methods=["DELETE"])
def remove_translation(book_id):
    "Remove the translation of the book (every language)."
    if _book(book_id) is None:
        return jsonify({"error": "No such book"}), 404
    if jobs.active(kind="translate", book_id=book_id):
        return jsonify({"error": "The book is being translated. Cancel that first."}), 409
    book_translation.clear(book_id)
    return jsonify({"ok": True})
