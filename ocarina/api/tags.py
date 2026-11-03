"""
JSON API for managing tags (the names you put on terms and on books).

    GET    /ocarina/api/tag-list/<kind>       tags with how many terms or books use each (kind: term or book)
    PATCH  /ocarina/api/tag-list/<kind>/<id>  rename a tag or change its comment
    DELETE /ocarina/api/tag-list/<kind>/<id>  delete a tag (it is taken off whatever used it)

Putting a tag on a term or a book is done where you edit them (terms.py, books.py).
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import text as sql
from sqlalchemy.exc import IntegrityError

from lute.db import db
from lute.models.book import BookTag
from lute.models.term import TermTag

bp = Blueprint("ocarina_tags", __name__, url_prefix="/ocarina/api")

MAX_TAG, MAX_COMMENT = 20, 200
KINDS = {
    "term": {"model": TermTag, "count": "select count(*) from wordtags where WtTgID = :i", "table": "tags"},
    "book": {"model": BookTag, "count": "select count(*) from booktags where BtT2ID = :i", "table": "tags2"},
}


def _comment(tag):
    return tag.comment or ""


def _tag_json(kind, tag):
    uses = db.session.execute(sql(KINDS[kind]["count"]), {"i": tag.id}).scalar()
    return {"id": tag.id, "text": tag.text, "comment": _comment(tag), "uses": uses}


@bp.route("/tag-list/<kind>", methods=["GET"])
def tag_list(kind):
    "All tags of a kind, by name."
    if kind not in KINDS:
        return jsonify({"error": "Unknown kind of tag"}), 404
    tags = db.session.query(KINDS[kind]["model"]).all()
    tags.sort(key=lambda t: t.text.lower())
    return jsonify([_tag_json(kind, t) for t in tags])


@bp.route("/tag-list/<kind>/<int:tag_id>", methods=["PATCH"])
def change_tag(kind, tag_id):
    "Rename a tag or change its comment."
    if kind not in KINDS:
        return jsonify({"error": "Unknown kind of tag"}), 404
    tag = db.session.get(KINDS[kind]["model"], tag_id)
    if tag is None:
        return jsonify({"error": "No such tag"}), 404
    body = request.get_json(silent=True) or {}
    if "text" in body:
        name = (body["text"] or "").strip()
        if not name or len(name) > MAX_TAG:
            return jsonify({"error": f"A tag name is required and at most {MAX_TAG} characters"}), 400
        tag.text = name
    if "comment" in body:
        comment = (body["comment"] or "").strip()
        if len(comment) > MAX_COMMENT:
            return jsonify({"error": f"A comment is at most {MAX_COMMENT} characters"}), 400
        tag.comment = comment
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "A tag with that name already exists"}), 409
    return jsonify(_tag_json(kind, tag))


@bp.route("/tag-list/<kind>/<int:tag_id>", methods=["DELETE"])
def delete_tag(kind, tag_id):
    "Delete a tag and take it off everything that used it."
    if kind not in KINDS:
        return jsonify({"error": "Unknown kind of tag"}), 404
    tag = db.session.get(KINDS[kind]["model"], tag_id)
    if tag is None:
        return jsonify({"error": "No such tag"}), 404
    uses = _tag_json(kind, tag)["uses"]
    db.session.delete(tag)
    db.session.commit()
    return jsonify({"deleted": tag_id, "uses": uses})
