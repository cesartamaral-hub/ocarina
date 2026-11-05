"""Asking the packs of a language for a word."""

from ocarina.dictionaries import registry

MAX_LEMMAS = 2


def lookup(datapath, code, word):
    """
    What each pack that is on knows about a word: [{pack: info, entries, lemmas: [{word, entries}]}], in the user's order; packs that
    know nothing of it are left out. An inflected form points to its base forms when the pack has them.
    """
    found = []
    for pack in registry.active(datapath, code):
        entries = pack.entries(word)
        lemmas = []
        for lemma in pack.lemmas(word)[:MAX_LEMMAS]:
            lemma_entries = pack.entries(lemma)
            if lemma_entries:
                lemmas.append({"word": lemma, "entries": lemma_entries})
        if entries or lemmas:
            found.append({"pack": pack.info(), "entries": entries, "lemmas": lemmas})
    return found
