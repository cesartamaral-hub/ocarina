"""
WikDict (wikdict.com, CC BY-SA, made from Wiktionary): its small bilingual SQLite dictionaries made into packs.

A WikDict pair file has the table `translation(lexentry, sense_num, sense, written_rep, trans_list, score, is_good, importance)`: one row
per sense of a lexical entry (lexentry looks like "nld/hebben__verb__2", which says the part of speech), with the translations separated
by " | ". Each lexical entry becomes an entry of the pack.
"""

import json
import re
import sqlite3
import urllib.request

from ocarina.dictionaries import languages, pack

URL = "https://download.wikdict.com/dictionaries/sqlite/2/{pair}.sqlite3"
LICENSE = "CC BY-SA 4.0 (Wiktionary, via WikDict)"
POS = re.compile(r"__([a-zA-Z]+)__\d+$")
# The part of speech as the source names it, in English.
POS_NAMES = {
    "adjc": "adjective", "adj": "adjective", "przymiotnik": "adjective", "adverb": "adverb", "adv": "adverb", "przysłówek": "adverb",
    "noun": "noun", "nom": "noun", "rzeczownik": "noun", "verb": "verb", "verbe": "verb", "czasownik": "verb", "czasownikmodalny": "modal verb",
    "name": "proper noun", "nompr": "proper noun", "patronyme": "proper noun", "num": "numeral", "liczebnik": "numeral", "liczebnikzbiorowy": "numeral",
    "ordn": "ordinal", "ordnindef": "ordinal", "numindef": "numeral", "adverbnum": "numeral",
    "abbr": "abbreviation", "phrase": "phrase", "fraza": "phrase", "zwrot": "phrase", "locutionphrase": "phrase", "locution": "phrase",
    "proverbe": "proverb", "interj": "interjection", "interjection": "interjection", "wykrzyknik": "interjection", "wykrzyknienie": "interjection",
    "symbool": "symbol", "symbol": "symbol", "prep": "preposition", "przyimek": "preposition", "conj": "conjunction", "conjonction": "conjunction",
    "pronomindef": "pronoun", "pronadv": "pronoun", "pronompers": "pronoun", "pronompos": "pronoun", "pronomdem": "pronoun", "pronomrel": "pronoun",
    "pronom": "pronoun", "zaimek": "pronoun", "zaimekosobowy": "pronoun", "zaimekpytajny": "pronoun",
    "suff": "suffix", "przyrostek": "suffix", "pref": "prefix", "przedrostek": "prefix", "modulant": "particle",
}


def download(pair, destination):
    "Fetch a pair file (nl-en) to a path."
    request = urllib.request.Request(URL.format(pair=pair), headers={"User-Agent": "Ocarina/1.0 (personal language-learning app)"})
    with urllib.request.urlopen(request, timeout=60) as r, open(destination, "wb") as out:  # nosec - a fixed address
        while chunk := r.read(1 << 20):
            out.write(chunk)


def _text(translations, sense):
    "One line of meanings: 'house; home', with the sense it belongs to in brackets when it has one."
    line = "; ".join(t.strip() for t in translations.split("|") if t.strip())
    note = re.sub(r"^\s*\d+[.)]\s*", "", (sense or "").strip())
    return f"{line} ({note})" if line and note else line


def convert(source_path, destination, code, version="", kind="builtin"):
    "Make a pack from a downloaded WikDict pair file; returns the number of entries."
    src = sqlite3.connect(source_path)
    db = pack.create(
        destination,
        {
            "id": f"wikdict-{code}-en",
            "name": f"WikDict · {languages.name(code)} to English",
            "language": code,
            "meaning": "en",
            "license": LICENSE,
            "source": "https://www.wikdict.com",
            "kind": kind,
            "version": version,
        },
    )
    rows = src.execute(
        "select lexentry, written_rep, sense, trans_list, score, importance from translation where trans_list is not null and trim(trans_list) != '' "
        "order by lexentry, sense_num, score desc"
    )
    entries = {}
    for lexentry, word, sense, translations, score, importance in rows:
        key = (lexentry, word)
        pos = POS.search(lexentry or "")
        entry = entries.setdefault(key, {"pos": POS_NAMES.get(pos.group(1), pos.group(1)) if pos else "", "importance": 0.0, "senses": [], "seen": set()})
        text = _text(translations, sense)
        if text and text not in entry["seen"]:
            entry["seen"].add(text)
            entry["senses"].append({"text": text})
        entry["importance"] = max(entry["importance"], float(importance or 0), float(score or 0) / 1000)
    db.executemany(
        "insert into entry (word, word_lc, pos, importance, senses) values (?, ?, ?, ?, ?)",
        [(word, pack.fold(word), e["pos"], e["importance"], json.dumps(e["senses"], ensure_ascii=False)) for (_, word), e in entries.items() if e["senses"]],
    )
    pack.finish(db)
    src.close()
    return len(entries)


def build_all(builtin_dir, cache_dir, force=False, say=print):
    "Make the packs that come with the app (those missing, or all with force); the downloads are kept in cache_dir."
    import os  # pylint: disable=import-outside-toplevel
    import time  # pylint: disable=import-outside-toplevel

    os.makedirs(cache_dir, exist_ok=True)
    for code in languages.bundled():
        target = os.path.join(builtin_dir, f"wikdict-{code}-en.sqlite")
        if os.path.exists(target) and not force:
            say(f"{code}: already made")
            continue
        raw = os.path.join(cache_dir, f"{code}-en.sqlite3")
        if not os.path.exists(raw) or force:
            say(f"{code}: downloading…")
            download(f"{code}-en", raw)
        count = convert(raw, target, code, version=time.strftime("%Y-%m-%d"))
        say(f"{code}: {count:,} entries, {os.path.getsize(target) / 1e6:.1f} MB")
