"""
Join sentence wavs into one audio file with pauses, and report where
each sentence starts (for sentence-level playback and bookmarks).
"""

import numpy as np
import soundfile as sf


def stitch(wav_paths, pause_seconds=0.5):
    """
    Return (samples, sample_rate, starts) for the given wav files.

    starts[i] is the start time in seconds of sentence i.
    """
    pieces, starts, sr, t = [], [], None, 0.0
    for p in wav_paths:
        data, rate = sf.read(p, dtype="float32")
        if sr is None:
            sr = rate
        if rate != sr:
            raise ValueError(f"Sample rate mismatch: {rate} != {sr}")
        starts.append(round(t, 3))
        pause = np.zeros(int(pause_seconds * sr), dtype="float32")
        pieces += [data, pause]
        t += (len(data) + len(pause)) / sr
    if sr is None:
        raise ValueError("No audio to stitch.")
    return np.concatenate(pieces), sr, starts
