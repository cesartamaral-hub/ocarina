"""
JSON API for the voice models.

    GET    /ocarina/api/tts/models                catalog with install status
    POST   /ocarina/api/tts/models/<id>/download  download a model (a job)
    POST   /ocarina/api/tts/models/<id>/import    copy a model's files from a folder (a job)
    DELETE /ocarina/api/tts/models/<id>           delete a model's files
    GET    /ocarina/api/tts/engines               how a model can be used (for adding one)
    POST   /ocarina/api/tts/models/lookup         look up a Hugging Face repository (needs the internet)
    POST   /ocarina/api/tts/models/custom         add a Hugging Face model to the list
    DELETE /ocarina/api/tts/models/<id>/entry     take a model you added out of the list (and delete its files)
    POST   /ocarina/api/tts/models/<id>/check     try an installed model once (a job); the result is in the model list
"""

from flask import Blueprint, current_app, jsonify, request

from ocarina import model_check, offline
from ocarina.api import jobs
from ocarina.tts import models as model_files

_OFFLINE_REPLY = {"error": "Work offline is on, so nothing can be downloaded. Turn it off in Settings → General, or import the files from a folder.", "code": "offline_mode"}

bp = Blueprint("ocarina_tts_models", __name__, url_prefix="/ocarina/api")


def _run_download(job, check, model, folder=None, datapath=None, engine=None):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """
    Queued job: download a model's files, or copy them from a folder (cancelling keeps what is there). A model you
    added yourself is then tried once, so you learn at once whether it works here (see ocarina/model_check.py).
    """

    def progress(done, total):
        check()
        job["done"], job["total"] = done, total

    check()
    if folder:
        model_files.import_from_folder(model, folder, progress)
    else:
        model_files.download(model, progress, check)
    if model.get("custom") and datapath:
        job["phase"] = "testing"
        model_check.check_model(datapath, model, engine)


def _run_check(job, check, model, datapath, engine):
    "Queued job: try an installed model once and store how it went."
    check()
    job["phase"] = "testing"
    model_check.check_model(datapath, model, engine)


@bp.route("/tts/models", methods=["GET"])
def models():
    "The model catalog, with whether each model is installed and its download size."
    active = jobs.active(kind="download")
    datapath = current_app.env_config.datapath
    return jsonify(
        [
            {
                **m,
                "kind": model_files.kind_of(m),
                "check": model_check.result_for(datapath, m),
                "installed": model_files.is_installed(m),
                "sizeBytes": model_files.total_bytes(m),
                "downloadJob": next((j["id"] for j in active if j["model_id"] == m["id"]), None),
            }
            for m in model_files.load_catalog()
        ]
    )


@bp.route("/tts/models/<model_id>/download", methods=["POST"])
def download_model(model_id):
    "Start downloading a model; returns the job."
    model = model_files.find_model(model_id)
    if model is None:
        return jsonify({"error": "Unknown model"}), 404
    if model_files.is_installed(model):
        return jsonify({"error": "Model is already installed"}), 409
    if offline.is_on():
        return jsonify(_OFFLINE_REPLY), 409
    if jobs.active(kind="download", model_id=model_id):
        return jsonify({"error": "This model is already being installed"}), 409
    datapath = current_app.env_config.datapath
    engine = current_app.config.get("OCARINA_TTS_ENGINE")  # the tests use a fake engine; None otherwise
    job = jobs.submit(
        "download",
        lambda job, check: _run_download(job, check, model, None, datapath, engine),
        model_id=model_id,
        title=model["name"],
        total=model_files.total_bytes(model),
    )
    return jsonify(job), 202


@bp.route("/tts/models/<model_id>/import", methods=["POST"])
def import_model(model_id):
    "Start copying a model's files from a folder you downloaded elsewhere; returns the job."
    model = model_files.find_model(model_id)
    if model is None:
        return jsonify({"error": "Unknown model"}), 404
    if model_files.is_installed(model):
        return jsonify({"error": "Model is already installed"}), 409
    folder = (request.get_json(silent=True) or {}).get("folder", "")
    try:
        model_files.find_import_files(model, folder)
    except model_files.FolderError as e:
        return jsonify({"error": str(e), "code": "bad_folder"}), 400
    if jobs.active(kind="download", model_id=model_id):
        return jsonify({"error": "This model is already being installed"}), 409
    datapath = current_app.env_config.datapath
    engine = current_app.config.get("OCARINA_TTS_ENGINE")  # the tests use a fake engine; None otherwise
    job = jobs.submit(
        "download",
        lambda job, check: _run_download(job, check, model, folder, datapath, engine),
        model_id=model_id,
        title=model["name"],
        total=model_files.total_bytes(model),
    )
    return jsonify(job), 202


@bp.route("/tts/engines", methods=["GET"])
def engines():
    "Ways a model can be used, and the languages it can be added for."
    return jsonify(
        {
            "engines": [{"id": key, "name": label} for key, label in model_files.ENGINES.items()],
            "languages": list(model_files.LANGUAGE_CODES),
        }
    )


@bp.route("/tts/models/lookup", methods=["POST"])
def lookup_model():
    "What a Hugging Face repository holds: revision, license and size."
    if offline.is_on():
        return jsonify(_OFFLINE_REPLY), 409
    try:
        found = model_files.describe(model_files.lookup_hub_repo((request.get_json(silent=True) or {}).get("repo", "").strip()))
    except model_files.HubError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({**found, "files": len(found["files"])})


@bp.route("/tts/models/custom", methods=["POST"])
def add_custom_model():
    "Add a Hugging Face model to the list (it still has to be downloaded)."
    if offline.is_on():
        return jsonify(_OFFLINE_REPLY), 409
    body = request.get_json(silent=True) or {}
    try:
        entry = model_files.add_custom_model(
            (body.get("repo") or "").strip(), body.get("engine"), body.get("languages") or [], body.get("name")
        )
    except model_files.HubError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(entry), 201


@bp.route("/tts/models/<model_id>/entry", methods=["DELETE"])
def remove_model_entry(model_id):
    "Forget a model that was added from Hugging Face, and delete its files."
    model = model_files.find_model(model_id)
    if model is None or not model.get("custom"):
        return jsonify({"error": "Only models you added can be removed from the list"}), 404
    if jobs.active():
        return jsonify({"error": "Wait for the running jobs to finish, or cancel them"}), 409
    model_files.delete(model)
    model_files.remove_custom_model(model_id)
    model_check.forget(current_app.env_config.datapath, model_id)
    return jsonify({"removed": model_id})


@bp.route("/tts/models/<model_id>/check", methods=["POST"])
def check_model(model_id):
    "Try an installed model once (loads it, uses it) and store the result."
    model = model_files.find_model(model_id)
    if model is None:
        return jsonify({"error": "Unknown model"}), 404
    engine = current_app.config.get("OCARINA_TTS_ENGINE")
    if engine is None and not model_files.is_installed(model):
        return jsonify({"error": "Download the model first"}), 409
    if jobs.active(kind="check", model_id=model_id):
        return jsonify({"error": "This model is already being tested"}), 409
    datapath = current_app.env_config.datapath
    job = jobs.submit(
        "check",
        lambda job, check: _run_check(job, check, model, datapath, engine),
        model_id=model_id,
        title=model["name"],
    )
    return jsonify(job), 202


@bp.route("/tts/models/<model_id>", methods=["DELETE"])
def delete_model(model_id):
    "Delete a model's files."
    model = model_files.find_model(model_id)
    if model is None:
        return jsonify({"error": "Unknown model"}), 404
    if jobs.active():
        return jsonify({"error": "Wait for the running jobs to finish, or cancel them"}), 409
    model_files.delete(model)
    model_check.forget(current_app.env_config.datapath, model_id)
    return jsonify({"ok": True})
