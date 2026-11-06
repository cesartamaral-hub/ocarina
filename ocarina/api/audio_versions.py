"""
JSON API for the audio versions of a book (your own recordings and generated audio, kept side by side).

    GET    /ocarina/api/books/<id>/audio/versions                     all versions; one is selected
    PUT    /ocarina/api/books/<id>/audio/versions/<version>/select    make it the book's audio
    PATCH  /ocarina/api/books/<id>/audio/versions/<version>           rename ({"label": ...})
    DELETE /ocarina/api/books/<id>/audio/versions/<version>           remove it (generated files are deleted,
                                                                      your own recording stays on disk)
    POST   /ocarina/api/books/<id>/audio/versions/<version>/sync      start a job that syncs your own recording with
                                                                      the text, so sentences can follow it ({"method": "aligner" (precise,
                                                                      needs the model) | "pauses" (approximate, no model)}; by default the
                                                                      aligner when it is installed, else the pauses)
    PUT    /ocarina/api/books/<id>/audio/versions/<version>/anchors   {"sentence", "time"}: pin a sentence start (time null removes the
                                                                      pin); the rest is fitted again (pause-synced versions only)
    POST   /ocarina/api/books/<id>/audio/versions/<version>/subtitles an SRT, WebVTT or LRC file ("file"): timings from its cues
Generating audio and uploading your own add versions (see audio.py).
"""

from flask import Blueprint, current_app, jsonify, request

from lute.db import db
from lute.models.repositories import BookRepository
from ocarina import audio_sync, audio_versions, pause_sync, subtitles
from ocarina.api import jobs
from ocarina.audio_sync import ALIGNER_ID
from ocarina.tts import models as model_files
from ocarina.tts.book_audio import tts_lang
from ocarina.tts.supervisor import Supervisor

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
    if jobs.active(kind="audio", book_id=book_id) or jobs.active(kind="sync", book_id=book_id):
        return jsonify({"error": "Audio for this book is being generated or synced. Cancel that first."}), 409
    removed = audio_versions.remove(book, version_id, _dir())
    if removed is None:
        return jsonify({"error": "No such audio version"}), 404
    return jsonify({"removed": removed, "versions": audio_versions.list_versions(book, _dir())})


def _run_sync(app, job, check, book_id, filename, model):
    "Queued job: align the recording with the book's text and write its timings."
    cfg = app.env_config
    engine = audio_sync.aligner_engine(app.config.get("OCARINA_TTS_ENGINE", model["engine"]))
    supervisor = Supervisor(engine, repo=model["repositories"][0]["id"], timeout=900)

    def progress(done, total):
        job["done"], job["total"] = done, total

    check()
    if "OCARINA_TTS_ENGINE" not in app.config and not model_files.is_installed(model):
        raise RuntimeError(f"{model['name']} is not installed.")
    with app.app_context():
        try:
            book = BookRepository(db.session).find(book_id)
            try:
                code = tts_lang(book.language)
            except ValueError:
                code = None
            job["phase"] = "aligning"
            suspect = audio_sync.sync_book_audio(book, cfg.useraudiopath, filename, supervisor, code, check, progress)
            job["suspect"] = len(suspect)
        finally:
            supervisor.unload()


def _run_sync_pauses(app, job, check, book_id, filename):
    "Queued job: match the recording's pauses to the book's sentences (no model) and write its timings."
    cfg = app.env_config
    with app.app_context():
        book = BookRepository(db.session).find(book_id)
        try:
            code = tts_lang(book.language)
        except ValueError:
            code = None
        job["phase"] = "finding pauses"
        suspect, how = pause_sync.sync_book_audio_pauses(book, cfg.useraudiopath, filename, code, None, check)
        job["suspect"], job["method"] = len(suspect), how


def queue_sync(book, row, method=None):
    """
    Queue the job that syncs one of the book's own recordings with its text. Returns (job, None), or (None, why) when it cannot be
    queued: {"code": "model_not_installed" | "already_queued" | "not_own", "error": message, "model": id}.
    """
    if row.BaKind != audio_versions.OWN:
        return None, {"code": "not_own", "error": "Audio made by Ocarina already follows the text."}
    if jobs.active(kind="sync", book_id=book.id) or jobs.active(kind="audio", book_id=book.id):
        return None, {"code": "already_queued", "error": "Audio for this book is already being generated or synced."}
    model = model_files.find_model(ALIGNER_ID)
    # pylint: disable=protected-access
    app = current_app._get_current_object()
    installed = "OCARINA_TTS_ENGINE" in app.config or model_files.is_installed(model)
    if method == "pauses" or (method is None and not installed):
        filename = row.BaFilename
        job = jobs.submit("sync", lambda job, check: _run_sync_pauses(app, job, check, book.id, filename), book_id=book.id, title=book.title, method="pauses")
        return job, None
    if not installed:
        return None, {"code": "model_not_installed", "error": f"{model['name']} is not downloaded yet. Download it in Settings.", "model": model["id"]}
    filename = row.BaFilename
    job = jobs.submit(
        "sync",
        lambda job, check: _run_sync(app, job, check, book.id, filename, model),
        book_id=book.id,
        title=book.title,
    )
    return job, None


def sync_new_audio(book, version_id):
    "Every recording added to a material is synced with its text: the answer for the page, {state: started | model_missing | busy}."
    row = audio_versions.find(book, version_id)
    if row is None:
        return None
    job, why = queue_sync(book, row)
    if job is not None:
        return {"state": "started", "job": job}
    if why["code"] == "model_not_installed":
        return {"state": "model_missing", "error": why["error"], "model": why.get("model")}
    return {"state": "busy", "error": why["error"]}


@bp.route("/books/<int:book_id>/audio/versions/<int:version_id>/sync", methods=["POST"])
def sync_version(book_id, version_id):
    "Start syncing one of your own recordings with the book's text; returns the job."
    book = _book(book_id)
    row = audio_versions.find(book, version_id) if book else None
    if row is None:
        return jsonify({"error": "No such audio version"}), 404
    method = (request.get_json(silent=True) or {}).get("method")
    if method not in (None, "aligner", "pauses"):
        return jsonify({"error": "Unknown sync method"}), 400
    job, why = queue_sync(book, row, method)
    if job is not None:
        return jsonify(job), 202
    status = {"not_own": 400, "already_queued": 409, "model_not_installed": 409}[why["code"]]
    return jsonify(why), status


def _info(book, version_id):
    "(row, timings info) of a version, or (None, None)."
    row = audio_versions.find(book, version_id) if book else None
    if row is None:
        return None, None
    from ocarina.tts.book_audio import timings_info  # pylint: disable=import-outside-toplevel

    return row, timings_info(_dir(), row.BaFilename)


@bp.route("/books/<int:book_id>/audio/versions/<int:version_id>/anchors", methods=["PUT"])
def set_anchor(book_id, version_id):
    "Pin one sentence's start to a time (or remove the pin) and fit the rest again."
    book = _book(book_id)
    row, info = _info(book, version_id)
    if row is None:
        return jsonify({"error": "No such audio version"}), 404
    if not info or info.get("method") not in ("pauses", "estimate"):
        return jsonify({"error": "Only a recording synced by its pauses can be adjusted this way. Sync it again with the quick method first."}), 409
    body = request.get_json(silent=True) or {}
    sentence, at = body.get("sentence"), body.get("time")
    if not isinstance(sentence, int) or sentence < 0 or (at is not None and not isinstance(at, (int, float))):
        return jsonify({"error": "Give a sentence number and a time in seconds (or null to remove the pin)"}), 400
    pins = {int(i): float(t) for i, t in (info.get("pins") or {}).items()}
    if at is None:
        pins.pop(sentence, None)
    else:
        pins[sentence] = float(at)
    from ocarina.audio_sync import SyncError  # pylint: disable=import-outside-toplevel

    try:
        suspect, how = pause_sync.sync_book_audio_pauses(book, _dir(), row.BaFilename, info.get("language"), pins)
    except SyncError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"pins": pins, "suspect": len(suspect), "method": how})


@bp.route("/books/<int:book_id>/audio/versions/<int:version_id>/subtitles", methods=["POST"])
def sync_from_subtitles(book_id, version_id):
    "Timings from a subtitle file (SRT, WebVTT, LRC) that goes with the recording."
    import json  # pylint: disable=import-outside-toplevel
    import os  # pylint: disable=import-outside-toplevel

    from ocarina.tts.book_audio import book_sentences, timings_path  # pylint: disable=import-outside-toplevel

    book = _book(book_id)
    row = audio_versions.find(book, version_id) if book else None
    if row is None:
        return jsonify({"error": "No such audio version"}), 404
    upload = request.files.get("file")
    if upload is None:
        return jsonify({"error": "Choose a subtitle file (.srt, .vtt or .lrc)."}), 400
    cues = subtitles.parse(upload.read().decode("utf-8-sig", errors="replace"))
    sentences = book_sentences(book)
    starts = subtitles.sentence_starts([s["text"] for s in sentences], cues) if cues and sentences else None
    if starts is None:
        return jsonify({"error": "The subtitles do not seem to match this text, or the file has no timed lines.", "code": "no_match"}), 400
    for s, start in zip(sentences, starts):
        s["start"] = start
    try:
        code = tts_lang(book.language)
    except ValueError:
        code = None
    with open(timings_path(os.path.join(_dir(), row.BaFilename)), "w", encoding="utf-8") as f:
        json.dump({"aligned": True, "aligner": "subtitles", "method": "subtitles", "approximate": True, "language": code, "sentences": sentences}, f, ensure_ascii=False)
    return jsonify(audio_versions.list_versions(book, _dir()))
