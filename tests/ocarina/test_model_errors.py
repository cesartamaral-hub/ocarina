"""
Model failures in plain words, and what a failing job reports.
"""

import time

import pytest

from ocarina.api import jobs
from ocarina.tts.errors import explain


@pytest.mark.parametrize(
    "technical, expected",
    [
        ("TtsError: ModuleNotFoundError: No module named 'torch'", "needs the Python package “torch”"),
        ("ModuleNotFoundError: No module named 'torchaudio.transforms'", "needs the Python package “torchaudio”"),
        ("FileNotFoundError: No weight files (safetensors or npz) found in /x", "incomplete"),
        ("RuntimeError: [metal::malloc] Resource limit exceeded. kIOGPUCommandBufferCallbackErrorOutOfMemory", "more memory than is free"),
        ("TtsError: TTS worker died or timed out", "stopped"),
        ("TtsError: No conditionals available - ref_audio will be required", "reference voice"),
        ("TypeError: data type 'bfloat16' not understood", "cannot read"),
    ],
)
def test_known_failures_are_explained(technical, expected):
    "Each known failure gets a sentence that says what to do."
    assert expected in explain(technical)


def test_unknown_failures_are_left_alone():
    "Nothing is guessed: an unrecognised message has no explanation."
    assert explain("ValueError: something odd") is None and explain(None) is None


def test_a_failing_job_reports_the_plain_message_and_keeps_the_original():
    "error is the sentence; detail is the original text, only when there was something to explain."
    def boom(job, check):  # pylint: disable=unused-argument
        raise ModuleNotFoundError("No module named 'torch'")

    def odd(job, check):  # pylint: disable=unused-argument
        raise ValueError("odd")

    a, b = jobs.submit("audio", boom), jobs.submit("audio", odd)
    end = time.time() + 5
    while time.time() < end and any(jobs._jobs[j["id"]]["state"] in ("queued", "running") for j in (a, b)):  # pylint: disable=protected-access
        time.sleep(0.02)
    first, second = jobs._jobs[a["id"]], jobs._jobs[b["id"]]  # pylint: disable=protected-access
    assert "needs the Python package “torch”" in first["error"] and first["detail"] == "ModuleNotFoundError: No module named 'torch'"
    assert second["error"] == "ValueError: odd" and "detail" not in second
