# Ocarina plan

Personal macOS app for studying Dutch, Polish and French (hard fork of Lute v3).
How to work on it: `CLAUDE.md`. How it fits together: `docs/ocarina/architecture.md`.
Background: `docs/ocarina/benchmarks.md` (TTS), `docs/ocarina/packaging.md` (py2app).

## Status (2026-11-03)

| Area | State |
|---|---|
| Screens (all React) | Books (edit, archive, delete, tags, progress), add a book (file, web page, own audio), reader, terms (search, filters, bulk, export), languages, tags, reading stats, backups, appearance (theme, text size, font), keyboard shortcuts, first-run welcome, Settings. |
| Reader | Word panel, statuses, hover card, phrases, bulk status, audio following (high-contrast outline), page text edit, term pictures (find or paste), other examples, dictionaries, highlights toggle, notices, key help. |
| TTS | Two engines: Chatterbox (clones a clip) and Audio8 (own voice, clones with a transcript). Voice library with previews, a shipped Dutch voice, a voice and a model per language, custom models from Hugging Face, job queue with cancel. |
| Lute | Its pages, templates and static files are gone; its services (parsing, terms, books, backups, stats) stay behind the API. `/` redirects to the app. |
| Packaged `Ocarina.app` | 444 MB, unsigned. Window, first-run screen, API and a bundled-worker preview checked. |
| Tests | 479 pass. Japanese tests need `brew install mecab mecab-ipadic`. |

## Next
1. Listen and compare Chatterbox and Audio8 on your own books (quality is unjudged); decide which to make the default.
2. Check by hand what could not be driven from here: the folder dialog ("Import from folder"), a Finder double-click, the Dock icon.
3. Later: speech-to-text for pronunciation practice (Handy-style).
4. Housekeeping: `tasks.py` is Lute's old task runner (it still mentions the deleted acceptance tests); remove or trim it.

## Decisions
- **Hard fork** (2026-11-03): no tracking of upstream `lute-v3`; Lute code is deleted once its React replacement exists.
- **Dropped with Lute's pages** (2026-11-03, recoverable from git history before the commit "Retire Lute's pages"): Anki export, term CSV import, audio bookmarks, Lute themes and its own settings screens (replaced by Appearance and Keyboard shortcuts), Lute's Bing image search (replaced by "Find pictures").
- **A new library starts empty** and shows the welcome screen; Lute's list of predefined languages is kept (65), also for "Add a language".
- **Second engine: Audio8** (2026-11-03), not CosyVoice2 (see benchmarks). **Dutch voice shipped**: your sample, with its transcript, is the default for Dutch books.
- **No early playback**: audio plays once the whole book is voiced. **No baked-in slow voice**: the model's pace can't be steered; use the player's speed. Audio8 happens to speak slower on its own.
- **Unsigned app** for now (open with right-click, Open). Revisit later.
- **Preferences on the server** (`ocarina_prefs.json`), not in the web view: its storage is lost with every new port.
