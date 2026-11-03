"""
JSON API for generating a book's audio.

    POST /ocarina/api/books/<id>/audio            start a job
    GET  /ocarina/api/books/<id>/audio/sentences  sentence start times
"""

import json
import os

from flask import Blueprint, current_app, jsonify, request

from lute.db import db
from lute.models.repositories import BookRepository
from ocarina import prefs
from ocarina.api import jobs
from ocarina.tts import models as model_files
from ocarina.tts.book_audio import (
    generate_book_audio,
    is_ocarina_audio,
    timings_path,
    tts_lang,
)
from ocarina.tts.cache import SentenceCache
from ocarina.tts.service import DEFAULT_VOICE
from ocarina.tts.supervisor import Supervisor

bp = Blueprint("ocarina_audio", __name__, url_prefix="/ocarina/api")


def _uses_real_engine(app):
    "False when tests swap in the fake engine, which needs no model files."
    return "OCARINA_TTS_ENGINE" not in app.config


def _run_job(app, job, check, book_id, model, voice, pause):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    "Queued job: generate and attach the audio. Finished sentences stay cached if it is cancelled."
    cfg = app.env_config
    engine = app.config.get("OCARINA_TTS_ENGINE", model["engine"])
    supervisor = Supervisor(engine, repo=model["repositories"][0]["id"])
    cache = SentenceCache(os.path.join(cfg.datapath, "tts_cache"))

    def progress(done, total):
        check()
        job["done"], job["total"] = done, total

    check()
    if _uses_real_engine(app) and not model_files.is_installed(model):
        raise RuntimeError(f"{model['name']} is not installed.")
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
        except Exception:
            db.session.rollback()
            raise
        finally:
            supervisor.unload()


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
    saved = prefs.load(prefs.path_for(cfg.datapath))
    try:
        preferred = saved.get(f"model.{tts_lang(book.language)}")
    except ValueError:
        preferred = None
    model = model_files.choose_model(body.get("model"), preferred)
    if model is None:
        return jsonify({"error": "Unknown model"}), 400
    # pylint: disable=protected-access
    app = current_app._get_current_object()
    if _uses_real_engine(app) and not model_files.is_installed(model):
        return (
            jsonify(
                {
                    "error": f"{model['name']} is not downloaded yet. Download it in Settings.",
                    "code": "model_not_installed",
                    "model": model["id"],
                }
            ),
            409,
        )
    voice = body.get("voice") or DEFAULT_VOICE
    if not os.path.exists(voice):
        return jsonify({"error": "Voice file not found"}), 400
    if jobs.active(kind="audio", book_id=book_id):
        return (
            jsonify({"error": "Audio for this book is already queued or running", "code": "already_queued"}),
            409,
        )
    pause = float(body.get("pause", 0.5))
    job = jobs.submit(
        "audio",
        lambda job, check: _run_job(app, job, check, book_id, model, voice, pause),
        book_id=book_id,
    )
    return jsonify(job), 202


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
