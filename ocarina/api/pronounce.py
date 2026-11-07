"""
JSON API for hearing a word or a few words (see ocarina/pronounce.py).

    POST /ocarina/api/pronounce            {"text", "languageId", "source"?}: the audio's address, the source that made it and a note
    GET  /ocarina/api/pronounce/audio/<f>  the audio file
    POST /ocarina/api/pronounce/system-voices/preview  {"name"}: one Mac voice saying its sample sentence
    POST /ocarina/api/pronounce/open-voice-settings    open System Settings at Spoken Content (to add Mac voices)
    POST /ocarina/api/speak                {"text", "languageId", "rate"?}: speak it now with the Mac voice; answers {"finished"} when it is done (false when cut short)
    POST /ocarina/api/speak/stop           end what is being spoken
    GET  /ocarina/api/numbers/spoken?languageId=<id>&text=<digits>  {words, kind} for a text that is one number (kind: number, year, ordinal), else {words: null}
    GET  /ocarina/api/pronounce/system-voices  the voices installed on this Mac per library language (best first) and the one in use
"""

import os
import re

from flask import Blueprint, current_app, jsonify, request, send_file

from lute.db import db
from lute.models.language import Language
from ocarina import live_speech, numbers, prefs, pronounce, translate
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
        locale = translate.locale_of(language.name)
        found = pronounce.mac_voices(code, locale) if code else []
        chosen = pronounce.mac_voice(code, saved.get(f"systemvoice.{code}"), locale) if code else None
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
        path, source, note = pronounce.say(cfg, current_app.config, text, code, body.get("source"), saved, busy, translate.locale_of(language.name))
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


@bp.route("/speak", methods=["POST"])
def speak():
    "Read a sentence aloud now, with the Mac voice of its language. Returns when it is finished."
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    language = db.session.get(Language, body.get("languageId")) if isinstance(body.get("languageId"), int) else None
    if not text or language is None:
        return jsonify({"error": "Choose some text in a language."}), 400
    code = _code(language)
    saved = prefs.load(prefs.path_for(current_app.env_config.datapath))
    voice = pronounce.mac_voice(code, saved.get(f"systemvoice.{code}"), translate.locale_of(language.name)) if code else None
    if voice is None:
        return jsonify({"error": pronounce.NO_MAC_VOICE, "code": "no_mac_voice"}), 409
    rate = body.get("rate")
    wpm = int(175 * min(max(float(rate), 0.5), 2.5)) if isinstance(rate, (int, float)) else None  # 175 is the Mac's usual pace
    return jsonify({"finished": live_speech.speak(numbers.spoken(text, code), voice, wpm), "voice": voice})


@bp.route("/speak/stop", methods=["POST"])
def speak_stop():
    "End the sentence being read aloud."
    live_speech.stop()
    return jsonify({"ok": True})


@bp.route("/numbers/spoken", methods=["GET"])
def number_words():
    "A number written in digits, in words in the language of the book."
    language = db.session.get(Language, int(request.args["languageId"])) if request.args.get("languageId", "").isdigit() else None
    if language is None:
        return jsonify({"error": "Unknown language"}), 404
    code = _code(language)
    found = numbers.describe(request.args.get("text", ""), code) if code else None
    return jsonify(found or {"words": None, "kind": None})
