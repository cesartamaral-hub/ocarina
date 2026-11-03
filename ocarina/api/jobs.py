"""
Background jobs (voice a book, download a model). One runs at a time; progress is kept in memory.

    GET /ocarina/api/jobs/<id>   state, done and total
"""

import threading
import uuid

from flask import Blueprint, jsonify

bp = Blueprint("ocarina_jobs", __name__, url_prefix="/ocarina/api")

MAX_KEPT = 50  # finished jobs to remember; older ones are dropped

_jobs = {}
_lock = threading.Lock()


def running_job():
    "The job that is running now, or None."
    return next((j for j in _jobs.values() if j["state"] == "running"), None)


def new_job(kind, **fields):
    "Register a running job, or return None if another one is already running."
    with _lock:
        if running_job() is not None:
            return None
        finished = [j for j in _jobs.values() if j["state"] != "running"]
        for old in finished[: max(0, len(finished) - MAX_KEPT)]:
            del _jobs[old["id"]]
        job = {
            "id": uuid.uuid4().hex,
            "kind": kind,
            "state": "running",
            "done": 0,
            "total": 0,
            **fields,
        }
        _jobs[job["id"]] = job
        return job


@bp.route("/jobs/<job_id>", methods=["GET"])
def job_status(job_id):
    "Progress of a job."
    job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "No such job"}), 404
    return jsonify(job)
