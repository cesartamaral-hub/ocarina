"""
Wiktionary packs: the entries of one language from the structured Wiktionary data of Wiktextract (kaikki.org), as packs.

Each line of the data is one entry: {word, pos, lang_code, senses: [{glosses, examples, form_of, tags}], forms: [{form, tags}], ...}. A pack keeps
the word, its part of speech, the meanings with up to two examples, and the inflected forms with the base form they belong to, so that a form
you meet in a text leads to the meaning of its base form.
"""

import json
import re

import requests

from ocarina.dictionaries import pack

LANGUAGE_NAMES = {"nl": "Dutch", "pl": "Polish", "fr": "French"}
URL = "https://kaikki.org/dictionary/{name}/kaikki.org-dictionary-{name}.jsonl"
LICENSE = "CC BY-SA 4.0 (Wiktionary, data by Wiktextract)"
MAX_SENSES = 10
MAX_EXAMPLES = 2
MAX_FORMS = 80
SKIP_FORM_TAGS = {"table-tags", "inflection-template", "class", "romanization", "pinyin"}
SKIP_SENSE_TAGS = {"form-of", "alt-of", "error-unrecognized-form", "no-gloss"}


def _example(example):
    text = (example.get("text") or "").strip()
    translation = (example.get("english") or example.get("translation") or "").strip()
    return f"{text} — {translation}" if text and translation else text


def sense_of(sense):
    "{text, examples} for one sense of an entry, or None when it has no words."
    glosses = [g.strip() for g in (sense.get("glosses") or []) if g and g.strip()]
    if not glosses:
        return None
    text = glosses[-1] if len(glosses) == 1 else f"{glosses[-1]} ({glosses[0]})"
    tags = [t for t in (sense.get("tags") or []) if t not in SKIP_SENSE_TAGS][:2]
    if tags:
        text = f"({', '.join(tags)}) {text}"
    examples = [e for e in (_example(x) for x in (sense.get("examples") or [])) if e][:MAX_EXAMPLES]
    return {"text": text, "examples": examples}


def entry_from(line, code):
    "(word, pos, senses, forms [(form, lemma)]) from one line of data, or None when it is not an entry of the language."
    if line.get("lang_code") not in (None, code) or not line.get("word"):
        return None
    word = line["word"]
    senses, forms = [], []
    for s in line.get("senses") or []:
        made = sense_of(s)
        if made:
            senses.append(made)
        for target in (s.get("form_of") or []) + (s.get("alt_of") or []):
            lemma = (target or {}).get("word")
            if lemma:
                forms.append((word, lemma))
    for f in (line.get("forms") or [])[: MAX_FORMS * 2]:
        form = (f.get("form") or "").strip()
        if not form or form == word or set(f.get("tags") or []) & SKIP_FORM_TAGS or re.search(r"[—|]|^-|-$", form) or len(form) > 40:
            continue
        forms.append((form, word))
        if len(forms) >= MAX_FORMS:
            break
    if not senses and not forms:
        return None
    return word, line.get("pos") or "", senses[:MAX_SENSES], forms


def convert_lines(lines, destination, code, meta, on_progress=None):
    "Build a pack from the lines (bytes or str) of a Wiktextract file; returns the number of entries."
    db = pack.create(destination, {"language": code, "meaning": meta.get("meaning", "en"), "license": LICENSE, "source": "https://kaikki.org", "kind": "wiktionary", **meta})
    seen_forms = set()
    count = 0
    wanted = f'"lang_code": "{code}"'.encode()
    for raw in lines:
        if on_progress:
            on_progress(len(raw))
        if wanted not in (raw if isinstance(raw, bytes) else raw.encode()):
            continue  # an edition holds words of every language: only this language's are read
        try:
            line = json.loads(raw)
        except ValueError:
            continue
        made = entry_from(line, code)
        if made is None:
            continue
        word, pos, senses, forms = made
        if senses:
            db.execute(
                "insert into entry (word, word_lc, pos, importance, senses) values (?, ?, ?, 0, ?)",
                (word, pack.fold(word), pos, json.dumps(senses, ensure_ascii=False)),
            )
            count += 1
        for form, lemma in forms:
            key = (pack.fold(form), pack.fold(lemma))
            if key[0] != key[1] and key not in seen_forms:
                seen_forms.add(key)
                db.execute("insert into form values (?, ?)", key)
    pack.finish(db)
    return count


def stream(url, check=None, chunk=1 << 20):
    "(total bytes, an iterator over the lines of a file at an address, read as it arrives)."
    response = requests.get(url, stream=True, timeout=30, headers={"User-Agent": "Ocarina/1.0 (personal language-learning app)"})
    response.raise_for_status()
    total = int(response.headers.get("Content-Length") or 0)

    def lines():
        pending = b""
        for block in response.iter_content(chunk):
            if check:
                check()
            pending += block
            *whole, pending = pending.split(b"\n")
            yield from whole
        if pending.strip():
            yield pending

    return total, lines()
