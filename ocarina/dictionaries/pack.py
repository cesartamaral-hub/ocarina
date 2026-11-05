"""
The format of a dictionary pack, and reading one.

    meta(key, value)          id, name, language (the dictionary's own, a code like "nl"), meaning (the language of the meanings, "en"),
                              license, source, kind (builtin | wiktionary | stardict), version, entries
    entry(id, word, word_lc, pos, importance, senses)
                              senses is JSON: [{"text": "...", "examples": ["..."]}]
    form(form_lc, lemma_lc)   an inflected form and the base form it belongs to (when the source knows them)
"""

import json
import os
import sqlite3
import unicodedata

SCHEMA = """
create table meta (key text primary key, value text);
create table entry (id integer primary key, word text not null, word_lc text not null, pos text, importance real default 0, senses text not null);
create index entry_word on entry (word_lc);
create table form (form_lc text not null, lemma_lc text not null);
create index form_form on form (form_lc);
"""


def fold(word):
    "A word as it is looked up: lower case, no zero-width spaces, composed accents."
    return unicodedata.normalize("NFC", (word or "").replace("​", "")).strip().lower()


def create(path, meta):
    "A new empty pack file (an old one at the path is replaced); returns the open connection."
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.executemany("insert into meta values (?, ?)", [(k, str(v)) for k, v in meta.items()])
    return db


def finish(db):
    "Count the entries into the meta table, tidy the file and close it."
    count = db.execute("select count(*) from entry").fetchone()[0]
    db.execute("insert or replace into meta values ('entries', ?)", (str(count),))
    db.commit()
    db.execute("vacuum")
    db.close()


class Pack:
    "A pack on disk, opened to look words up (read only)."

    def __init__(self, path):
        self.path = path
        self.size = os.path.getsize(path)
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        self.db = db
        self.meta = dict(db.execute("select key, value from meta"))
        self.id = self.meta["id"]
        self.name = self.meta.get("name", self.id)
        self.language = self.meta["language"]

    def close(self):
        self.db.close()

    def info(self):
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "meaning": self.meta.get("meaning", "en"),
            "license": self.meta.get("license", ""),
            "source": self.meta.get("source", ""),
            "kind": self.meta.get("kind", ""),
            "entries": int(self.meta.get("entries", 0)),
            "bytes": self.size,
        }

    def entries(self, word):
        "The entries for a word as the panel shows them: [{partOfSpeech, definitions: [{text, examples}]}], best known first."
        rows = self.db.execute("select pos, senses from entry where word_lc = ? order by importance desc, id", (fold(word),)).fetchall()
        found = []
        for pos, senses in rows:
            definitions = [{"text": s["text"], "examples": s.get("examples", [])} for s in json.loads(senses) if s.get("text")]
            if definitions:
                found.append({"partOfSpeech": (pos or "").capitalize(), "definitions": definitions})
        return found

    def lemmas(self, word):
        "The base forms of an inflected form that this pack knows."
        rows = self.db.execute("select distinct lemma_lc from form where form_lc = ?", (fold(word),)).fetchall()
        return [r[0] for r in rows if r[0] != fold(word)]
