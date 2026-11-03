"""
JSON API for the voice models.

    GET    /ocarina/api/tts/models                catalog with install status
    POST   /ocarina/api/tts/models/<id>/download  download a model (a job)
    POST   /ocarina/api/tts/models/<id>/import    copy a model's files from a folder (a job)
    DELETE /ocarina/api/tts/models/<id>           delete a model's files
"""

from flask import Blueprint, jsonify, request

from ocarina.api import jobs
from ocarina.tts import models as model_files

bp = Blueprint("ocarina_tts_models", __name__, url_prefix="/ocarina/api")


def _run_download(job, check, model, folder=None):
    "Queued job: download a model's files, or copy them from a folder (cancelling keeps what is there)."

    def progress(done, total):
        check()
        job["done"], job["total"] = done, total

    check()
    if folder:
        model_files.import_from_folder(model, folder, progress)
    else:
        model_files.download(model, progress)


@bp.route("/tts/models", methods=["GET"])
def models():
    "The model catalog, with whether each model is installed and its download size."
    active = jobs.active(kind="download")
    return jsonify(
        [
            {
                **m,
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
    if jobs.active(kind="download", model_id=model_id):
        return jsonify({"error": "This model is already being installed"}), 409
    job = jobs.submit(
        "download",
        lambda job, check: _run_download(job, check, model),
        model_id=model_id,
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
    job = jobs.submit(
        "download",
        lambda job, check: _run_download(job, check, model, folder),
        model_id=model_id,
        total=model_files.total_bytes(model),
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
    return jsonify({"ok": True})
