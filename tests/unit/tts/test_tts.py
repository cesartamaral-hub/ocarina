"""
TTS tests; use the fake engine so no model is needed.
"""

import os

import soundfile as sf

from ocarina.tts.cache import SentenceCache
from ocarina.tts.sentences import split_sentences
from ocarina.tts.service import DEFAULT_VOICE, synthesize_text
from ocarina.tts.stitch import stitch
from ocarina.tts.supervisor import Supervisor


def test_split_sentences():
    "Splits on sentence ends and line breaks, drops empties."
    text = "Hallo wereld. Hoe gaat het?\n\nGoed! « Ja », zei hij."
    assert split_sentences(text) == [
        "Hallo wereld.",
        "Hoe gaat het?",
        "Goed!",
        "« Ja », zei hij.",
    ]
    assert split_sentences("") == []


def test_cache_path_depends_on_all_inputs(tmp_path):
    "Different model, language, voice or text give different files."
    c = SentenceCache(str(tmp_path))
    base = c.path_for("m", "nl", "v", "Hallo.")
    assert base == c.path_for("m", "nl", "v", "Hallo.")
    for other in [("m2", "nl", "v", "Hallo."), ("m", "fr", "v", "Hallo."),
                  ("m", "nl", "v2", "Hallo."), ("m", "nl", "v", "Hallo!")]:
        assert c.path_for(*other) != base


def test_synthesize_uses_cache_and_stitches(tmp_path):
    "Second run reuses cached sentences; stitch reports sentence starts."
    cache = SentenceCache(str(tmp_path / "cache"))
    sup = Supervisor("fake")
    try:
        first = synthesize_text(sup, cache, "fake", "Eén. Twee. Drie.", "nl", DEFAULT_VOICE)
        assert [c for _, _, c in first] == [False, False, False]
        second = synthesize_text(sup, cache, "fake", "Eén. Twee. Vier.", "nl", DEFAULT_VOICE)
        assert [c for _, _, c in second] == [True, True, False]
    finally:
        sup.unload()
    audio, sr, starts = stitch([p for _, p, _ in first], pause_seconds=0.5)
    assert starts[0] == 0 and starts[1] > 0.5 and starts[2] > starts[1]
    assert len(audio) / sr > starts[2]


def test_worker_restarts_after_crash(tmp_path):
    "A killed worker is restarted and the request still succeeds."
    sup = Supervisor("fake")
    out = str(tmp_path / "a.wav")
    try:
        sup.synth("Hallo.", "nl", DEFAULT_VOICE, out)
        sup._proc.kill()  # pylint: disable=protected-access
        sup._proc.wait()  # pylint: disable=protected-access
        out2 = str(tmp_path / "b.wav")
        sup.synth("Hallo.", "nl", DEFAULT_VOICE, out2)
    finally:
        sup.unload()
    assert os.path.exists(out2)
    assert sf.info(out2).samplerate == 24000
