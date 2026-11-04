"""
Sync a recording with the book's text: find when each sentence starts, so the reader can follow along.

A forced aligner is given the audio and exactly what is said in it, and places every word in time. Long recordings
are aligned window by window (the model works on a few minutes at a time): each window gets more text than it will
probably hold, and only the sentences that end well inside the window are kept; the next window starts at the first
sentence that was not kept.
"""

import json
import math
import os
import re
import unicodedata

from ocarina.tts.book_audio import book_sentences, timings_path

ALIGNER_ID = "qwen3-forced-aligner-mlx"
WINDOW = 240.0  # seconds of audio per call; the model's own limit is about 5 minutes
KEEP = 0.75  # keep the sentences that end within this share of a window; the rest are aligned again, next window
FIRST_WORDS_PER_SECOND = 2.6  # a first guess of how fast the narrator speaks, until a window shows it
MORE_TEXT = 1.4  # offer this much more text than the speech rate suggests, so a window never runs out of text
LEAD_IN = 0.08  # seconds a sentence's start is placed ahead of the first sound, so the highlight is never late
MIN_WORD, MAX_WORD = 0.04, 2.5  # seconds per word, outside which a sentence is probably misplaced


def aligner_engine(engine):
    "The worker engine for the aligner; tests that fake every engine get the fake aligner."
    return "fake-aligner" if engine == "fake" else (engine or "mlx-aligner")


class SyncError(Exception):
    "The recording could not be synced; the message says why in plain words."


def words_of(text):
    "The words the aligner will find in a text: runs of letters, digits and apostrophes between spaces."
    out = []
    for token in text.split():
        cleaned = "".join(c for c in token if c == "'" or unicodedata.category(c)[0] in "LN")
        if cleaned:
            out.append(cleaned)
    return out


def _window_sentences(tokens, first, wanted):
    "How many sentences from `first` on hold at least `wanted` words (at least one)."
    count, total = 0, 0
    while first + count < len(tokens) and (count == 0 or total < wanted):
        total += len(tokens[first + count])
        count += 1
    return count


def align_sentences(sentences, aligner, audio, check=None, on_progress=None, window=WINDOW):
    """
    Start and end time of every sentence. sentences: list of {"text": ...}; aligner has duration(audio) and
    align(audio, offset, length, text) -> [[word, start, end], ...]. Returns a list of (start, end) per sentence
    (None for one without words).
    """
    tokens = [words_of(s["text"]) for s in sentences]
    spans = [None] * len(sentences)
    total_time = aligner.duration(audio)
    first, offset, rate = 0, 0.0, FIRST_WORDS_PER_SECOND
    while first < len(sentences):
        if check:
            check()
        length = min(window, total_time - offset)
        if length < 0.5:
            raise SyncError("The audio ends before the text does. Is this the recording of this text?")
        last_window = offset + length >= total_time - 0.01
        remaining = sum(len(t) for t in tokens[first:])
        wanted = remaining if last_window else math.ceil(rate * length * MORE_TEXT)
        n = len(sentences) - first if last_window else _window_sentences(tokens, first, wanted)
        text = " ".join(s["text"] for s in sentences[first : first + n])
        words = aligner.align(audio, offset, length, text)
        expected = sum(len(t) for t in tokens[first : first + n])
        if len(words) != expected:
            raise SyncError("The aligner and Ocarina split the text into words differently. This text cannot be synced.")
        # Cut the words into sentences.
        at, found = 0, []
        for t in tokens[first : first + n]:
            chunk = words[at : at + len(t)]
            at += len(t)
            found.append((chunk[0][1], chunk[-1][2]) if chunk else None)
        keep_until = offset + length * KEEP
        accepted = n if last_window else sum(1 for _ in _leading(found, keep_until)) or 1
        if not last_window and found[accepted - 1] is not None and found[accepted - 1][1] > offset + length * 0.98:
            raise SyncError("A sentence is longer than the part of the audio being checked. This text cannot be synced.")
        for i in range(accepted):
            spans[first + i] = found[i]
        done = [f for f in found[:accepted] if f]
        if done and done[-1][1] > done[0][0]:
            rate = sum(len(t) for t in tokens[first : first + accepted]) / (done[-1][1] - done[0][0])
        first += accepted
        if first < len(sentences):
            offset = max(spans[first - 1][1] if spans[first - 1] else offset, (found[accepted][0] if found[accepted] else offset) - 0.2)
        if on_progress:
            on_progress(first, len(sentences))
    return spans


def _leading(found, until):
    "The leading spans that end by `until` (blank sentences, with no words, ride along)."
    for span in found:
        if span is not None and span[1] > until:
            return
        yield span


def refine_starts(spans, aligner, audio):
    """
    The aligner starts a word where the one before it ended, and after a pause it can pile words onto silence or onto
    the end of the sentence before, so a sentence would start while the narrator is quiet or still on the one before.
    Move each start forward to the first real sound between its start and its end (see the worker's first_speech), a
    little ahead of it. Starts never move back.
    """
    wanted = [(i, s) for i, s in enumerate(spans) if s is not None]
    onsets = aligner.onsets(audio, [[s[0], s[1]] for _, s in wanted]) if wanted else []
    refined = list(spans)
    for (i, (start, end)), onset in zip(wanted, onsets):
        refined[i] = (min(max(start, onset - LEAD_IN), end), end)
    return refined


def suspect_sentences(sentences, spans):
    "Indexes of sentences whose timing looks wrong: far too quick or too slow for their number of words."
    bad = []
    for i, (s, span) in enumerate(zip(sentences, spans)):
        n = len(words_of(s["text"]))
        if span is None or n == 0:
            continue
        per_word = (span[1] - span[0]) / n
        if per_word < MIN_WORD or per_word > MAX_WORD:
            bad.append(i)
    return bad


def sync_book_audio(book, audio_dir, filename, aligner, language, check=None, on_progress=None, window=WINDOW):
    "Align a book's text with an audio file in audio_dir and write its timings file; returns the suspect sentences."
    sentences = book_sentences(book)
    if not sentences:
        raise SyncError("The book has no text to sync.")
    path = os.path.join(audio_dir, filename)
    spans = refine_starts(align_sentences(sentences, aligner, path, check, on_progress, window), aligner, path)
    for s, span in zip(sentences, spans):
        s["start"] = round(span[0], 2) if span else None
    # A blank sentence has no words to place: it starts where the one before it does.
    for i, s in enumerate(sentences):
        if s["start"] is None:
            s["start"] = sentences[i - 1]["start"] if i else 0.0
    suspect = suspect_sentences(sentences, spans)
    if len(suspect) > max(2, len(sentences) // 5):
        raise SyncError("The recording does not seem to match this text: many sentences could not be placed. Is it the right recording, and is the text the same?")
    with open(timings_path(os.path.join(audio_dir, filename)), "w", encoding="utf-8") as f:
        json.dump({"aligned": True, "aligner": ALIGNER_ID, "language": language, "sentences": sentences}, f, ensure_ascii=False)
    return suspect
