"""
JSON API for terms (words and phrases): read, save, status, hover data, references, pictures.

    GET    /ocarina/api/terms/<id>              one term
    POST   /ocarina/api/terms                   create or update a term
    GET    /ocarina/api/terms/lookup            a term by language and text (new if unknown)
    PATCH  /ocarina/api/terms/<id>/status       set only the status
    POST   /ocarina/api/terms/bulk-status       set the status of several terms
    GET    /ocarina/api/terms/<id>/popup        short hover data
    GET    /ocarina/api/terms/<id>/references   sentences in other books
    POST   /ocarina/api/terms/<id>/image        upload a picture (DELETE removes it)
"""

import os
import re
import uuid

from flask import Blueprint, current_app, jsonify, request

from lute.db import db
from lute.models.term import Term as DBTerm, Status
from lute.read.render.service import Service as RenderService
from lute.term.model import ReferencesRepository
from lute.term.model import Repository as TermRepository
from ocarina.api.common import ZWS, clean

bp = Blueprint("ocarina_terms", __name__, url_prefix="/ocarina/api")

STATUSES = {0, 1, 2, 3, 4, 5, 98, 99}
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _image_url(dbterm):
    image = dbterm.get_current_image()
    return f"/userimages/{dbterm.language.id}/{image}" if image else None


def _components(dbterm):
    "Known terms that are inside a multiword term, in the order they appear."
    if dbterm.token_count <= 1:
        return []
    found = RenderService(db.session).find_all_Terms_in_string(dbterm.text, dbterm.language)
    return [
        {
            "id": c.id,
            "text": clean(c.text),
            "translation": clean(c.translation),
            "status": c.status,
        }
        for c in found
        if c.id != dbterm.id and c.status != Status.UNKNOWN
    ]


def _extras(term_id):
    "Fields that need the database term: image and component words."
    dbterm = db.session.get(DBTerm, term_id) if term_id else None
    if dbterm is None:
        return {"image": None, "components": []}
    return {"image": _image_url(dbterm), "components": _components(dbterm)}


def _term_json(t):
    "A term business object as JSON."
    return {
        "id": t.id,
        "languageId": t.language_id,
        "text": t.text,
        "displayText": (t.text or "").replace(ZWS, ""),
        "translation": t.translation or "",
        "romanization": t.romanization or "",
        "status": t.status,
        "tags": list(t.term_tags),
        "parents": list(t.parents),
        "syncStatus": bool(t.sync_status),
        **_extras(t.id),
    }


@bp.route("/terms/<int:term_id>", methods=["GET"])
def get_term(term_id):
    "One term."
    try:
        term = TermRepository(db.session).load(term_id)
    except ValueError:
        return jsonify({"error": "No such term"}), 404
    return jsonify(_term_json(term))


@bp.route("/terms", methods=["POST"])
def save_term():
    "Create a term, or update the one with the given id."
    body = request.get_json(silent=True) or {}
    status = int(body.get("status", 1))
    if status not in STATUSES:
        return jsonify({"error": f"Bad status {status}"}), 400
    repo = TermRepository(db.session)
    if body.get("id"):
        try:
            term = repo.load(body["id"])
        except ValueError:
            return jsonify({"error": "No such term"}), 404
    else:
        if not body.get("languageId") or not body.get("text"):
            return jsonify({"error": "languageId and text are required"}), 400
        term = repo.find_or_new(body["languageId"], body["text"])
    term.status = status
    term.translation = body.get("translation", term.translation)
    term.romanization = body.get("romanization", term.romanization)
    if "tags" in body:
        term.term_tags = [t.strip() for t in body["tags"] if t.strip()]
    if "parents" in body:
        term.parents = [p.strip() for p in body["parents"] if p.strip()]
    repo.add(term)
    repo.commit()
    saved = repo.find(term.language_id, term.text)
    return jsonify(_term_json(saved))


@bp.route("/terms/<int:term_id>/status", methods=["PATCH"])
def set_status(term_id):
    "Change only the status of a term."
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in STATUSES:
        return jsonify({"error": f"Bad status {status}"}), 400
    repo = TermRepository(db.session)
    try:
        term = repo.load(term_id)
    except ValueError:
        return jsonify({"error": "No such term"}), 404
    term.status = status
    repo.add(term)
    repo.commit()
    return jsonify({"id": term_id, "status": status})


@bp.route("/terms/lookup", methods=["GET"])
def lookup_term():
    "A term by language and text: the saved one, or a new unsaved one (id is null)."
    language_id = request.args.get("languageId", type=int)
    text = (request.args.get("text") or "").strip()
    if not language_id or not text:
        return jsonify({"error": "languageId and text are required"}), 400
    return jsonify(_term_json(TermRepository(db.session).find_or_new(language_id, text)))


@bp.route("/terms/<int:term_id>/popup", methods=["GET"])
def term_popup(term_id):
    "What to show when hovering a word."
    t = db.session.get(DBTerm, term_id)
    if t is None:
        return jsonify({"error": "No such term"}), 404
    parents = [{"text": clean(p.text), "translation": clean(p.translation)} for p in t.parents]
    translation = clean(t.translation)
    if not translation and len(parents) == 1:
        translation = parents[0]["translation"]
    return jsonify(
        {
            "id": t.id,
            "text": clean(t.text),
            "status": t.status,
            "translation": translation,
            "romanization": clean(t.romanization),
            "tags": [tag.text for tag in t.term_tags],
            "parents": [p for p in parents if p["translation"] and p["translation"] != translation],
            "image": _image_url(t),
        }
    )


def _reference_json(ref):
    "A reference with the matched word marked: parts of {text, bold}."
    parts = [
        {"text": chunk[3:-4] if chunk.startswith("<b>") else chunk, "bold": chunk.startswith("<b>")}
        for chunk in re.split(r"(<b>.*?</b>)", ref.sentence or "")
        if chunk
    ]
    return {"bookId": ref.book_id, "page": ref.page_number, "title": ref.title, "sentence": parts}


@bp.route("/terms/<int:term_id>/references", methods=["GET"])
def term_references(term_id):
    "Sentences with this term (and its children and parents) from pages read so far."
    if db.session.get(DBTerm, term_id) is None:
        return jsonify({"error": "No such term"}), 404
    refs = ReferencesRepository(db.session, limit=20).find_references_by_id(term_id)
    # "term" is a list of references; "children" and "parents" are lists of {term, refs}.
    return jsonify(
        {
            "term": [_reference_json(r) for r in refs["term"]],
            "children": [
                {"term": clean(g["term"]), "references": [_reference_json(r) for r in g["refs"]]}
                for g in refs["children"]
            ],
            "parents": [
                {"term": clean(g["term"]), "references": [_reference_json(r) for r in g["refs"]]}
                for g in refs["parents"]
            ],
        }
    )


@bp.route("/terms/bulk-status", methods=["POST"])
def bulk_status():
    "Set the same status on several terms."
    body = request.get_json(silent=True) or {}
    status = body.get("status")
    ids = body.get("termIds") or []
    if status not in STATUSES or not ids:
        return jsonify({"error": "status and termIds are required"}), 400
    repo = TermRepository(db.session)
    for term_id in ids:
        term = repo.load(term_id)
        term.status = status
        repo.add(term)
    repo.commit()
    return jsonify({"status": status, "count": len(ids)})


@bp.route("/terms/<int:term_id>/image", methods=["POST"])
def upload_image(term_id):
    "Attach an uploaded picture to a term (replaces the current one)."
    dbterm = db.session.get(DBTerm, term_id)
    upload = request.files.get("file")
    if dbterm is None or upload is None:
        return jsonify({"error": "A term and a file are required"}), 400
    ext = os.path.splitext(upload.filename or "")[1].lower()
    if ext not in IMAGE_TYPES:
        return jsonify({"error": "Only png, jpg, gif and webp pictures are accepted"}), 400
    data = upload.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        return jsonify({"error": "Picture is larger than 5 MB"}), 400
    folder = os.path.join(current_app.env_config.userimagespath, str(dbterm.language.id))
    os.makedirs(folder, exist_ok=True)
    name = f"{term_id}-{uuid.uuid4().hex[:8]}{ext}"
    with open(os.path.join(folder, name), "wb") as f:
        f.write(data)
    dbterm.set_current_image(name)
    db.session.add(dbterm)
    db.session.commit()
    return jsonify({"image": _image_url(dbterm)})


@bp.route("/terms/<int:term_id>/image", methods=["DELETE"])
def delete_image(term_id):
    "Remove the term's picture (the file stays on disk)."
    dbterm = db.session.get(DBTerm, term_id)
    if dbterm is None:
        return jsonify({"error": "No such term"}), 404
    dbterm.set_current_image(None)
    db.session.add(dbterm)
    db.session.commit()
    return jsonify({"image": None})
