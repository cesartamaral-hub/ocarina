"""
Sync a recording with the text without any model: find the pauses in the sound and match them to the sentence breaks.

    detect_pauses(path)                      -> (duration, [(start, end), ...]) from the loudness of the decoded sound
    match_pauses(weights, duration, pauses)  -> the start of every sentence (seconds), or None when the pauses do not fit

A narrator pauses between sentences, so a sentence starts where speech resumes after a pause. Which pauses are sentence breaks
and which are commas is decided by length: the sentences have a length in the text (their weight), speech has a steady pace, so
the sentence i should take about pace * weight[i] seconds. A dynamic programme chooses the n-1 pauses whose spacing is the
closest to that, with a small reward for long pauses. It is approximate by design: the aligner model is more precise.
"""

import subprocess

from ocarina import tools

NOISE_DB = -35  # below this level it is silence
MIN_PAUSE = 0.15  # seconds of silence that count as a pause
LONG_PAUSE_REWARD = 1.2  # how much a long pause attracts a sentence start (seconds of timing error it is worth)
RATE = 16000  # samples per second the recording is decoded to
LEAD_IN = 0.08  # a sentence starts a little ahead of the first sound, like the aligner's


class PauseSyncError(Exception):
    "The pauses could not be found or did not fit the text; the message says it in plain words."


def detect_pauses(path, noise_db=NOISE_DB, min_pause=MIN_PAUSE):
    """
    (duration, [(start, end), ...]) of the silences in an audio file; the last one may run to the end. ffmpeg only decodes (the one
    inside the app is a small build without the silencedetect filter); the loudness is read here, in frames of 10 ms.
    """
    import numpy as np  # pylint: disable=import-outside-toplevel

    ffmpeg = tools.ffmpeg()
    if not ffmpeg:
        raise PauseSyncError("ffmpeg is needed to find the pauses and was not found.")
    done = subprocess.run(
        [ffmpeg, "-v", "error", "-i", path, "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
        capture_output=True,
        check=False,
        timeout=900,
    )
    samples = np.frombuffer(done.stdout[: len(done.stdout) // 2 * 2], dtype="<i2")
    if done.returncode != 0 or len(samples) == 0:
        raise PauseSyncError("This audio file could not be read.")
    duration = len(samples) / RATE
    frame = RATE // 100
    count = len(samples) // frame
    loud = np.sqrt(np.mean((samples[: count * frame].astype(np.float32) / 32768.0).reshape(count, frame) ** 2, axis=1))
    silent = loud < 10 ** (noise_db / 20)
    pauses, start = [], None
    for i, quiet in enumerate(silent):
        if quiet and start is None:
            start = i
        elif not quiet and start is not None:
            if (i - start) / 100 >= min_pause:
                pauses.append((start / 100, i / 100))
            start = None
    if start is not None and (count - start) / 100 >= min_pause:
        pauses.append((start / 100, duration))  # silence up to the end of the file
    return duration, pauses


def _speech_bounds(duration, pauses):
    "Where the speech starts and ends: after a leading silence, before a trailing one."
    speech_from = pauses[0][1] if pauses and pauses[0][0] <= 0.05 else 0.0
    speech_to = pauses[-1][0] if pauses and pauses[-1][1] >= duration - 0.05 else duration
    return speech_from, speech_to


def _match(weights, speech_from, speech_to, pauses):
    "The start of each sentence of weights, speech running from speech_from to speech_to; None when the pauses are too few."
    n = len(weights)
    if n == 0:
        return []
    inner = [p for p in pauses if p[0] > speech_from + 0.05 and p[1] < speech_to - 0.05]
    if n == 1:
        return [max(speech_from - LEAD_IN, 0.0)]
    if len(inner) < n - 1:
        return None
    total = float(sum(weights)) or 1.0
    pace = (speech_to - speech_from) / total  # seconds per unit of weight, pauses included
    resume = [p[1] for p in inner]  # a sentence starts where speech resumes
    bonus = [LONG_PAUSE_REWARD * min(p[1] - p[0], 1.0) for p in inner]
    cands = len(inner)
    inf = float("inf")
    # best[i][k]: the least cost with sentence i starting at pause k; sentence 0 starts at speech_from
    best = [[inf] * cands for _ in range(n)]
    back = [[-1] * cands for _ in range(n)]

    def cost(observed, i):
        expected = max(pace * weights[i], 0.2)
        return (observed - expected) ** 2 / expected

    for k in range(cands):
        best[1][k] = cost(resume[k] - speech_from, 0) - bonus[k]
    for i in range(2, n):
        for k in range(i - 1, cands):
            for j in range(i - 2, k):
                if best[i - 1][j] == inf:
                    continue
                c = best[i - 1][j] + cost(resume[k] - resume[j], i - 1) - bonus[k]
                if c < best[i][k]:
                    best[i][k], back[i][k] = c, j
    last = inf, -1
    for k in range(n - 2, cands):
        if best[n - 1][k] < inf:
            c = best[n - 1][k] + cost(speech_to - resume[k], n - 1)
            if c < last[0]:
                last = c, k
    if last[1] < 0:
        return None
    chosen = [0] * (n - 1)
    k = last[1]
    for i in range(n - 1, 0, -1):
        chosen[i - 1] = k
        k = back[i][k]
    return [max(speech_from - LEAD_IN, 0.0)] + [max(resume[k] - LEAD_IN, 0.0) for k in chosen]


def match_pauses(weights, duration, pauses):
    "Start time of every sentence (weights: the speech each holds, e.g. its characters), or None when there are too few pauses."
    speech_from, speech_to = _speech_bounds(duration, pauses)
    starts = _match(weights, speech_from, speech_to, pauses)
    return None if starts is None else [round(x, 3) for x in starts]


def proportional_starts(weights, speech_from, speech_to):
    "A plain guess: sentences share the time in proportion to their weight."
    total = float(sum(weights)) or 1.0
    starts, at = [], speech_from
    for w in weights:
        starts.append(round(at, 3))
        at += (speech_to - speech_from) * w / total
    return starts


def fit(weights, duration, pauses, pins=None):
    """
    (starts, how) for every sentence. pins: {sentence index: time} the user fixed; between two pins the pauses are matched on their
    own, so one correction cannot shift the rest of the recording. `how` is "pauses" when every stretch was matched to pauses, else
    "estimate" (some stretch had too few pauses and was spread by length).
    """
    speech_from, speech_to = _speech_bounds(duration, pauses)
    n = len(weights)
    pinned = {int(i): float(t) for i, t in (pins or {}).items() if 0 <= int(i) < n}
    marks = {0: speech_from, **pinned}
    edges = sorted(marks)
    starts = [0.0] * n
    how = "pauses"
    for a, b in zip(edges, edges[1:] + [n]):
        begin = marks[a]
        end = marks[edges[edges.index(a) + 1]] if b < n else speech_to
        found = _match(weights[a:b], begin, end, pauses)
        if found is None:
            found, how = proportional_starts(weights[a:b], begin, end), "estimate"
        if a in pinned:
            found[0] = begin  # a time the user gave is used as it is
        starts[a:b] = found
    return [round(x, 3) for x in starts], how


def suspect_indexes(weights, starts, duration):
    "Sentences whose length in time is far from what their text suggests (a sign they were not placed right)."
    pace = (duration - starts[0]) / (float(sum(weights)) or 1.0)
    bad = []
    for i, w in enumerate(weights):
        length = (starts[i + 1] if i + 1 < len(starts) else duration) - starts[i]
        expected = max(pace * w, 0.3)
        if length > 3 * expected or length < expected / 3:
            bad.append(i)
    return bad


def sync_book_audio_pauses(book, audio_dir, filename, language, pins=None, check=None):
    """
    Match a recording to a book's text by its pauses and write the timings file (marked approximate). `pins` ({sentence: time}) are
    times the user fixed. Returns (suspect sentence indexes, how), how being "pauses" or "estimate".
    """
    import json  # pylint: disable=import-outside-toplevel
    import os  # pylint: disable=import-outside-toplevel

    from ocarina.audio_sync import SyncError  # pylint: disable=import-outside-toplevel
    from ocarina.tts.book_audio import book_sentences, timings_info, timings_path  # pylint: disable=import-outside-toplevel

    sentences = book_sentences(book)
    if not sentences:
        raise SyncError("The book has no text to sync.")
    path = os.path.join(audio_dir, filename)
    info = timings_info(audio_dir, filename) or {}
    if check:
        check()
    if info.get("pauses") and info.get("duration"):  # found before: only the pins changed
        duration, pauses = info["duration"], [tuple(p) for p in info["pauses"]]
    else:
        try:
            duration, pauses = detect_pauses(path)
        except PauseSyncError as e:
            raise SyncError(str(e)) from e
    weights = [max(1, len("".join(s["text"].split()))) for s in sentences]
    pins = {int(i): float(t) for i, t in (pins or {}).items()}
    starts, how = fit(weights, duration, pauses, pins)
    suspect = suspect_indexes(weights, starts, duration)
    if len(suspect) > max(2, len(sentences) // 3):
        raise SyncError("The recording does not seem to match this text: many sentences could not be placed. Is it the right recording, and is the text the same?")
    for s, start in zip(sentences, starts):
        s["start"] = start
    with open(timings_path(path), "w", encoding="utf-8") as f:
        json.dump(
            {"aligned": True, "aligner": "pauses", "method": how, "approximate": True, "language": language, "pins": {str(i): t for i, t in pins.items()},
             "duration": duration, "pauses": pauses, "sentences": sentences},
            f,
            ensure_ascii=False,
        )
    return suspect, how
