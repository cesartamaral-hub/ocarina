"""
The job queue: order, waiting positions, cancelling, errors.
"""

import threading
import time

from ocarina.api import jobs


def _wait(job_id, states, seconds=5):
    end = time.time() + seconds
    while time.time() < end:
        if jobs._jobs[job_id]["state"] in states:  # pylint: disable=protected-access
            return
        time.sleep(0.01)
    raise AssertionError(f"job stayed {jobs._jobs[job_id]['state']}")  # pylint: disable=protected-access


def test_jobs_run_one_at_a_time_in_order():
    "A second job waits (position 1) until the first has finished."
    gate, order = threading.Event(), []

    def first(job, check):  # pylint: disable=unused-argument
        order.append("first")
        gate.wait(5)

    def second(job, check):  # pylint: disable=unused-argument
        order.append("second")

    a = jobs.submit("audio", first)
    b = jobs.submit("audio", second)
    _wait(a["id"], ("running",))
    assert jobs._jobs[b["id"]]["state"] == "queued"  # pylint: disable=protected-access
    assert [j["id"] for j in jobs.active()] == [a["id"], b["id"]]
    assert jobs.active()[1]["queuePosition"] == 1
    gate.set()
    _wait(b["id"], ("done",))
    assert order == ["first", "second"]
    assert jobs.active() == []


def test_cancel_a_waiting_job_skips_it():
    "A cancelled waiting job never runs."
    gate, ran = threading.Event(), []
    a = jobs.submit("audio", lambda job, check: gate.wait(5))
    b = jobs.submit("audio", lambda job, check: ran.append("b"))
    _wait(a["id"], ("running",))
    assert jobs.cancel(b["id"])["state"] == "cancelled"
    gate.set()
    _wait(a["id"], ("done",))
    assert ran == [] and jobs.cancel(b["id"]) is None


def test_cancel_a_running_job_stops_it_at_its_next_check():
    "check() raises once cancelled; the job ends as cancelled, and the next job still runs."
    started, progress = threading.Event(), []

    def work(job, check):  # pylint: disable=unused-argument
        started.set()
        for i in range(1000):
            check()
            progress.append(i)
            time.sleep(0.01)

    a = jobs.submit("audio", work)
    b = jobs.submit("audio", lambda job, check: None)
    started.wait(5)
    jobs.cancel(a["id"])
    _wait(a["id"], ("cancelled",))
    _wait(b["id"], ("done",))
    assert len(progress) < 1000


def test_a_failing_job_reports_the_error_and_the_queue_goes_on():
    "An exception becomes state=error with a message."

    def boom(job, check):  # pylint: disable=unused-argument
        raise ValueError("kapot")

    a = jobs.submit("audio", boom)
    b = jobs.submit("audio", lambda job, check: None)
    _wait(b["id"], ("done",))
    assert jobs._jobs[a["id"]]["state"] == "error"  # pylint: disable=protected-access
    assert "kapot" in jobs._jobs[a["id"]]["error"]  # pylint: disable=protected-access


def test_old_finished_jobs_are_dropped():
    "The in-memory job list does not grow without limit."
    for _ in range(jobs.MAX_KEPT + 20):
        job = jobs.submit("audio", lambda job, check: None)
        _wait(job["id"], ("done",))
    assert len(jobs._jobs) <= jobs.MAX_KEPT + 1  # pylint: disable=protected-access


def test_cancel_and_queue_api(client):
    "The HTTP endpoints list active jobs and cancel them."
    gate = threading.Event()
    a = jobs.submit("audio", lambda job, check: gate.wait(5), book_id=1)
    b = jobs.submit("audio", lambda job, check: None, book_id=2)
    _wait(a["id"], ("running",))
    listed = client.get("/ocarina/api/jobs").json
    assert [j["state"] for j in listed] == ["running", "queued"]
    assert client.get(f"/ocarina/api/jobs/{b['id']}").json["queuePosition"] == 1
    assert client.post(f"/ocarina/api/jobs/{b['id']}/cancel").json["state"] == "cancelled"
    assert client.post(f"/ocarina/api/jobs/{b['id']}/cancel").status_code == 404
    gate.set()
    _wait(a["id"], ("done",))
