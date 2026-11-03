"""
JSON API for the audio versions of a book (your own recordings and generated audio, kept side by side).

    GET    /ocarina/api/books/<id>/audio/versions                     all versions; one is selected
    PUT    /ocarina/api/books/<id>/audio/versions/<version>/select    make it the book's audio
    PATCH  /ocarina/api/books/<id>/audio/versions/<version>           rename ({"label": ...})
    DELETE /ocarina/api/books/<id>/audio/versions/<version>           remove it (generated files are deleted,
                                                                      your own recording stays on disk)
Generating audio and uploading your own add versions (see audio.py).
"""

from flask import Blueprint, current_app, jsonify, request

from lute.db import db
from lute.models.repositories import BookRepository
from ocarina import audio_versions
from ocarina.api import jobs

bp = Blueprint("ocarina_audio_versions", __name__, url_prefix="/ocarina/api")


def _book(book_id):
    return BookRepository(db.session).find(book_id)


def _dir():
    return current_app.env_config.useraudiopath


@bp.route("/books/<int:book_id>/audio/versions", methods=["GET"])
def list_versions(book_id):
    "All audio versions of a book."
    book = _book(book_id)
    if book is None:
        return jsonify({"error": "No such book"}), 404
    return jsonify(audio_versions.list_versions(book, _dir()))


@bp.route("/books/<int:book_id>/audio/versions/<int:version_id>/select", methods=["PUT"])
def select_version(book_id, version_id):
    "Make a version the book's audio (the player, and sentence following when it has timings, use it)."
    book = _book(book_id)
    if book is None or not audio_versions.select(book, version_id):
        return jsonify({"error": "No such audio version"}), 404
    return jsonify(audio_versions.list_versions(book, _dir()))


@bp.route("/books/<int:book_id>/audio/versions/<int:version_id>", methods=["PATCH"])
def rename_version(book_id, version_id):
    "Rename a version."
    book = _book(book_id)
    label = ((request.get_json(silent=True) or {}).get("label") or "").strip()
    if not label or len(label) > audio_versions.MAX_LABEL:
        return jsonify({"error": f"A name is required, at most {audio_versions.MAX_LABEL} characters"}), 400
    if book is None or not audio_versions.rename(book, version_id, label):
        return jsonify({"error": "No such audio version"}), 404
    return jsonify(audio_versions.list_versions(book, _dir()))


@bp.route("/books/<int:book_id>/audio/versions/<int:version_id>", methods=["DELETE"])
def delete_version(book_id, version_id):
    "Remove a version; if it was selected, the newest remaining one is selected."
    book = _book(book_id)
    if book is None:
        return jsonify({"error": "No such book"}), 404
    if jobs.active(kind="audio", book_id=book_id):
        return jsonify({"error": "Audio for this book is being generated. Cancel it first."}), 409
    removed = audio_versions.remove(book, version_id, _dir())
    if removed is None:
        return jsonify({"error": "No such audio version"}), 404
    return jsonify({"removed": removed, "versions": audio_versions.list_versions(book, _dir())})
