"""
JSON API for generating a book's audio.

    POST /ocarina/api/books/<id>/audio            start a job (adds a version; never replaces yours)
    POST /ocarina/api/books/<id>/audio/upload     attach your own audio file (form field "audio")
    GET  /ocarina/api/books/<id>/audio/options    what would voice this book, and what can be chosen instead
    GET  /ocarina/api/books/<id>/audio/sentences  sentence start times
"""

import json
import os

from flask import Blueprint, current_app, jsonify, request

from lute.book.service import Service
from lute.db import db
from lute.models.repositories import BookRepository
from ocarina import audio_versions, prefs
from ocarina.api import jobs
from ocarina.api.common import ALLOWED_AUDIO_EXTENSIONS
from ocarina.tts import models as model_files
from ocarina.tts.book_audio import (
    generate_book_audio,
    is_ocarina_audio,
    timings_path,
    tts_lang,
)
from ocarina.tts.cache import SentenceCache
from ocarina.tts import voices
from ocarina.tts.supervisor import Supervisor

bp = Blueprint("ocarina_audio", __name__, url_prefix="/ocarina/api")


def _uses_real_engine(app):
    "False when tests swap in the fake engine, which needs no model files."
    return "OCARINA_TTS_ENGINE" not in app.config


def _run_job(app, job, check, book_id, model, voice, pause, ref_text=None, voice_id=None):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """
    Queued job: generate the audio and add it to the book as a new version (selected). Nothing the book
    already has is touched, except a generated version made with exactly the same model, voice and pause,
    which this one replaces. Finished sentences stay cached if the job is cancelled.
    """
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
            audio_versions.sync(book, cfg.useraudiopath)  # audio from before versions becomes one first
            name = generate_book_audio(
                book, supervisor, cache, model["id"], cfg.useraudiopath, voice, pause, progress, ref_text
            )
            same = audio_versions.find_same_generated(book, model["id"], voice_id, pause)
            existing = [v["label"] for v in audio_versions.list_versions(book, cfg.useraudiopath)]
            voice_name = next((v["name"] for v in voices.list_voices(cfg.datapath) if v["id"] == voice_id), voice_id)
            label = f"{model['name']} · {voice_name}"
            if any(e == label or e.startswith(label + " · pause") for e in existing if not same or e != label):
                label += f" · pause {pause:.1f} s"
            audio_versions.add(book, name, audio_versions.GENERATED, label, model["id"], voice_id, pause)
            if same:
                audio_versions.remove(book, same.BaID, cfg.useraudiopath)
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
    saved = prefs.load(prefs.path_for(cfg.datapath))
    try:
        code = tts_lang(book.language)
    except ValueError:
        code = None
    preferred = saved.get(f"model.{code}") if code else None
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
    voice_id = body.get("voice") or saved.get(f"voice.{code}") or voices.default_voice_id(code)
    voice = voices.path_of(cfg.datapath, voice_id)
    if voice is None:
        if body.get("voice"):
            return jsonify({"error": "Voice not found"}), 400
        voice_id = voices.default_voice_id(code)  # the chosen voice was deleted: use the default
        voice = voices.path_of(cfg.datapath, voice_id)
    if jobs.active(kind="audio", book_id=book_id):
        return (
            jsonify({"error": "Audio for this book is already queued or running", "code": "already_queued"}),
            409,
        )
    pause = float(body.get("pause", 0.5))
    ref_text = voices.transcript_of(cfg.datapath, voice_id)
    job = jobs.submit(
        "audio",
        lambda job, check: _run_job(app, job, check, book_id, model, voice, pause, ref_text, voice_id),
        book_id=book_id,
        title=book.title,
    )
    return jsonify(job), 202


@bp.route("/books/<int:book_id>/audio/upload", methods=["POST"])
def upload_audio(book_id):
    "Add an audio file of the user's own as a new version of the book's audio (and select it). Nothing is replaced."
    book = BookRepository(db.session).find(book_id)
    if book is None:
        return jsonify({"error": "No such book"}), 404
    audio = request.files.get("audio")
    if not audio or not audio.filename:
        return jsonify({"error": "Choose an audio file"}), 400
    if audio.filename.rsplit(".", 1)[-1].lower() not in ALLOWED_AUDIO_EXTENSIONS:
        return jsonify({"error": "Audio must be one of: " + ", ".join(ALLOWED_AUDIO_EXTENSIONS)}), 400
    if jobs.active(kind="audio", book_id=book_id):
        return jsonify({"error": "Audio for this book is being generated. Cancel it first."}), 409
    audio_dir = current_app.env_config.useraudiopath
    audio_versions.sync(book, audio_dir)  # what the book has now becomes a version before the new one is selected
    filename = Service().save_audio_file(audio)
    label = os.path.splitext(os.path.basename(audio.filename))[0].strip()[:60] or "Original"
    version_id = audio_versions.add(book, filename, audio_versions.OWN, label)
    return jsonify({"audio_filename": filename, "versionId": version_id}), 201


@bp.route("/books/<int:book_id>/audio/options", methods=["GET"])
def audio_options(book_id):
    """
    The model and voice that would voice this book (the language's choice in Settings, else the first
    installed model), and the models and voices that can be picked for one generation instead.
    """
    book = BookRepository(db.session).find(book_id)
    if book is None:
        return jsonify({"error": "No such book"}), 404
    try:
        code = tts_lang(book.language)
    except ValueError:
        return jsonify({"error": f"Ocarina can't make audio for {book.language.name} yet", "code": "unsupported_language"}), 400
    datapath = current_app.env_config.datapath
    saved = prefs.load(prefs.path_for(datapath))
    default_model = model_files.choose_model(None, saved.get(f"model.{code}"))
    voice_list = voices.list_voices(datapath)
    voice_id = saved.get(f"voice.{code}") or voices.default_voice_id(code)
    default_voice = next((v for v in voice_list if v["id"] == voices.LEGACY_IDS.get(voice_id, voice_id)), voice_list[0])
    return jsonify(
        {
            "language": code,
            "defaultModel": default_model["id"],
            "defaultVoice": default_voice["id"],
            "models": [
                {"id": m["id"], "name": m["name"], "installed": model_files.is_installed(m), "custom": bool(m.get("custom"))}
                for m in model_files.load_catalog()
                if code in m.get("languages", [])
            ],
            "voices": [{"id": v["id"], "name": v["name"], "builtin": v["builtin"]} for v in voice_list],
        }
    )


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
