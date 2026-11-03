# Ocarina plan

Personal macOS app for studying Dutch, Polish and French (hard fork of Lute v3).
How to work on it: `CLAUDE.md`. How it fits together: `docs/ocarina/architecture.md`.
Background: `docs/ocarina/benchmarks.md` (TTS), `docs/ocarina/packaging.md` (py2app).

## Status (2026-11-03)

| Area | State |
|---|---|
| Screens (all React) | Books (edit, archive, delete, tags, progress), add a book (file, web page, own audio), reader, terms (search, filters, bulk, export), languages, tags, reading stats, backups, appearance (theme, text size, font), keyboard shortcuts, first-run welcome, Settings (model list shows download progress with speed and time left; a header chip follows downloads and voicing anywhere). |
| Reader | Word panel, statuses, hover card, phrases, bulk status, audio following (high-contrast outline), page text edit, term pictures (find or paste), other examples, dictionaries, highlights toggle, notices, key help. |
| TTS | Two engines: Chatterbox (clones a clip) and Audio8 (own voice, clones with a transcript). Voice library with previews, one shipped voice (the Dutch sample, default for every language), a model and voice menu per generation (⋯ next to Generate audio), a voice and a model per language, custom models from Hugging Face, job queue with cancel. |
| Lute | Its pages, templates and static files are gone; its services (parsing, terms, books, backups, stats) stay behind the API. `/` redirects to the app. |
| Packaged `Ocarina.app` | 444 MB, unsigned. Window, first-run screen, API and a bundled-worker preview checked. |
| Tests | 479 pass. Japanese tests need `brew install mecab mecab-ipadic`. |

## Next (agreed 2026-11-03, build in this order)

**1. Selection stands out in the dark theme (done).** The clicked word or dragged phrase gets a thick outline in a neutral high-contrast colour (white in dark, near-black in light, with a soft halo). The playing sentence now has a calmer outline in another hue (gold in dark, burnt orange in light) and a faint tint, and the sentence around the selection gets a subtle band, so you see which sentence "translate" will use.

**2. Audio versions per book (done).** A book keeps several audio versions; generating never replaces yours.
- New table of versions per book (label, own or generated, model, voice, pause, timings file, created); the book points at the selected one, which the player and sentence following use. A migration turns each book's existing audio into its first version.
- Generating adds a version; the same model + voice + pause replaces that generated version only. "Use my own audio…" also adds a version. Deleting a version asks first.
- UI: a selector in the audio panel with rename and delete.
- Later: timings for your own recordings with Whisper, so sentence following works on originals.

**3. Dictionary inside the app.** Lute's embedded dictionaries cannot work: Vandale (`X-Frame-Options: DENY`), DeepL (frame-ancestors itself), Google Translate (same origin) and WordReference (HTTP 418) refuse frames. So show data, not pages.
- a. **(done)** **Word definitions** from the Wiktionary API (English definitions; tested for nl, pl, fr) in the word panel and hover card, cached locally, with a "Full entry" link to the browser. Inflected words (szkoły, huizen, maisons) also show their base form's meaning first; "Use" copies a meaning into the translation. Lute's dictionary list stays, every entry becomes an "Open in browser" link.
- b. **(done)** **Online sentence translation** (MyMemory free; DeepL with your own key), one service and one target language for the whole app (Settings → Translation); cached, with a Try it button.
- c. **Local model** (Qwen3-4B 4-bit via `mlx-lm`, Apache-2.0, 2.3 GB, installed through the model manager like the voices): translates a sentence and explains the word in that sentence, offline. Local is the default, online the option.

**Other**
- Listen and compare Chatterbox and Audio8 on your own books; decide the default.
- Check by hand: the folder dialog ("Import from folder"), a Finder double-click, the Dock icon.
- Later: speech-to-text for pronunciation practice (Handy-style). Housekeeping: remove Lute's `tasks.py`.

## Decisions
- **Hard fork** (2026-11-03): no tracking of upstream `lute-v3`; Lute code is deleted once its React replacement exists.
- **Dropped with Lute's pages** (2026-11-03, recoverable from git history before the commit "Retire Lute's pages"): Anki export, term CSV import, audio bookmarks, Lute themes and its own settings screens (replaced by Appearance and Keyboard shortcuts), Lute's Bing image search (replaced by "Find pictures").
- **A new library starts empty** and shows the welcome screen; Lute's list of predefined languages is kept (65), also for "Add a language".
- **Second engine: Audio8** (2026-11-03), not CosyVoice2 (see benchmarks). **Dutch voice shipped**: your sample, with its transcript, is the default for Dutch books.
- **No early playback**: audio plays once the whole book is voiced. **No baked-in slow voice**: the model's pace can't be steered; use the player's speed. Audio8 happens to speak slower on its own.
- **Unsigned app** for now (open with right-click, Open). Revisit later.
- **Preferences on the server** (`ocarina_prefs.json`), not in the web view: its storage is lost with every new port.
