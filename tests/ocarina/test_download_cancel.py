"""
Cancelling a model download stops it at once: the files are fetched by a process of its own, which is ended when the job is cancelled.
"""

import os
import sys
import time

import pytest

from ocarina.api.jobs import Cancelled
from ocarina.tts import models

SLOW = """
import json, sys, time
sys.stdin.readline()
for i in range(1000):
    print(json.dumps({"done": i, "total": 1000}), flush=True)
    time.sleep(0.05)
print(json.dumps({"ok": True}), flush=True)
"""

QUICK = """
import json, sys
sys.stdin.readline()
print(json.dumps({"done": 5, "total": 10}), flush=True)
print(json.dumps({"ok": True}), flush=True)
"""

FAILS = """
import json, sys
sys.stdin.readline()
print(json.dumps({"error": "OSError: no space left on device"}), flush=True)
"""

DIES = """
import sys
sys.stdin.readline()
sys.exit(3)
"""


def run_script(monkeypatch, tmp_path, source):
    script = tmp_path / "fake_download.py"
    script.write_text(source)
    monkeypatch.setattr(models, "_download_command", lambda: ([sys.executable, str(script)], dict(os.environ)))


def test_a_cancel_ends_the_download_at_once(monkeypatch, tmp_path):
    run_script(monkeypatch, tmp_path, SLOW)
    seen = []
    stop = {"now": False}

    def check():
        if stop["now"]:
            raise Cancelled()

    def progress(done, total):
        seen.append(done)
        if done >= 3:
            stop["now"] = True

    started = time.time()
    with pytest.raises(Cancelled):
        models.download({"repositories": []}, progress, check)
    assert time.time() - started < 3  # the script would take 50 s to finish
    assert seen and seen[-1] < 100


def test_progress_comes_through_and_the_end_is_noticed(monkeypatch, tmp_path):
    run_script(monkeypatch, tmp_path, QUICK)
    seen = []
    models.download({"repositories": []}, lambda done, total: seen.append((done, total)), lambda: None)
    assert seen == [(5, 10)]


def test_a_failure_in_the_process_is_reported(monkeypatch, tmp_path):
    run_script(monkeypatch, tmp_path, FAILS)
    with pytest.raises(RuntimeError, match="no space left"):
        models.download({"repositories": []}, None, lambda: None)


def test_a_process_that_dies_is_reported(monkeypatch, tmp_path):
    run_script(monkeypatch, tmp_path, DIES)
    with pytest.raises(RuntimeError, match="stopped unexpectedly"):
        models.download({"repositories": []}, None, lambda: None)


def test_a_download_that_does_not_fit_is_refused(client, monkeypatch):
    model = models.load_catalog()[0]
    monkeypatch.setattr(models, "is_installed", lambda m: False)
    monkeypatch.setattr(models, "free_bytes", lambda path: models.total_bytes(model) + models.SPACE_MARGIN - 1000)
    reply = client.post(f"/ocarina/api/tts/models/{model['id']}/download")
    assert reply.status_code == 409
    assert reply.json["code"] == "no_space" and reply.json["missingBytes"] == 1000
    space = client.get("/ocarina/api/tts/models/space").json
    assert space["marginBytes"] == models.SPACE_MARGIN and space["queuedBytes"] == 0


def test_the_space_check_counts_the_margin():
    model = {"repositories": [{"files": {"a": 1000}}]}
    assert models.short_of_space(model, 1000 + models.SPACE_MARGIN) == 0
    assert models.short_of_space(model, 1000 + models.SPACE_MARGIN - 1) == 1
    assert models.short_of_space(model, 1000 + models.SPACE_MARGIN, queued=500) == 500


def test_only_the_voice_and_translation_models_are_starters(client):
    listed = client.get("/ocarina/api/tts/models").json
    assert {(m["kind"], m["id"]) for m in listed if m.get("starter")} == {
        ("speech", "chatterbox-multilingual-v3-mlx"),
        ("text", "qwen3-4b-instruct-mlx"),
    }
    optional = {m["kind"] for m in listed if m.get("badge") == "Recommended" and not m.get("starter")}
    assert optional == {"aligner", "transcriber"}


def test_a_failed_download_is_reported_until_the_next_try(client, monkeypatch):
    import time  # pylint: disable=import-outside-toplevel

    model = models.load_catalog()[0]
    monkeypatch.setattr(models, "is_installed", lambda m: False)
    monkeypatch.setattr(models, "free_bytes", lambda path: 10**15)

    def broken(*_args, **_kwargs):
        raise OSError("Network is unreachable")

    monkeypatch.setattr(models, "download", broken)
    job = client.post(f"/ocarina/api/tts/models/{model['id']}/download").json
    for _ in range(100):
        if client.get(f"/ocarina/api/jobs/{job['id']}").json["state"] not in ("queued", "running"):
            break
        time.sleep(0.05)
    listed = {m["id"]: m for m in client.get("/ocarina/api/tts/models").json}
    assert listed[model["id"]]["downloadError"]
    others = [m for i, m in listed.items() if i != model["id"]]
    assert all(m["downloadError"] is None for m in others)
