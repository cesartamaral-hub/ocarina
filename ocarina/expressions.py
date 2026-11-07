"""
Combinations of words. A selection of several words can mean something its words do not mean one by one ("ook al": even though), so
the dictionaries are asked for the selection as a whole, and for the runs of words inside it, longest first, and for each word.
"""

import re

from ocarina.dictionaries import registry
from ocarina.dictionaries.pack import fold

MAX_WORDS = 8  # a longer selection is a sentence, not an expression
MAX_PARTS = 6

_EDGES = re.compile(r"^[^\w]+|[^\w]+$")


def words_of(text):
    "The words of a selection, without the punctuation around them."
    return [w for w in (_EDGES.sub("", raw) for raw in re.split(r"\s+", (text or "").replace("​", "").strip())) if w]


def runs(text):
    """
    Everything worth looking up inside a selection, longest first: the runs of two or more words (the whole selection first), then the
    single words. [] for a selection of one word or one that is too long to be an expression.
    """
    words = words_of(text)
    if len(words) < 2 or len(words) > MAX_WORDS:
        return []
    found = []
    for size in range(len(words), 0, -1):
        for start in range(len(words) - size + 1):
            found.append(" ".join(words[start : start + size]))
    return found


def parts(datapath, code, text):
    """
    What the dictionaries on this Mac know inside a selection: [{text, words, source: {id, name, license, offline}, entries}], longest runs
    first, at most MAX_PARTS. The pack that comes first in the user's order and knows a run answers for it. The whole selection is left
    out (the dictionary lookup of the selection already answers for it).
    """
    whole = fold(" ".join(words_of(text)))
    out, seen = [], set()
    for run in runs(text):
        key = fold(run)
        if key == whole or key in seen:
            continue
        seen.add(key)
        for pack in registry.active(datapath, code):
            entries = pack.entries(run)
            if entries:
                info = pack.info()
                out.append({"text": run, "words": len(run.split()), "source": {"id": info["id"], "name": info["name"], "license": info["license"], "offline": True}, "entries": entries})
                break
        if len(out) >= MAX_PARTS:
            break
    return out
