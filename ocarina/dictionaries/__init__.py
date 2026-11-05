"""
Offline dictionaries.

A dictionary is a *pack*: one SQLite file in Ocarina's own format (pack.py) for one language. Some come with the app (builtin/, made from
WikDict by scripts/build_wikdict.py), some are downloaded (Wiktionary packs, wiktextract.py) or added by the user (StarDict files,
stardict.py), and those live in <data folder>/dictionaries. The user chooses which are on and in what order (registry.py); looking a word
up (lookup.py) asks the packs of its language in that order.
"""
