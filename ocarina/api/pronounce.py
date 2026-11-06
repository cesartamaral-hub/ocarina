"""
JSON API for hearing a word or a few words (see ocarina/pronounce.py).

    POST /ocarina/api/pronounce            {"text", "languageId", "source"?}: the audio's address, the source that made it and a note
    GET  /ocarina/api/pronounce/audio/<f>  the audio file
    POST /ocarina/api/pronounce/system-voices/preview  {"name"}: one Mac voice saying its sample sentence
    POST /ocarina/api/pronounce/open-voice-settings    open System Settings at Spoken Content (to add Mac voices)
    GET  /ocarina/api/pronounce/system-voices  the voices installed on this Mac per library language (best first) and the one in use
"""

import os
import re

from flask import Blueprint, current_app, jsonify, request, send_file

from lute.db import db
from lute.models.language import Language
from ocarina import prefs, pronounce, translate
from ocarina.api import jobs
from ocarina.tts.book_audio import tts_lang

bp = Blueprint("ocarina_pronounce", __name__, url_prefix="/ocarina/api")

FILE = re.compile(r"^[0-9a-f]{64}\.(wav|mp3)$")
TYPES = {"wav": "audio/wav", "mp3": "audio/mpeg"}
VOICE_JOBS = ("audio", "preview")  # these use the speech model; two copies of it would not fit in memory comfortably


def _code(language):
    "Two-letter code of a Lute language: any language Ocarina knows by name, not only the ones with voice models."
    try:
        return tts_lang(language)
    except ValueError:
        return translate.code_for(language.name)


@bp.route("/pronounce/system-voices", methods=["GET"])
def system_voices():
    "The voices of this Mac for each language in the library, best first, and the one in use."
    saved = prefs.load(prefs.path_for(current_app.env_config.datapath))
    out = []
    for language in db.session.query(Language).order_by(Language.name).all():
        code = _code(language)
        found = pronounce.mac_voices(code) if code else []
        chosen = pronounce.mac_voice(code, saved.get(f"systemvoice.{code}")) if code else None
        out.append({"languageId": language.id, "language": language.name, "code": code, "chosen": chosen, "voices": [{k: v[k] for k in ("name", "quality", "novelty")} for v in found]})
    return jsonify(out)


@bp.route("/pronounce/system-voices/preview", methods=["POST"])
def preview_system_voice():
    "Hear one installed Mac voice say its sample sentence."
    name = (request.get_json(silent=True) or {}).get("name", "")
    try:
        path = pronounce.preview_system(current_app.env_config, name)
    except pronounce.Unavailable as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"url": f"/ocarina/api/pronounce/audio/{os.path.basename(path)}"})


@bp.route("/pronounce/open-voice-settings", methods=["POST"])
def open_voice_settings():
    "Open System Settings where macOS voices are added (Spoken Content)."
    if not pronounce.open_voice_settings():
        return jsonify({"error": "Ocarina could not open System Settings. Open it, then Accessibility → Spoken Content → System Voice → Manage Voices."}), 501
    return jsonify({"ok": True})


@bp.route("/pronounce", methods=["POST"])
def say():
    "Make (or find) the audio of the text, in the language."
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    language = db.session.get(Language, body.get("languageId")) if isinstance(body.get("languageId"), int) else None
    if not text or language is None:
        return jsonify({"error": "Choose some text in a language."}), 400
    code = _code(language)
    if code is None:
        return jsonify({"error": f"Ocarina does not know which language code {language.name} has, so it cannot pick a voice for it."}), 400
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
