"""
JSON API for adding a book.

    POST /ocarina/api/books/extract  text of an uploaded file (txt, epub, pdf, srt, vtt), of a web page or of a YouTube video
                                     ({"url": ..., "languageId", "keepAudio"}); nothing is saved. A video that has captions
                                     answers at once; one that must be transcribed answers 202 with a job (state done: its
                                     "result" holds the same fields; "audioToken" is the video's sound when it was asked for)
    POST /ocarina/api/books          save a book (form fields: title, languageId, text,
                                     sourceUri, optional audio file)

Reading the file formats and the web page is Lute's own code (lute/book/service.py).
"""

import json
import os
import re
import uuid

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text as sql

from lute.book.model import Book
from lute.book.service import BookImportException, FileTextExtraction, Service
from lute.db import db
from lute.models.language import Language
from lute.models.repositories import BookRepository
from ocarina import audio_versions, importer, transcribe, video, youtube
from ocarina.api import jobs
from ocarina.tts.book_audio import tts_lang
from ocarina.api.common import ALLOWED_AUDIO_EXTENSIONS

bp = Blueprint("ocarina_book_import", __name__, url_prefix="/ocarina/api")

MAX_TITLE = 200  # the size of the title column
MAX_SOURCE = 1000
PDF_NOTE = "PDF text can be inaccurate because of how PDFs are encoded. Check it before saving."


def _error(message, status=400, **extra):
    return jsonify({"error": message, **extra}), status


def _language_code(language_id):
    "The two-letter code of a language, for the video's captions; None when it is unknown (the video's own language is used)."
    language = db.session.get(Language, language_id) if isinstance(language_id, int) else None
    try:
        return tts_lang(language) if language else None
    except ValueError:
        return None


def _imported(got, audio_token=None):
    return {
        "title": got.title,
        "text": got.text,
        "sourceUri": got.source_uri,
        "note": got.note,
        "audioToken": audio_token,
        "videoId": got.video_id,
        "anchors": got.anchors,
    }


def _temp_dir(app):
    path = os.path.join(app.env_config.datapath, "temp")
    os.makedirs(path, exist_ok=True)
    return path


def _extract_url(url, code, keep_audio):
    "A web page now; a video with captions now; a video to transcribe (or to keep the sound of) as a job."
    url = importer.check_url(url)
    if not importer.is_youtube(url):
        return jsonify(_imported(importer.from_web(url)))
    app = current_app._get_current_object()  # pylint: disable=protected-access
    run_whisper = transcribe.transcriber(app.config)
    if not keep_audio:
        got = youtube.captions_only(url, code)
        if got is not None and not (got.automatic and run_whisper):  # automatic captions have no punctuation: Whisper does better
            return jsonify(_imported(got))
    if run_whisper is None and not keep_audio:
        model = transcribe.model()
        return (
            jsonify(
                {
                    "error": "This video has no captions in this language. Download the transcription model in Settings to transcribe it on this Mac.",
                    "code": "model_not_installed",
                    "model": model["id"] if model else None,
                }
            ),
            409,
        )
    if jobs.active(kind="import"):
        return _error("A video is already being imported.", 409, code="already_queued")

    def run(job, check):
        def progress(message):
            job["message"] = message

        got = importer.import_url(url, code, progress=progress, keep_audio=keep_audio, check=check, transcribe=run_whisper)
        token = None
        if got.audio_path:
            token = f"{uuid.uuid4().hex}{os.path.splitext(got.audio_path)[1]}"
            os.replace(got.audio_path, os.path.join(_temp_dir(app), token))
        job["result"] = _imported(got, token)

    job = jobs.submit("import", run, title=url)
    return jsonify(job), 202


@bp.route("/books/extract", methods=["POST"])
def extract():
    "Text of an uploaded file or a web page, for the user to check before saving."
    try:
        upload = request.files.get("file")
        if upload:
            name = upload.filename or ""
            content = FileTextExtraction().get_file_content(name, upload.stream)
            title = os.path.splitext(os.path.basename(name))[0]
            note = PDF_NOTE if name.lower().endswith(".pdf") else None
            return jsonify({"title": title, "text": content, "sourceUri": "", "note": note})
        body = request.get_json(silent=True) or {}
        url = (body.get("url") or "").strip()
        if not url.startswith(("http://", "https://")) and not url.startswith(("www.", "youtu")):
            return _error("Choose a file, or give a web address starting with http:// or https://")
        return _extract_url(url, _language_code(body.get("languageId")), bool(body.get("keepAudio")))
    except importer.ImportFailed as e:
        return _error(str(e))
    except BookImportException as e:
        return _error(e.message)
    except ValueError as e:  # an unknown file extension
        return _error(str(e))


@bp.route("/books", methods=["POST"])
def create_book():
    "Save a new book (and its own audio file, if one is sent); returns its id."
    form = request.form
    title = form.get("title", "").strip()
    body = form.get("text", "").strip()
    try:
        language_id = int(form.get("languageId", ""))
    except ValueError:
        return _error("Choose a language")
    if not title or len(title) > MAX_TITLE:
        return _error(f"The title is required and at most {MAX_TITLE} characters")
    if not body:
        return _error("The text is empty")
    if len(form.get("sourceUri", "")) > MAX_SOURCE:
        return _error(f"The source address is at most {MAX_SOURCE} characters")
    known = db.session.execute(
        sql("select 1 from languages where LgID = :i"), {"i": language_id}
    ).first()
    if not known:
        return _error("Unknown language")
    if BookRepository(db.session).find_by_title(title, language_id):
        return _error("A book with this title already exists in this language", 409)

    book = Book()
    book.language_id, book.title, book.text = language_id, title, body
    book.source_uri = form.get("sourceUri", "").strip() or None
    audio = request.files.get("audio")
    token = form.get("importAudio", "")
    kept = None
    if token:
        if not re.fullmatch(r"[0-9a-f]{32}\.[A-Za-z0-9]{2,5}", token):
            return _error("That sound is not available any more.")
        kept = os.path.join(current_app.env_config.datapath, "temp", token)
        if not os.path.exists(kept):
            return _error("That sound is not available any more. Get the text again.")
    if kept:
        book.audio_stream, book.audio_stream_filename = open(kept, "rb"), f"{title[:60]}{os.path.splitext(kept)[1]}"  # pylint: disable=consider-using-with
    elif audio and audio.filename:
        if audio.filename.rsplit(".", 1)[-1].lower() not in ALLOWED_AUDIO_EXTENSIONS:
            return _error("Audio must be one of: " + ", ".join(ALLOWED_AUDIO_EXTENSIONS))
        book.audio_stream, book.audio_stream_filename = audio.stream, audio.filename
    try:
        saved = Service().import_book(book, db.session)
    except BookImportException as e:
        db.session.rollback()
        return _error(e.message)
    if kept:
        book.audio_stream.close()
        os.remove(kept)
    if form.get("videoId"):
        try:
            video.save(saved.id, form["videoId"], json.loads(form.get("videoAnchors") or "[]"))
        except ValueError:
            pass  # the book is saved; it just has no video to play
    audio_versions.sync(saved, current_app.env_config.useraudiopath)  # an audio file sent with the book is its first version
    return jsonify({"id": saved.id}), 201
