"""
Background jobs (voice a book, download or import a model). They run one at a time, in the order
they were submitted; progress is kept in memory.

    GET  /ocarina/api/jobs              running and waiting jobs, in order
    GET  /ocarina/api/jobs/<id>         state, done and total (and queue position while waiting)
    POST /ocarina/api/jobs/<id>/cancel  drop a waiting job, or stop a running one

States: queued, running, done, error, cancelled. A job's function is called as run(job, check)
and calls check() now and then; check() raises Cancelled once the user cancelled the job.
"""

import threading
import uuid

from flask import Blueprint, jsonify

from ocarina.tts.errors import explain

bp = Blueprint("ocarina_jobs", __name__, url_prefix="/ocarina/api")

MAX_KEPT = 50  # finished jobs to remember; older ones are dropped
ACTIVE = ("queued", "running")


class Cancelled(Exception):
    "Raised by check() inside a job that the user cancelled."


_jobs = {}  # id -> job dict (what the API shows)
_queue = []  # ids of waiting jobs, first in line first
_runs = {}  # id -> function to run
_stop = {}  # id -> Event, set when the user cancels
_cond = threading.Condition()
_dispatcher = None


def _describe(job):
    "The job as the API shows it."
    out = dict(job)
    if job["state"] == "queued":
        out["queuePosition"] = _queue.index(job["id"]) + 1
    return out


def _prune():
    finished = [j for j in _jobs.values() if j["state"] not in ACTIVE]
    for old in finished[: max(0, len(finished) - MAX_KEPT)]:
        del _jobs[old["id"]]


def _dispatch():
    "Thread: run the waiting jobs one after another."
    while True:
        with _cond:
            while not _queue:
                _cond.wait()
            job = _jobs[_queue.pop(0)]
            job["state"] = "running"
            run, stop = _runs.pop(job["id"]), _stop[job["id"]]

        def check(stop=stop):
            if stop.is_set():
                raise Cancelled()

        try:
            run(job, check)
            outcome = ("done", None)
        except Cancelled:
            outcome = ("cancelled", None)
        except Exception as e:  # pylint: disable=broad-exception-caught
            technical = f"{type(e).__name__}: {e}"
            friendly = explain(technical)
            outcome = ("error", friendly or technical, technical if friendly else None)
        with _cond:
            job["state"] = outcome[0]
            if outcome[1]:
                job["error"] = outcome[1]
            if len(outcome) > 2 and outcome[2]:
                job["detail"] = outcome[2]  # the original message, for those who want it
            _stop.pop(job["id"], None)


def submit(kind, run, **fields):
    "Add a job to the queue; run(job, check) is called when its turn comes. Returns the job."
    global _dispatcher  # pylint: disable=global-statement
    with _cond:
        _prune()
        job = {"id": uuid.uuid4().hex, "kind": kind, "state": "queued", "done": 0, "total": 0, **fields}
        _jobs[job["id"]] = job
        _runs[job["id"]] = run
        _stop[job["id"]] = threading.Event()
        _queue.append(job["id"])
        if _dispatcher is None:
            _dispatcher = threading.Thread(target=_dispatch, daemon=True)
            _dispatcher.start()
        _cond.notify()
        return _describe(job)


def active(**match):
    "Running and waiting jobs (running first) whose fields equal match."
    with _cond:
        jobs = sorted(
            (j for j in _jobs.values() if j["state"] in ACTIVE),
            key=lambda j: (j["state"] != "running", _queue.index(j["id"]) if j["id"] in _queue else 0),
        )
        return [_describe(j) for j in jobs if all(j.get(k) == v for k, v in match.items())]


def cancel(job_id):
    "Cancel a job; returns the job, or None if it is unknown or already finished."
    with _cond:
        job = _jobs.get(job_id)
        if job is None or job["state"] not in ACTIVE:
            return None
        if job["state"] == "queued":
            _queue.remove(job_id)
            _runs.pop(job_id, None)
            _stop.pop(job_id, None)
            job["state"] = "cancelled"
        else:
            _stop[job_id].set()  # the running job notices at its next check()
        return _describe(job)


@bp.route("/jobs", methods=["GET"])
def active_jobs():
    "Running and waiting jobs."
    return jsonify(active())


@bp.route("/jobs/<job_id>", methods=["GET"])
def job_status(job_id):
    "Progress of a job."
    with _cond:
        job = _jobs.get(job_id)
        return (jsonify(_describe(job)), 200) if job else (jsonify({"error": "No such job"}), 404)


@bp.route("/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id):
    "Cancel a waiting or running job."
    job = cancel(job_id)
    if job is None:
        return jsonify({"error": "No such active job"}), 404
    return jsonify(job)
