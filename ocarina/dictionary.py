"""
Word definitions from Wiktionary (its public REST API), cached on disk.

Lute's dictionaries were web pages shown in a frame, and most sites refuse that. This asks Wiktionary for
data instead: part of speech, definitions and examples, in English, for the language of the book.
Every answer is cached in <data folder>/cache/dictionary, so a word you looked up once is instant and
works without internet; with no connection, an old cached answer is still used.
"""

import hashlib
import html
import json
import os
import re
import time
from urllib.parse import quote

import requests

from ocarina import paths

API = "https://en.wiktionary.org/api/rest_v1/page/definition/"
WIKI = "https://en.wiktionary.org/wiki/"
USER_AGENT = "Ocarina/1.0 (personal language-learning app; https://github.com/cesartamaral-hub/ocarina)"
TIMEOUT = 6
FOUND_TTL = 90 * 24 * 3600  # a definition rarely changes
MISSING_TTL = 2 * 24 * 3600  # a missing entry may appear soon
MAX_WORD = 100
MAX_ENTRIES, MAX_DEFINITIONS, MAX_EXAMPLES = 4, 6, 2

# Lute names some languages in their own language; Wiktionary's section names are English.
SECTION_NAMES = {"polski": "Polish", "nederlands": "Dutch", "français": "French", "francais": "French"}


class DictionaryError(Exception):
    "The lookup could not be done; the message says why. offline: Wiktionary could not be reached or failed."

    def __init__(self, message, offline=False):
        super().__init__(message)
        self.offline = offline


def section_name(language_name):
    "The name Wiktionary uses for a Lute language."
    return SECTION_NAMES.get(language_name.strip().lower(), language_name.strip())


_TAG = re.compile(r"<[^>]+>")
# "inflection of <a title="szkoła">szkoła</a>": the link inside a form-of definition names the base form.
_LEMMA = re.compile(r'form-of-definition-link.*?title="([^"#]+)"', re.S)
MAX_LEMMAS = 2


_NESTED = re.compile(r"<(ol|ul)\b.*", re.S)  # from the first nested list on (its closing tag is often missing)


def _plain(markup):
    "Wiktionary sends definitions as HTML: keep the text only, and leave out nested sub-senses (lists inside it)."
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub("", _NESTED.sub("", markup or "")))).strip()


def parse(payload, section):
    "Entries of one language from a Wiktionary definition payload: [{partOfSpeech, definitions: [...]}]."
    entries = []
    for group in payload.values():
        for entry in group:
            if str(entry.get("language", "")).lower() != section.lower():
                continue
            definitions = []
            for d in entry.get("definitions", []):
                text = _plain(d.get("definition"))
                if not text:
                    continue
                examples = [_plain(e) for e in d.get("examples", []) if _plain(e)]
                examples += [_plain(e.get("example")) for e in d.get("parsedExamples", []) if _plain(e.get("example"))]
                item = {"text": text, "examples": list(dict.fromkeys(examples))[:MAX_EXAMPLES]}
                lemma = _LEMMA.search(d.get("definition") or "")
                if lemma:
                    item["lemma"] = html.unescape(lemma.group(1))
                definitions.append(item)
            if definitions:
                entries.append({"partOfSpeech": entry.get("partOfSpeech", ""), "definitions": definitions[:MAX_DEFINITIONS]})
    return entries[:MAX_ENTRIES]


def _cache_path(datapath, section, word):
    key = hashlib.sha256(f"{section}\n{word}".encode("utf-8")).hexdigest()
    return os.path.join(paths.cache(datapath, "dictionary"), key[:2], key + ".json")


def _read_cache(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_cache(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)  # never a half-written file


def _fetch(word, section):
    "Ask Wiktionary for one spelling; returns its entries for the language (empty if none)."
    try:
        response = requests.get(API + quote(word, safe=""), headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        raise DictionaryError("No connection to Wiktionary.", offline=True) from e
    if response.status_code == 404:
        return []
    if response.status_code != 200:
        raise DictionaryError(f"Wiktionary answered with an error ({response.status_code}).", offline=True)
    try:
        return parse(response.json(), section)
    except ValueError as e:
        raise DictionaryError("Wiktionary sent an answer that could not be read.", offline=True) from e


def _spellings(word):
    "The word as given, then in lower case, then with a plain apostrophe."
    seen = []
    for candidate in (word, word.lower(), word.lower().replace("’", "'")):
        if candidate not in seen:
            seen.append(candidate)
    return seen


def _lemmas(entries, section):
    """
    Base forms named by inflected-form definitions ("inflection of szkoła"), with their own meanings, so that
    looking up an inflected word shows what it means. One level only. A failure here is not an error: the
    inflected word's own entry is still useful.
    """
    names = []
    for entry in entries:
        for d in entry["definitions"]:
            if d.get("lemma") and d["lemma"] not in names:
                names.append(d["lemma"])
    found = []
    for name in names[:MAX_LEMMAS]:
        try:
            lemma_entries = _fetch(name, section)
        except DictionaryError:
            continue
        if lemma_entries:
            found.append({"word": name, "entries": lemma_entries})
    return found


def define_online(datapath, language_name, word, cache_only=False):
    """
    Definitions of a word from Wiktionary (kept on this Mac): {found, word, entries, lemmas, url, cached, stale}.
    cache_only never uses the network (None when the word is not cached). Raises DictionaryError when
    Wiktionary can't be reached and nothing was cached.
    """
    word = re.sub(r"\s+", " ", (word or "").replace("​", "")).strip()
    if not word or len(word) > MAX_WORD:
        raise DictionaryError("Give a word or phrase of up to %d characters." % MAX_WORD)
    section = section_name(language_name)
    path = _cache_path(datapath, section, word)
    cached = _read_cache(path)
    now = time.time()
    if cached:
        # An entry saved before base forms existed has no "lemmas": fetch it again (it is still the offline fallback).
        fresh = "lemmas" in cached and now - cached["fetched"] < (FOUND_TTL if cached["found"] else MISSING_TTL)
        if fresh or cache_only:
            return {**cached, "cached": True, "stale": not fresh}
    if cache_only:
        return None
    try:
        matched, entries = word, []
        for spelling in _spellings(word):
            entries = _fetch(spelling, section)
            if entries:
                matched = spelling
                break
    except DictionaryError:
        if cached:  # old data is better than none when offline
            return {**cached, "cached": True, "stale": True}
        raise
    result = {
        "found": bool(entries),
        "word": matched,
        "entries": entries,
        "lemmas": _lemmas(entries, section),
        "url": f"{WIKI}{quote(matched.replace(' ', '_'), safe='/')}#{quote(section)}",
        "fetched": now,
    }
    _write_cache(path, result)
    return {**result, "cached": False, "stale": False}


WIKTIONARY = {"id": "wiktionary", "name": "Wiktionary", "license": "CC BY-SA", "offline": False}


def _source(pack):
    return {"id": pack["id"], "name": pack["name"], "license": pack["license"], "offline": True}


def _clean(word):
    word = re.sub(r"\s+", " ", (word or "").replace("\u200b", "")).strip()
    if not word or len(word) > MAX_WORD:
        raise DictionaryError("Give a word or phrase of up to %d characters." % MAX_WORD)
    return word


def define(datapath, language_name, word, cache_only=False, online=False):
    """
    What the dictionaries say about a word: {found, word, entries, lemmas, url, cached, stale, source, others}. The dictionaries on this Mac
    (packs, see ocarina/dictionaries) are asked first, in the user's order: the first that knows the word is the answer and the others
    that know it come in `others`, each with its own source. Only when none does (or with online=True) Wiktionary is asked over the
    internet; that answer is kept on this Mac, and works offline from then on. cache_only never uses the network.
    """
    from ocarina import offline, translate  # pylint: disable=import-outside-toplevel,cyclic-import
    from ocarina.dictionaries import lookup  # pylint: disable=import-outside-toplevel

    word = _clean(word)
    if offline.is_on():  # only what is on this Mac: the dictionaries, and what was looked up on Wiktionary before
        cache_only, online = True, False
    code = translate.code_for(language_name)
    local = lookup.lookup(datapath, code, word) if code else []
    if not local:
        result = define_online(datapath, language_name, word, cache_only)
        return {**result, "source": WIKTIONARY, "others": []} if result is not None else None
    first = local[0]
    others = [{"source": _source(r["pack"]), "entries": r["entries"], "lemmas": r["lemmas"]} for r in local[1:]]
    if online and not cache_only:
        try:
            wiki = define_online(datapath, language_name, word)
        except DictionaryError:
            wiki = None
        if wiki and wiki.get("found"):
            others.append({"source": WIKTIONARY, "entries": wiki["entries"], "lemmas": wiki["lemmas"], "url": wiki["url"], "stale": wiki.get("stale", False)})
    return {
        "found": True,
        "word": word,
        "entries": first["entries"],
        "lemmas": first["lemmas"],
        "url": None,
        "cached": False,
        "stale": False,
        "source": _source(first["pack"]),
        "others": others,
    }
