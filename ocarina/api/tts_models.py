"""
JSON API for the voice models.

    GET    /ocarina/api/tts/models                catalog with install status
    POST   /ocarina/api/tts/models/<id>/download  download a model (a job)
    DELETE /ocarina/api/tts/models/<id>           delete a model's files
"""

import threading

from flask import Blueprint, jsonify

from ocarina.api import jobs
from ocarina.tts import models as model_files

bp = Blueprint("ocarina_tts_models", __name__, url_prefix="/ocarina/api")


def _run_download(job, model):
    "Background thread: download a model's files."

    def progress(done, total):
        job["done"], job["total"] = done, total

    try:
        model_files.download(model, progress)
        job["state"] = "done"
    except Exception as e:  # pylint: disable=broad-exception-caught
        job["state"], job["error"] = "error", f"{type(e).__name__}: {e}"


@bp.route("/tts/models", methods=["GET"])
def models():
    "The model catalog, with whether each model is installed and its download size."
    active = jobs.running_job()
    return jsonify(
        [
            {
                **m,
                "installed": model_files.is_installed(m),
                "sizeBytes": model_files.total_bytes(m),
                "downloadJob": active["id"]
                if active and active.get("model_id") == m["id"]
                else None,
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
    job = jobs.new_job("download", model_id=model_id, total=model_files.total_bytes(model))
    if job is None:
        return jsonify({"error": "Another job is running"}), 409
    threading.Thread(target=_run_download, args=(job, model), daemon=True).start()
    return jsonify(job), 202


@bp.route("/tts/models/<model_id>", methods=["DELETE"])
def delete_model(model_id):
    "Delete a model's files."
    model = model_files.find_model(model_id)
    if model is None:
        return jsonify({"error": "Unknown model"}), 404
    if jobs.running_job() is not None:
        return jsonify({"error": "Another job is running"}), 409
    model_files.delete(model)
    return jsonify({"ok": True})
