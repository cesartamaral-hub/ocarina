"""
JSON API for reference voices and previews.

    GET    /ocarina/api/tts/voices                 the built-in voice and your own
    POST   /ocarina/api/tts/voices                 add a voice from a clip (form: clip, optional name and transcript)
    DELETE /ocarina/api/tts/voices/<id>            remove one of your voices
    POST   /ocarina/api/tts/voices/preview         say a sample sentence in a voice (a job)
    GET    /ocarina/api/tts/previews/<name>        a finished preview (wav)
"""

import os
import re
import shutil
import uuid

from flask import Blueprint, current_app, jsonify, request, send_file

from ocarina import prefs
from ocarina.api import jobs
from ocarina.tts import models as model_files
from ocarina.tts import voices
from ocarina.tts.cache import SentenceCache
from ocarina.tts.service import synthesize_text_sentences
from ocarina.tts.supervisor import Supervisor

bp = Blueprint("ocarina_voices", __name__, url_prefix="/ocarina/api")

KEPT_PREVIEWS = 20
PREVIEW_NAME = re.compile(r"^preview_[0-9a-f]{32}\.wav$")
MAX_PREVIEW_TEXT = 300


def _previews_dir(cfg):
    return os.path.join(cfg.datapath, "temp", "previews")


def _prune_previews(folder):
    files = sorted((os.path.join(folder, f) for f in os.listdir(folder)), key=os.path.getmtime)
    for old in files[:-KEPT_PREVIEWS]:
        os.remove(old)


def _run_preview(app, job, check, model, language, voice_path, text, ref_text):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    "Queued job: say the text once and keep the wav for the page to play."
    cfg = app.env_config
    check()
    if "OCARINA_TTS_ENGINE" not in app.config and not model_files.is_installed(model):
        raise RuntimeError(f"{model['name']} is not installed.")
    engine = app.config.get("OCARINA_TTS_ENGINE", model["engine"])
    supervisor = Supervisor(engine, repo=model["repositories"][0]["id"])
    cache = SentenceCache(os.path.join(cfg.datapath, "tts_cache"))
    try:
        (made,) = synthesize_text_sentences(supervisor, cache, model["id"], [text], language, voice_path, ref_text=ref_text)
    finally:
        supervisor.unload()
    folder = _previews_dir(cfg)
    os.makedirs(folder, exist_ok=True)
    name = f"preview_{uuid.uuid4().hex}.wav"
    shutil.copyfile(made, os.path.join(folder, name))
    _prune_previews(folder)
    job["preview"] = name


@bp.route("/tts/voices", methods=["GET"])
def list_voices():
    "The built-in voice and the user's own."
    return jsonify(voices.list_voices(current_app.env_config.datapath))


@bp.route("/tts/voices", methods=["POST"])
def add_voice():
    "Add a voice from an uploaded clip."
    clip = request.files.get("clip")
    if not clip or not clip.filename:
        return jsonify({"error": "Choose an audio clip"}), 400
    try:
        voice = voices.add_voice(
            current_app.env_config.datapath, clip.filename, clip.stream, request.form.get("name"), request.form.get("transcript")
        )
    except voices.VoiceError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(voice), 201


@bp.route("/tts/voices/<voice_id>", methods=["DELETE"])
def delete_voice(voice_id):
    "Remove one of the user's voices (books keep their audio)."
    if not voices.delete_voice(current_app.env_config.datapath, voice_id):
        return jsonify({"error": "No such voice (the built-in one can't be removed)"}), 404
    return jsonify({"deleted": voice_id})


@bp.route("/tts/voices/preview", methods=["POST"])
def preview():
    "Say a sample sentence in the chosen voice and language."
    body = request.get_json(silent=True) or {}
    language = body.get("language")
    if language not in voices.SAMPLE_TEXT:
        return jsonify({"error": "Choose a language"}), 400
    cfg = current_app.env_config
    saved = prefs.load(prefs.path_for(cfg.datapath))
    voice_id = body.get("voice") or saved.get(f"voice.{language}") or voices.default_voice_id(language)
    voice_path = voices.path_of(cfg.datapath, voice_id)
    if voice_path is None:
        return jsonify({"error": "Voice not found"}), 400
    ref_text = voices.transcript_of(cfg.datapath, voice_id)
    text = (body.get("text") or "").strip() or voices.SAMPLE_TEXT[language]
    if len(text) > MAX_PREVIEW_TEXT:
        return jsonify({"error": f"The sample is at most {MAX_PREVIEW_TEXT} characters"}), 400
    model = model_files.choose_model(body.get("model"), saved.get(f"model.{language}"))
    if model is None:
        return jsonify({"error": "Unknown model"}), 400
    # pylint: disable=protected-access
    app = current_app._get_current_object()
    if "OCARINA_TTS_ENGINE" not in app.config and not model_files.is_installed(model):
        return jsonify({"error": f"{model['name']} is not downloaded yet. Download it in Settings.", "code": "model_not_installed"}), 409
    job = jobs.submit(
        "preview",
        lambda job, check: _run_preview(app, job, check, model, language, voice_path, text, ref_text),
    )
    return jsonify(job), 202


@bp.route("/tts/previews/<name>", methods=["GET"])
def get_preview(name):
    "A finished preview."
    path = os.path.join(_previews_dir(current_app.env_config), name)
    if not PREVIEW_NAME.match(name) or not os.path.isfile(path):
        return jsonify({"error": "No such preview"}), 404
    return send_file(path, mimetype="audio/wav")
