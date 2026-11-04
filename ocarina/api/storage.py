"""
JSON API for the Storage page.

    GET  /ocarina/api/storage         disk space used by each model and by Ocarina's data
    POST /ocarina/api/storage/clear   {"what": "sentence_audio" | "translations" | "dictionary" | "temp" | "leftovers"}:
                                      empty a cache, or delete what deleted models left in the shared download store
                                      (not while a job is running, since jobs use them)
Deleting a model is DELETE /ocarina/api/tts/models/<id> (see tts_models.py).
"""

from flask import Blueprint, current_app, jsonify, request

from ocarina import storage
from ocarina.api import jobs

bp = Blueprint("ocarina_storage", __name__, url_prefix="/ocarina/api")


@bp.route("/storage", methods=["GET"])
def get_storage():
    "Disk space used by models and data."
    return jsonify(storage.summary(current_app.env_config.datapath))


@bp.route("/storage/clear", methods=["POST"])
def clear_cache():
    "Empty one cache; the data you made yourself cannot be cleared here."
    what = (request.get_json(silent=True) or {}).get("what")
    if jobs.active():
        return jsonify({"error": "Something is running in the background (audio, a download or a check). Try again when it has finished.", "code": "busy"}), 409
    freed = storage.clear(current_app.env_config.datapath, what)
    if freed is None:
        return jsonify({"error": "That cannot be cleared here."}), 400
    return jsonify({"freed": freed, **storage.summary(current_app.env_config.datapath)})
