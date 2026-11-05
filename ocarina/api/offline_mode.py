"""
JSON API for Work offline (see ocarina/offline.py).

    GET /ocarina/api/offline   {offline, languages: [{code, name, dictionary, translation, voice}], audioSync}
                               the switch, and what each language of the library has on this Mac for working without the internet
    PUT /ocarina/api/offline   {"offline": true | false}
"""

from flask import Blueprint, current_app, jsonify, request

from lute.db import db
from lute.models.language import Language
from ocarina import offline, prefs, translate
from ocarina.audio_sync import ALIGNER_ID
from ocarina.dictionaries import registry
from ocarina.tts import models as model_files

bp = Blueprint("ocarina_offline_mode", __name__, url_prefix="/ocarina/api")


def _installed(models):
    fake = current_app.config.get("OCARINA_TTS_ENGINE") is not None  # the tests use a fake engine: models count as downloaded
    return [m for m in models if fake or model_files.is_installed(m)]


def readiness(datapath):
    "What is on this Mac for each language of the library: a dictionary, a model that translates, a voice; and the model that syncs audio."
    translating = _installed(model_files.text_models())
    voices = _installed(model_files.speech_models())
    languages = []
    for language in db.session.query(Language).order_by(Language.name).all():
        code = translate.code_for(language.name)
        if code is None:
            continue
        packs = registry.active(datapath, code)
        speaking = [m for m in voices if code in m.get("languages", [])]
        languages.append(
            {
                "code": code,
                "name": language.name,
                "dictionary": {"ok": bool(packs), "names": [p.name for p in packs]},
                "translation": {"ok": bool(translating), "names": [m["name"] for m in translating]},
                "voice": {"ok": bool(speaking), "names": [m["name"] for m in speaking]},
            }
        )
    sync = model_files.find_model(ALIGNER_ID)
    return {"languages": languages, "audioSync": {"ok": bool(sync and _installed([sync])), "name": sync["name"] if sync else ""}}


@bp.route("/offline", methods=["GET"])
def get_offline():
    return jsonify({"offline": offline.is_on(), **readiness(current_app.env_config.datapath)})


@bp.route("/offline", methods=["PUT"])
def put_offline():
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get("offline"), bool):
        return jsonify({"error": "offline must be true or false"}), 400
    prefs.update(prefs.path_for(current_app.env_config.datapath), {offline.PREF: body["offline"]})
    return get_offline()
