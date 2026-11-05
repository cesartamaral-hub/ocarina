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
