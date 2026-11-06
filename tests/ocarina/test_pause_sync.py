"""
Syncing without a model: the pauses of a recording are matched to the sentences, the user can pin a start, and a subtitle file gives
the timings. The recordings here are tones of the right length (about 0.07 s per character) with silence between them.
"""

import io
import math
import shutil

import numpy as np
import pytest
import soundfile as sf

from ocarina import pause_sync, subtitles
from ocarina.tts.book_audio import book_sentences
from tests.ocarina.helpers import make_dutch_book, wait_for_job

BOOKS = "/ocarina/api/books"
pytestmark = pytest.mark.autosync  # uploads start a sync here, as in the app
RATE = 16000
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None and not pause_sync.tools.ffmpeg(), reason="ffmpeg is needed to find pauses")


def recording(chars, gap=0.6, lead=0.5, per_char=0.07):
    "A wav of one tone burst per sentence (length by characters); returns (bytes, the true start of each burst)."
    parts, starts, at = [np.zeros(int(lead * RATE))], [], lead
    for n in chars:
        seconds = n * per_char
        t = np.arange(int(seconds * RATE)) / RATE
        parts.append(0.5 * np.sin(2 * math.pi * 220 * t))
        parts.append(np.zeros(int(gap * RATE)))
        starts.append(at)
        at += seconds + gap
    buffer = io.BytesIO()
    sf.write(buffer, np.concatenate(parts), RATE, format="WAV")
    return buffer.getvalue(), starts


def test_the_matcher_picks_the_sentence_breaks_among_commas():
    weights = [30, 12, 40, 20]
    pauses = [(0.0, 0.5), (4.0, 4.6), (5.0, 5.2), (6.0, 6.7), (9.5, 10.1), (12.0, 12.6)]  # (5.0, 5.2) is a comma inside a sentence
    starts = pause_sync.match_pauses(weights, 14.0, pauses)
    assert starts is not None and len(starts) == 4
    assert starts[0] == pytest.approx(0.42, abs=0.01)
    assert starts == sorted(starts) and 4.0 < starts[1] < 6.7 and 9.0 < starts[3] < 12.6  # never the comma pause between sentence 1 and 2


def test_too_few_pauses_give_no_match_and_an_estimate_instead():
    assert pause_sync.match_pauses([10, 10, 10], 9.0, []) is None
    starts, how = pause_sync.fit([10, 10, 10], 9.0, [])
    assert how == "estimate" and starts == [0.0, 3.0, 6.0]


def test_a_pin_fixes_one_sentence_and_the_rest_is_fitted_around_it():
    weights = [20, 20, 20, 20]
    pauses = [(0.0, 0.5), (2.0, 2.4), (4.0, 4.4), (6.0, 6.4)]
    starts, _ = pause_sync.fit(weights, 8.4, pauses, {2: 4.1})
    assert starts[2] == 4.1 and starts[0] < starts[1] < starts[2] < starts[3]


def test_subtitles_give_sentence_starts_in_srt_vtt_and_lrc():
    srt = "1\n00:00:01,000 --> 00:00:03,000\nHallo! Mijn naam is Carla.\n\n2\n00:00:03,500 --> 00:00:05,000\nIk woon in Nederland.\n"
    vtt = "WEBVTT\n\n00:01.000 --> 00:03.000\nHallo! Mijn naam is Carla.\n\n00:03.500 --> 00:05.000\nIk woon in Nederland.\n"
    lrc = "[00:01.00]Hallo! Mijn naam is Carla.\n[00:03.50]Ik woon in Nederland.\n"
    for text in (srt, vtt, lrc):
        cues = subtitles.parse(text)
        assert len(cues) == 2 and cues[1][0] == pytest.approx(3.5)
        starts = subtitles.sentence_starts(["Hallo!", "Mijn naam is Carla.", "Ik woon in Nederland."], cues)
        assert starts is not None and starts[0] == pytest.approx(0.95, abs=0.01) and starts[2] == pytest.approx(3.45, abs=0.01)
        assert starts[0] < starts[1] < starts[2]


def test_subtitles_that_do_not_match_the_text_are_refused():
    cues = subtitles.parse("1\n00:00:01,000 --> 00:00:03,000\nCompletely different words here.\n")
    assert subtitles.sentence_starts(["Hallo!", "Mijn naam is Carla."], cues) is None


@needs_ffmpeg
def test_a_recording_is_synced_by_its_pauses_then_adjusted(app, client, monkeypatch):
    monkeypatch.setattr("ocarina.tts.models.is_installed", lambda model: False)
    with app.app_context():
        book = make_dutch_book("Pauzes")
        chars = [len("".join(s["text"].split())) for s in book_sentences(book)]
        book_id = book.id
    wav, truth = recording(chars)
    up = client.post(f"{BOOKS}/{book_id}/audio/upload", data={"audio": (io.BytesIO(wav), "eigen.wav")}, content_type="multipart/form-data")
    version_id = up.json["versionId"]
    job = up.json["sync"]["job"]
    assert job["method"] == "pauses" and wait_for_job(client, job["id"])["state"] == "done"
    sentences = client.get(f"{BOOKS}/{book_id}/sentences").json
    assert sentences["hasTimings"]
    got = [s["start"] for s in sentences["sentences"]]
    assert all(abs(a - b) < 0.3 for a, b in zip(got, truth))
    version = next(v for v in client.get(f"{BOOKS}/{book_id}/audio/versions").json if v["id"] == version_id)
    assert version["synced"] and version["syncMethod"] == "pauses" and version["approximate"]
    pinned = client.put(f"{BOOKS}/{book_id}/audio/versions/{version_id}/anchors", json={"sentence": 1, "time": truth[1] + 0.2})
    assert pinned.status_code == 200 and pinned.json["pins"] == {"1": truth[1] + 0.2}
    assert client.get(f"{BOOKS}/{book_id}/sentences").json["sentences"][1]["start"] == pytest.approx(truth[1] + 0.2, abs=0.01)
    assert client.put(f"{BOOKS}/{book_id}/audio/versions/{version_id}/anchors", json={"sentence": "x"}).status_code == 400


def test_a_subtitle_file_syncs_a_recording(app, client):
    with app.app_context():
        book_id = make_dutch_book("Ondertitels").id
    up = client.post(f"{BOOKS}/{book_id}/audio/upload", data={"audio": (io.BytesIO(b"ID3x"), "eigen.mp3")}, content_type="multipart/form-data")
    version_id = up.json["versionId"]
    srt = "1\n00:00:01,000 --> 00:00:03,000\nHallo! Mijn naam is Carla.\n\n2\n00:00:03,500 --> 00:00:06,000\nIk woon in Nederland.\n\n3\n00:00:07,000 --> 00:00:09,000\nElke ochtend sta ik op.\n"
    r = client.post(f"{BOOKS}/{book_id}/audio/versions/{version_id}/subtitles", data={"file": (io.BytesIO(srt.encode()), "x.srt")}, content_type="multipart/form-data")
    assert r.status_code == 200
    version = next(v for v in r.json if v["id"] == version_id)
    assert version["syncMethod"] == "subtitles" and version["approximate"]
    wrong = client.post(f"{BOOKS}/{book_id}/audio/versions/{version_id}/subtitles", data={"file": (io.BytesIO(b"1\n00:00:01,000 --> 00:00:02,000\nnothing alike\n"), "y.srt")}, content_type="multipart/form-data")
    assert wrong.status_code == 400 and wrong.json["code"] == "no_match"



def test_ffmpeg_only_decodes_because_the_apps_own_build_has_no_silencedetect(monkeypatch):
    "The ffmpeg inside the app is a small build; asking it for a filter would silently find no pauses."
    seen = {}

    class Done:
        returncode = 0
        stdout = np.zeros(RATE, dtype="<i2").tobytes() + (np.ones(RATE // 2, dtype="<i2") * 8000).tobytes()

    def run(cmd, **kwargs):
        seen["cmd"] = cmd
        return Done()

    monkeypatch.setattr(pause_sync.tools, "ffmpeg", lambda: "/bundled/ffmpeg")
    monkeypatch.setattr(pause_sync.subprocess, "run", run)
    duration, pauses = pause_sync.detect_pauses("x.mp3")
    assert "-af" not in seen["cmd"] and "silencedetect" not in " ".join(seen["cmd"])
    assert duration == pytest.approx(1.5) and pauses == [(0.0, 1.0)]
