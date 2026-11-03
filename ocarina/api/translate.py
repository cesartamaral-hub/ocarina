"""
JSON API for translating a sentence (see ocarina/translate.py) and its settings.

    GET  /ocarina/api/translate/settings   provider, target language, whether a DeepL key is saved (never the key)
    PUT  /ocarina/api/translate/settings   change them; deeplKey saves a key, "" removes it
    POST /ocarina/api/translate            {languageId, text} -> {translation, provider, source, target, cached}
    POST /ocarina/api/translate/test       a trial translation with the current settings (asks the service for real)

Errors are {error, code}; code is one of offline, quota, bad_key, no_key, no_model, unsupported_language,
too_long, bad_input, failed.
"""

import re

from flask import Blueprint, current_app, jsonify, request

from lute.db import db
from lute.models.language import Language
from ocarina import keystore, prefs, translate
from ocarina.tts import models as model_files

bp = Blueprint("ocarina_translate", __name__, url_prefix="/ocarina/api")

STATUS = {"no_model": 400, "bad_input": 400, "too_long": 400, "unsupported_language": 400, "no_key": 400, "bad_key": 400, "quota": 429, "offline": 502, "failed": 502}
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _datapath():
    return current_app.env_config.datapath


def _settings():
    saved = prefs.load(prefs.path_for(_datapath()))
    provider = saved.get("translate.provider")
    target = saved.get("translate.target")
    if provider not in translate.PROVIDERS:
        # Not chosen yet: the model on this Mac once it is downloaded (private, no limits), else the free online service.
        provider = "local" if model_files.is_installed(model_files.find_model(translate.LOCAL_MODEL)) else "mymemory"
    return {
        "provider": provider,
        "target": target if target in translate.TARGETS else "en",
        "email": saved.get("translate.email") or "",
    }


def _settings_json():
    return {
        **_settings(),
        "hasDeeplKey": keystore.get(_datapath(), "deepl") is not None,
        "deeplKeyHint": keystore.hint(_datapath(), "deepl"),
        "providers": [{"id": k, **v} for k, v in translate.PROVIDERS.items()],
        "localModel": _local_model_json(),
        "targets": [{"code": k, "name": v} for k, v in translate.TARGETS.items()],
    }


def _local_model_json():
    model = model_files.find_model(translate.LOCAL_MODEL)
    return {"id": model["id"], "name": model["name"], "installed": model_files.is_installed(model), "sizeBytes": model_files.total_bytes(model)}


def _local_engine():
    "The tests use a fake engine for the local model, the way they do for the voices."
    return current_app.config.get("OCARINA_TTS_ENGINE")


def _failure(e):
    return jsonify({"error": str(e), "code": e.code}), STATUS.get(e.code, 502)


@bp.route("/translate/settings", methods=["GET"])
def get_settings():
    "How sentences are translated."
    return jsonify(_settings_json())


@bp.route("/translate/settings", methods=["PUT"])
def put_settings():
    "Change how sentences are translated."
    body = request.get_json(silent=True) or {}
    changes = {}
    if "provider" in body:
        if body["provider"] not in translate.PROVIDERS:
            return jsonify({"error": "Unknown translation service"}), 400
        changes["translate.provider"] = body["provider"]
    if "target" in body:
        if body["target"] not in translate.TARGETS:
            return jsonify({"error": "Unknown target language"}), 400
        changes["translate.target"] = body["target"]
    if "email" in body:
        email = (body["email"] or "").strip()
        if email and not EMAIL.match(email):
            return jsonify({"error": "That does not look like an email address"}), 400
        changes["translate.email"] = email
    if "deeplKey" in body:
        key = (body["deeplKey"] or "").strip()
        if key and (len(key) > 100 or re.search(r"\s", key)):
            return jsonify({"error": "That does not look like a DeepL API key"}), 400
        keystore.put(_datapath(), "deepl", key)
    if changes:
        prefs.update(prefs.path_for(_datapath()), changes)
    return jsonify(_settings_json())


@bp.route("/translate", methods=["POST"])
def translate_sentence():
    "Translate a sentence of a language into the target language."
    body = request.get_json(silent=True) or {}
    language = db.session.get(Language, body["languageId"]) if isinstance(body.get("languageId"), int) else None
    if language is None:
        return jsonify({"error": "Unknown language", "code": "bad_input"}), 404
    try:
        return jsonify(translate.translate(_datapath(), _settings(), language.name, body.get("text"), local_engine=_local_engine()))
    except translate.TranslateError as e:
        return _failure(e)


@bp.route("/translate/test", methods=["POST"])
def test_translation():
    "Try the current settings with a short Dutch sentence, asking the service for real."
    try:
        result = translate.translate(_datapath(), _settings(), "Dutch", "Goedemorgen, hoe gaat het met je?", use_cache=False, local_engine=_local_engine())
    except translate.TranslateError as e:
        return _failure(e)
    return jsonify(result)
