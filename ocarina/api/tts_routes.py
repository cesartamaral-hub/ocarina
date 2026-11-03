"""
JSON API for generating book audio.

    GET  /ocarina/api/tts/models                 model catalog with install status
    POST /ocarina/api/tts/models/<id>/download   download a model (a job)
    DELETE /ocarina/api/tts/models/<id>          delete a model's files
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
from ocarina.tts import models as model_files
from ocarina.tts.book_audio import (
    generate_book_audio,
    is_ocarina_audio,
    timings_path,
)
from ocarina.tts.cache import SentenceCache
from ocarina.tts.service import DEFAULT_VOICE
from ocarina.tts.supervisor import Supervisor

bp = Blueprint("ocarina_tts", __name__, url_prefix="/ocarina/api")

_jobs = {}
_lock = threading.Lock()


def _catalog():
    return model_files.load_catalog()


def _uses_real_engine(app):
    "False when tests swap in the fake engine, which needs no model files."
    return "OCARINA_TTS_ENGINE" not in app.config


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


def _run_download(job, model):
    "Background thread: download a model's files."

    def progress(done, total):
        job["done"], job["total"] = done, total

    try:
        model_files.download(model, progress)
        job["state"] = "done"
    except Exception as e:  # pylint: disable=broad-exception-caught
        job["state"], job["error"] = "error", f"{type(e).__name__}: {e}"


def _new_job(kind, **fields):
    "Register a running job, or None if another one is already running."
    with _lock:
        if _running_job() is not None:
            return None
        job = {
            "id": uuid.uuid4().hex,
            "kind": kind,
            "state": "running",
            "done": 0,
            "total": 0,
            **fields,
        }
        _jobs[job["id"]] = job
        return job


@bp.route("/tts/models", methods=["GET"])
def models():
    "The model catalog, with whether each model is installed and its download size."
    active = _running_job()
    return jsonify(
        [
            {
                **m,
                "installed": model_files.is_installed(m),
                "sizeBytes": model_files.total_bytes(m),
                "downloadJob": active["id"]
                if active and active.get("model_id") == m["id"]
                else None,
            }
            for m in _catalog()
        ]
    )


@bp.route("/tts/models/<model_id>/download", methods=["POST"])
def download_model(model_id):
    "Start downloading a model; returns the job."
    model = model_files.find_model(model_id)
    if model is None:
        return jsonify({"error": "Unknown model"}), 404
    if model_files.is_installed(model):
        return jsonify({"error": "Model is already installed"}), 409
    job = _new_job("download", model_id=model_id, total=model_files.total_bytes(model))
    if job is None:
        return jsonify({"error": "Another job is running"}), 409
    threading.Thread(target=_run_download, args=(job, model), daemon=True).start()
    return jsonify(job), 202


@bp.route("/tts/models/<model_id>", methods=["DELETE"])
def delete_model(model_id):
    "Delete a model's files."
    model = model_files.find_model(model_id)
    if model is None:
        return jsonify({"error": "Unknown model"}), 404
    if _running_job() is not None:
        return jsonify({"error": "Another job is running"}), 409
    model_files.delete(model)
    return jsonify({"ok": True})


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
    model = model_files.find_model(body.get("model", _catalog()[0]["id"]))
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
    job = _new_job("audio", book_id=book_id)
    if job is None:
        return jsonify({"error": "Another job is running"}), 409
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
