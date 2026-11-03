"""
Turn text into sentence audio: split, reuse cached sentences, and
synthesize only what is missing.
"""

import os
import time

from ocarina.tts.cache import SentenceCache, file_digest
from ocarina.tts.sentences import split_sentences

DEFAULT_VOICE = os.path.join(os.path.dirname(__file__), "voices", "default.wav")


def synthesize_text(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    supervisor, cache, model_id, text, lang, voice=DEFAULT_VOICE, on_sentence=None
):
    """
    Return a list of (sentence, wav_path, was_cached) for the text.

    on_sentence(index, total, sentence, wav_path, cached, seconds) is
    called after each sentence so a UI can start playing early.
    """
    sentences = split_sentences(text)
    digest = file_digest(voice)
    result = []
    for i, sentence in enumerate(sentences):
        path = cache.get(model_id, lang, digest, sentence)
        cached = path is not None
        t = time.time()
        if not cached:
            path = cache.path_for(model_id, lang, digest, sentence)
            supervisor.synth(sentence, lang, voice, path)
        result.append((sentence, path, cached))
        if on_sentence:
            on_sentence(i, len(sentences), sentence, path, cached, time.time() - t)
    return result


__all__ = ["synthesize_text", "SentenceCache", "DEFAULT_VOICE"]
