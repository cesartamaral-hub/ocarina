"""
JSON API for hearing a word or a few words (see ocarina/pronounce.py).

    POST /ocarina/api/pronounce            {"text", "languageId", "source"?}: the audio's address, the source that made it and a note
    GET  /ocarina/api/pronounce/audio/<f>  the audio file
"""

import os
import re

from flask import Blueprint, current_app, jsonify, request, send_file

from lute.db import db
from lute.models.language import Language
from ocarina import prefs, pronounce
from ocarina.api import jobs
from ocarina.tts.book_audio import tts_lang

bp = Blueprint("ocarina_pronounce", __name__, url_prefix="/ocarina/api")

FILE = re.compile(r"^[0-9a-f]{64}\.(wav|mp3)$")
TYPES = {"wav": "audio/wav", "mp3": "audio/mpeg"}
VOICE_JOBS = ("audio", "preview")  # these use the speech model; two copies of it would not fit in memory comfortably


@bp.route("/pronounce", methods=["POST"])
def say():
    "Make (or find) the audio of the text, in the language."
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    language = db.session.get(Language, body.get("languageId")) if isinstance(body.get("languageId"), int) else None
    if not text or language is None:
        return jsonify({"error": "Choose some text in a language."}), 400
    try:
        code = tts_lang(language)
    except ValueError:
        return jsonify({"error": f"Ocarina cannot say {language.name} yet."}), 400
    cfg = current_app.env_config
    saved = prefs.load(prefs.path_for(cfg.datapath))
    busy = any(jobs.active(kind=k) for k in VOICE_JOBS)
    try:
        path, source, note = pronounce.say(cfg, current_app.config, text, code, body.get("source"), saved, busy)
    except pronounce.Unavailable as e:
        return jsonify({"error": str(e)}), 503
    name = os.path.basename(path)
    return jsonify({"url": f"/ocarina/api/pronounce/audio/{name}", "source": source, "note": note})


@bp.route("/pronounce/audio/<name>", methods=["GET"])
def audio(name):
    "A finished audio file."
    if not FILE.match(name):
        return jsonify({"error": "No such audio"}), 404
    folder = os.path.join(pronounce.cache_dir(current_app.env_config.datapath), name[:2])
    path = os.path.join(folder, name)
    if not os.path.isfile(path):
        return jsonify({"error": "No such audio"}), 404
    return send_file(path, mimetype=TYPES[name.rsplit(".", 1)[1]])
