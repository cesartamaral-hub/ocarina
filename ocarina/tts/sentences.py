"""
Split text into sentences for per-sentence audio generation.
"""

import re

_SPLIT = re.compile(r"(?<=[.!?…])[\"'»”’)\]]*\s+|\n+")


def split_sentences(text):
    "Split text into non-empty sentences, one paragraph break or sentence end at a time."
    parts = (p.strip() for p in _SPLIT.split(text or ""))
    return [p for p in parts if p]
