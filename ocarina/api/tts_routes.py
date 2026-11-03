"""
JSON API for generating book audio.

    GET  /ocarina/api/tts/models                 model catalog
    POST /ocarina/api/books/<id>/audio           start a job (one at a time)
    GET  /ocarina/api/jobs/<job_id>              job progress
    GET  /ocarina/api/books/<id>/audio/sentences sentence start times
"""

import json
import os
import threading
import uuid

from flask import Blueprint, current_app, jsonify, request

from lute.db import db
from lute.models.repositories import BookRepository
from ocarina.tts.book_audio import (
    generate_book_audio,
    is_ocarina_audio,
    timings_path,
)
from ocarina.tts.cache import SentenceCache
from ocarina.tts.service import DEFAULT_VOICE
from ocarina.tts.supervisor import Supervisor

bp = Blueprint("ocarina_tts", __name__, url_prefix="/ocarina/api")

CATALOG = os.path.join(os.path.dirname(__file__), "..", "tts", "catalog.json")

_jobs = {}
_lock = threading.Lock()


def _catalog():
    with open(CATALOG, encoding="utf-8") as f:
        return json.load(f)["models"]


def _running_job():
    return next((j for j in _jobs.values() if j["state"] == "running"), None)


def _run_job(app, job, book_id, model, voice, pause):
    "Background thread: generate and attach the audio."
    cfg = app.env_config
    engine = app.config.get("OCARINA_TTS_ENGINE", model["engine"])
    supervisor = Supervisor(engine)
    cache = SentenceCache(os.path.join(cfg.datapath, "tts_cache"))

    def progress(done, total):
        job["done"], job["total"] = done, total

    with app.app_context():
        try:
            book = BookRepository(db.session).find(book_id)
            old = book.audio_filename
            name = generate_book_audio(
                book, supervisor, cache, model["id"], cfg.useraudiopath, voice, pause, progress
            )
            book.audio_filename = name
            book.audio_current_pos = 0
            book.audio_bookmarks = None
            db.session.add(book)
            db.session.commit()
            if old and is_ocarina_audio(cfg.useraudiopath, old):
                for suffix in ("", ".sentences.json"):
                    p = os.path.join(cfg.useraudiopath, old + suffix)
                    if os.path.exists(p):
                        os.remove(p)
            job["audio_filename"] = name
            job["state"] = "done"
        except Exception as e:  # pylint: disable=broad-exception-caught
            db.session.rollback()
            job["state"], job["error"] = "error", f"{type(e).__name__}: {e}"
        finally:
            supervisor.unload()


@bp.route("/tts/models", methods=["GET"])
def models():
    "The model catalog."
    return jsonify(_catalog())


@bp.route("/books/<int:book_id>/audio", methods=["POST"])
def start_audio(book_id):
    "Start generating audio for a book; returns the job."
    body = request.get_json(silent=True) or {}
    book = BookRepository(db.session).find(book_id)
    if book is None:
        return jsonify({"error": "No such book"}), 404
    cfg = current_app.env_config
    if book.audio_filename and not is_ocarina_audio(cfg.useraudiopath, book.audio_filename):
        if not body.get("replace"):
            return (
                jsonify(
                    {
                        "error": "Book has its own audio. Send replace=true to overwrite it.",
                        "code": "has_user_audio",
                    }
                ),
                409,
            )
    model = next(
        (m for m in _catalog() if m["id"] == body.get("model", _catalog()[0]["id"])), None
    )
    if model is None:
        return jsonify({"error": "Unknown model"}), 400
    voice = body.get("voice") or DEFAULT_VOICE
    if not os.path.exists(voice):
        return jsonify({"error": "Voice file not found"}), 400
    with _lock:
        if _running_job() is not None:
            return jsonify({"error": "Another audio job is running"}), 409
        job = {
            "id": uuid.uuid4().hex,
            "book_id": book_id,
            "state": "running",
            "done": 0,
            "total": 0,
        }
        _jobs[job["id"]] = job
    # pylint: disable=protected-access
    app = current_app._get_current_object()
    threading.Thread(
        target=_run_job,
        args=(app, job, book_id, model, voice, float(body.get("pause", 0.5))),
        daemon=True,
    ).start()
    return jsonify(job), 202


@bp.route("/jobs/<job_id>", methods=["GET"])
def job_status(job_id):
    "Progress of a job."
    job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "No such job"}), 404
    return jsonify(job)


@bp.route("/books/<int:book_id>/audio/sentences", methods=["GET"])
def sentence_timings(book_id):
    "Sentence start times for the book's generated audio."
    book = BookRepository(db.session).find(book_id)
    if book is None or not book.audio_filename:
        return jsonify({"error": "No audio"}), 404
    path = timings_path(os.path.join(current_app.env_config.useraudiopath, book.audio_filename))
    if not os.path.exists(path):
        return jsonify({"error": "Audio has no sentence timings"}), 404
    with open(path, encoding="utf-8") as f:
        return jsonify(json.load(f))
