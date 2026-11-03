# Ocarina plan

Personal macOS app for studying Dutch, Polish and French (hard fork of Lute v3).
How to work on it: `CLAUDE.md`. How it fits together: `docs/ocarina/architecture.md`.
Background: `docs/ocarina/benchmarks.md` (TTS), `docs/ocarina/packaging.md` (py2app).

## Status (2026-11-03)

| Area | State |
|---|---|
| Environment, test baseline | Done. Whole suite passes (554). Japanese tests need `brew install mecab mecab-ipadic`. |
| TTS service (`ocarina/tts`) | Done: MLX Chatterbox, worker process, sentence cache, CLI, model downloads. |
| Book audio API | Done: whole-book jobs, sentence timings, never overwrites your recordings without `replace`. |
| React app: books, book view, Settings (models), reader | Working. Reader: word panel, statuses, hover card, phrases, bulk status, audio following, page text edit, pictures, other examples, dictionaries (frame shown blank in preview, unverified). |
| Model management | Download, import from folder, delete; voice per language (Settings). |
| Packaged `Ocarina.app` | Builds and ran an audio job. Window itself and double-click not checked; unsigned. |

## Next (rough order)
1. Model choice: per-language voice pref and import from folder are done; custom catalog entries (`models.json` in the data folder, then a Hugging Face form) wait for a second engine.
2. Port remaining Lute screens to React: backups, stats. (Done: language settings; book import; term list with search, filters, bulk edit, inline edit, CSV export. Term tags have no screen of their own: they are edited on terms.) (Book import done: file or web page, edit, save.)
3. Audio: voice preview and reference-voice picker, a second engine (CosyVoice2 or Parkiet).
4. Reader polish: remember current page on leaving, Bing image search, flash messages, keyboard help.
5. Packaging: check the window, trim the 470 MB bundle, first-run flow, then retire Lute's Flask templates.
6. Later: speech-to-text for pronunciation practice (Handy-style).

## Decisions
- **No early playback** (2026-11-03): audio plays once the whole book is voiced.
- **No baked-in slow voice** (2026-11-03): the model's pace can't be steered (see benchmarks); playback speed in the player is the learner control.
- **Hard fork** (2026-11-03): no tracking of upstream `lute-v3`; change or delete Lute modules once their React replacement exists.
- **Unsigned app** for now (open with right-click, Open). Revisit later.
- **App icon** (2026-11-03): ocarina glyph, paper white on green; sources in `assets/`.
- **Preferences on the server** (`ocarina_prefs.json`), not in the web view: its storage is lost with every new port.

## Open questions
- Which reference voice(s) to ship? (Pace can't be changed through the reference voice; only timbre.)
- Keep Lute's language definitions (`lute/db/language_defs`) or trim the language list?
