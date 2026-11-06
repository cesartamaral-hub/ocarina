"""
Timings from a subtitle file (SRT, WebVTT or LRC) that goes with a recording: each cue says when some words are said, so the sentence
starts follow from where the sentence's first words sit in the cues.

    parse(text)                       -> [(start, end or None, text), ...]
    sentence_starts(sentences, cues)  -> the start of every sentence, or None when the subtitles do not match the text
"""

import re
import unicodedata

TIME = r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})"
ARROW = re.compile(TIME + r"\s*-->\s*" + TIME)
LRC = re.compile(r"^\[(\d+):(\d{2})(?:[.:](\d{1,3}))?\](.*)$")
MIN_MATCHED = 0.6  # share of sentences that must be found in the cues


def _seconds(h, m, s, frac):
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(frac.ljust(3, "0")[:3]) / 1000


def parse(text):
    "The cues of an SRT, WebVTT or LRC file: (start seconds, end seconds or None, text)."
    cues = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip().lstrip("﻿")
        m = ARROW.search(line)
        if m:
            g = m.groups()
            start, end = _seconds(*g[:4]), _seconds(*g[4:])
            body = []
            i += 1
            while i < len(lines) and lines[i].strip():
                body.append(re.sub(r"<[^>]+>", "", lines[i].strip()))
                i += 1
            if body:
                cues.append((start, end, " ".join(body)))
            continue
        lrc = LRC.match(line)
        if lrc and lrc.group(4).strip():
            frac = lrc.group(3) or "0"
            cues.append((int(lrc.group(1)) * 60 + int(lrc.group(2)) + int(frac.ljust(3, "0")[:3]) / 1000, None, lrc.group(4).strip()))
        i += 1
    cues.sort(key=lambda c: c[0])
    # an LRC line ends where the next one starts
    return [(s, e if e is not None else (cues[k + 1][0] if k + 1 < len(cues) else None), t) for k, (s, e, t) in enumerate(cues)]


def _words(text):
    out = []
    for token in text.split():
        cleaned = "".join(c for c in token.lower() if c == "'" or unicodedata.category(c)[0] in "LN")
        if cleaned:
            out.append(cleaned)
    return out


def sentence_starts(sentences, cues):
    """
    The start of each sentence (sentences: list of text). A sentence is found by its first words in the cues' words, in order; where
    inside a cue it begins is guessed from the word's position. Sentences not found take a time between their neighbours.
    Returns None when too few are found.
    """
    flat = []  # (word, cue index, position in the cue, words in the cue)
    for k, (_, _, text) in enumerate(cues):
        words = _words(text)
        flat.extend((w, k, p, len(words)) for p, w in enumerate(words))
    found, at = [], 0
    for text in sentences:
        words = _words(text)[:3]
        hit = None
        if words:
            for j in range(at, len(flat) - len(words) + 1):
                if all(flat[j + x][0] == words[x] for x in range(len(words))):
                    hit = j
                    break
        if hit is None:
            found.append(None)
            continue
        _, k, pos, count = flat[hit]
        start, end, _ = cues[k]
        end = end if end is not None else start + 3.0
        found.append(start + (end - start) * pos / max(count, 1))
        at = hit + 1
    matched = sum(1 for f in found if f is not None)
    if not sentences or matched / len(sentences) < MIN_MATCHED:
        return None
    times = list(found)
    for i, t in enumerate(times):  # fill the gaps from the nearest known neighbours
        if t is None:
            before = next(((j, times[j]) for j in range(i - 1, -1, -1) if times[j] is not None), (-1, 0.0))
            after = next(((j, times[j]) for j in range(i + 1, len(times)) if times[j] is not None), (len(times), before[1]))
            span = after[0] - before[0]
            times[i] = before[1] + (after[1] - before[1]) * (i - before[0]) / span
    return [round(max(t - 0.05, 0.0), 3) for t in times]
