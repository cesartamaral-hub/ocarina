"""
Per-sentence audio cache: the same sentence, language, model and
voice always maps to the same wav file, so edits regenerate only
what changed.
"""

import hashlib
import os


def file_digest(path):
    "Hex digest of a file's contents (identifies a reference voice)."
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class SentenceCache:
    "Wav files on disk, keyed by model, language, voice and text."

    def __init__(self, cache_dir):
        self.cache_dir = cache_dir

    def path_for(self, model_id, lang, voice_digest, text):
        "Cache path for one sentence (the file may not exist yet)."
        key = "\n".join([model_id, lang, voice_digest, text])
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, digest[:2], digest + ".wav")

    def get(self, model_id, lang, voice_digest, text):
        "Cached path if present, else None."
        p = self.path_for(model_id, lang, voice_digest, text)
        return p if os.path.exists(p) else None
