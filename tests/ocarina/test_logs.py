"The log file (ocarina/logs.py) and its API."

import logging
import os

from ocarina import logs


def test_the_log_gets_a_header_and_what_is_logged(tmp_path, monkeypatch):
    monkeypatch.setattr(logs, "_ready", False)
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        path = logs.setup(str(tmp_path), redirect=False)
        logging.getLogger("ocarina.test").error("something broke: %s", "details")
        for h in root.handlers:
            h.flush()
        text = open(path, encoding="utf-8").read()
        assert "Ocarina " in text and "starting; macOS" in text and "something broke: details" in text
    finally:
        for h in list(root.handlers):
            if h not in before:
                root.removeHandler(h)
                h.close()
        logs._ready = False  # pylint: disable=protected-access


def test_a_big_log_is_kept_as_the_older_one(tmp_path):
    folder = tmp_path / "logs"
    folder.mkdir()
    big = folder / logs.NAME
    big.write_bytes(b"x" * (logs.MAX_BYTES + 1))
    logs._rotate(str(big))  # pylint: disable=protected-access
    assert (folder / (logs.NAME + ".1")).exists() and not big.exists()


def test_the_api_shows_where_the_log_is(client):
    body = client.get("/ocarina/api/log").json
    assert body["path"].endswith(os.path.join("logs", logs.NAME)) and body["folder"].endswith("logs")
    r = client.post("/ocarina/api/log/open")
    assert r.status_code == 200 and r.json["opened"] is False  # the tests do not open Finder


def test_a_failed_job_is_logged(app, caplog):
    from ocarina.api import jobs  # pylint: disable=import-outside-toplevel

    def boom(job, check):
        raise ValueError("it broke")

    with caplog.at_level(logging.ERROR, logger="ocarina.jobs"):
        with app.app_context():
            job = jobs.submit("check", boom)
            for _ in range(100):
                if jobs._jobs[job["id"]]["state"] not in ("queued", "running"):  # pylint: disable=protected-access
                    break
                __import__("time").sleep(0.05)
    assert any("it broke" in r.getMessage() for r in caplog.records)
