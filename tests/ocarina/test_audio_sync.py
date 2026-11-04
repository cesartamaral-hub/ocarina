import json
import os

import pytest

from ocarina import audio_sync
from ocarina.audio_sync import SyncError, align_sentences, suspect_sentences, words_of
from tests.ocarina.helpers import make_dutch_book

WORD, GAP = 0.4, 0.6  # seconds a word takes, and the pause after a sentence


def narrated(sentences):
    "A recording of the sentences: every word's true start and end."
    t, words = 0.5, []
    for s in sentences:
        for w in words_of(s["text"]):
            words.append((w, t, t + WORD))
            t += WORD
        t += GAP
    return words, t


class SpeechAligner:
    "Behaves like a forced aligner: finds the spoken words in the window and puts the given words on them in order."

    def __init__(self, truth, total, wrong=None):
        self.truth, self.total, self.calls = truth, total, []
        self.wrong = wrong

    def duration(self, audio):
        return self.total

    def onsets(self, audio, intervals):
        return [interval[0] for interval in intervals]

    def align(self, audio, offset, length, text):
        self.calls.append((offset, length))
        given = words_of(text)
        inside = [w for w in self.truth if w[1] >= offset - 0.001 and w[2] <= offset + length]
        out = []
        for i, w in enumerate(given):
            if i < len(inside):
                out.append([w, inside[i][1], inside[i][2]])
            else:  # more words than speech: they are squeezed in at the end of the window
                out.append([w, offset + length - 0.01, offset + length])
        return out


def sentences(n):
    return [{"text": f"Dit is zin nummer {i} van de tekst."} for i in range(n)]  # 8 words each


def test_words_are_runs_of_letters_digits_and_apostrophes():
    assert words_of("Hallo, 's nachts: Léa's kat — 12 keer!") == ["Hallo", "'s", "nachts", "Léa's", "kat", "12", "keer"]
    assert words_of("... ,, ") == []


def test_aligns_a_short_recording_in_one_window():
    s = sentences(5)
    truth, total = narrated(s)
    spans = align_sentences(s, SpeechAligner(truth, total), "x.mp3")
    first_words = [truth[i * 8][1] for i in range(5)]
    assert [round(a, 2) for a, *_ in spans] == [round(t, 2) for t in first_words]


def test_a_long_recording_is_aligned_in_windows_without_losing_or_repeating_sentences():
    s = sentences(40)
    truth, total = narrated(s)
    aligner = SpeechAligner(truth, total)
    spans = align_sentences(s, aligner, "x.mp3", window=30)
    assert len(aligner.calls) > 3
    first_words = [truth[i * 8][1] for i in range(40)]
    assert [round(a, 2) for a, *_ in spans] == [round(t, 2) for t in first_words]
    starts = [a for a, *_ in spans]
    assert starts == sorted(starts)


def test_progress_and_cancelling():
    s = sentences(40)
    truth, total = narrated(s)
    seen = []
    align_sentences(s, SpeechAligner(truth, total), "x.mp3", on_progress=lambda d, t: seen.append((d, t)), window=30)
    assert seen[-1] == (40, 40)
    assert [d for d, _ in seen] == sorted(d for d, _ in seen)

    def stop():
        raise RuntimeError("cancelled")

    with pytest.raises(RuntimeError):
        align_sentences(s, SpeechAligner(truth, total), "x.mp3", check=stop)


def test_text_longer_than_the_recording_is_refused_and_nothing_is_written(app, tmp_path):
    with app.app_context():
        book = make_dutch_book("Te lang")
        from ocarina.tts.book_audio import book_sentences

        s = book_sentences(book)
        truth, total = narrated(s[:1])  # the recording only has the first sentence
        with pytest.raises(SyncError):
            audio_sync.sync_book_audio(book, str(tmp_path), "rec.mp3", SpeechAligner(truth, total), "nl")
    assert not os.path.exists(tmp_path / "rec.mp3.sentences.json")


def test_a_different_word_count_from_the_aligner_is_reported():
    s = sentences(3)
    truth, total = narrated(s)

    class Odd(SpeechAligner):
        def align(self, audio, offset, length, text):
            return super().align(audio, offset, length, text)[:-1]

    with pytest.raises(SyncError):
        align_sentences(s, Odd(truth, total), "x.mp3")


def test_suspect_sentences_are_the_ones_too_quick_or_too_slow():
    s = [{"text": "een twee drie vier"}] * 3
    spans = [(0.0, 1.6), (2.0, 2.05), (3.0, 20.0)]
    assert suspect_sentences(s, spans) == [1, 2]


def test_writes_the_timings_file_the_reader_follows(app, tmp_path):
    with app.app_context():
        book = make_dutch_book("Sync")
        from ocarina.tts.book_audio import book_sentences

        s = book_sentences(book)
        truth, total = narrated(s)
        (tmp_path / "rec.mp3").write_bytes(b"x")
        suspect = audio_sync.sync_book_audio(book, str(tmp_path), "rec.mp3", SpeechAligner(truth, total), "nl")
    assert suspect == []
    made = json.loads((tmp_path / "rec.mp3.sentences.json").read_text(encoding="utf-8"))
    assert made["aligned"] is True and made["language"] == "nl"
    assert [x["text"] for x in made["sentences"]] == [x["text"] for x in s]
    assert made["sentences"][0]["start"] == 0.5
    assert all(x["start"] is not None for x in made["sentences"])
    assert os.path.exists(tmp_path / "rec.mp3.sentences.json")


def test_a_start_that_is_too_early_moves_to_the_first_sound():
    "The aligner puts a start in the pause before the sentence; it moves to the sound, a little ahead of it."
    spans = [(10.0, 14.0), (20.0, 24.0), (30.0, 33.0)]
    asked = []

    class Aligner:
        def onsets(self, audio, intervals):
            asked.extend(intervals)
            return [11.2, 20.0, 29.0]  # the third: sound claimed before the start; it must not move earlier

    refined = audio_sync.refine_starts(spans, Aligner(), "x.mp3")
    assert asked == [[10.0, 14.0], [20.0, 24.0], [30.0, 33.0]]  # looked for between each start and end
    assert refined[0][0] == pytest.approx(11.2 - audio_sync.LEAD_IN) and refined[0][1] == 14.0
    assert refined[1][0] == 20.0  # the sound starts where the start is: unchanged
    assert refined[2][0] == 30.0
    assert audio_sync.refine_starts([None, (1.0, 2.0)], Aligner(), "x.mp3")[0] is None


def _frames(*runs, length=1000):
    "10 ms frames, loud in the given (from, to) runs."
    import numpy as np  # pylint: disable=import-outside-toplevel

    frames = np.zeros(length, dtype=bool)
    for a, b in runs:
        frames[a:b] = True
    return frames


def test_speech_starts_at_the_first_sound():
    from ocarina.tts.worker import first_speech  # pylint: disable=import-outside-toplevel

    assert first_speech(_frames((120, 300)), 50, 400) == 120  # the aligner started in silence
    assert first_speech(_frames((50, 300)), 50, 400) == 50  # it started right on the sound
    assert first_speech(_frames(), 50, 400) is None  # nothing is said there


def test_a_short_tail_of_the_sentence_before_is_skipped():
    from ocarina.tts.worker import first_speech  # pylint: disable=import-outside-toplevel

    # sound before the start and a little after it (the end of the last word), then 1.1 s of quiet, then the sentence
    assert first_speech(_frames((30, 55), (165, 400)), 50, 450) == 165
    # a start right after a pause, on a short word followed by a comma pause: that is the sentence, not a tail
    assert first_speech(_frames((50, 90), (130, 400)), 50, 450) == 50
    # a long stretch of sound is the sentence itself, whatever follows
    assert first_speech(_frames((30, 150), (300, 400)), 50, 450) == 50
    # a click in the pause is not the next sentence
    assert first_speech(_frames((30, 55), (65, 68), (165, 400)), 50, 450) == 165
    # a tail with nothing after it stays
    assert first_speech(_frames((30, 55)), 50, 450) == 50
