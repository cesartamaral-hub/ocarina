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
- c. **(done, translation only)** **Local model** (Qwen3-4B 4-bit via `mlx-lm`, Apache-2.0, 2.3 GB, installed through the model manager like the voices): translates a sentence offline; it is the default once downloaded, online the option. "Explain this word in context" was dropped: the small model gave wrong grammar notes and wrong senses (see benchmarks), so definitions stay with Wiktionary.

**Other**
- Listen and compare Chatterbox and Audio8 on your own books; decide the default.
- Check by hand: the folder dialog ("Import from folder"), a Finder double-click, the Dock icon.
- Later: speech-to-text for pronunciation practice (Handy-style). Housekeeping: remove Lute's `tasks.py`.

## Reader and books: agreed plan (2026-11-04, not started)

Build in this order, one session and one commit each. Steps 1 to 4 are the reader; step 5 is independent and can run in parallel.

1. **Playback shortcuts (done).** `K` play/pause, `J` back, `L` forward, remappable in the shortcuts page, listed in the `?` help and in player tooltips; reader and book page. Audio cannot play in reverse, so `J` means "jump back": to the start of the current sentence (the previous one if within about 1 s of its start) when timings exist, else 10 s. `L` mirrors it. `Space` is left alone (it scrolls).
2. **Reader layout (done).** Remove the 760 px cap for the reader (width scale: narrow for forms, medium for lists, full for the reader). The word panel is pinned to the right window edge, full height, own scroll, resizable (drag handle, also keyboard) and collapsible, width remembered; below about 1000 px it becomes a drawer. The player bar spans the reading column on one row. The text is a centred column with a readable measure (default about 70 characters). Split `Reader.tsx` into layout, toolbar and selection parts.
3. **Text formatting (done).** An "Aa" popover in the reader toolbar, like Firefox Reader View: text size − / +, font (system fonts only), weight, content width, line spacing, character spacing, word spacing, alignment (start, center, end, justify; set the book's language for hyphenation), reset. Live preview, saved as preferences. The same controls component serves the popover and the Appearance page; current text size and font carry over.
4. **Drag-select (done, not yet committed; Option-click selects the whole sentence as text).** Up to about 6 words in one sentence it stays a phrase; longer or across a sentence end it opens a "Selected text" panel with Translate (any length up to the service limit), Play from here and "Save as phrase anyway". The selected span is outlined like a selected word. Optional: Option-click selects the whole sentence.
5. **Books page (done, not yet committed).**
   - Row: title and tags, a minimal speaker icon (no text; badge only when there are several versions; tooltip and aria-label say what it is), stats, a Continue button; Edit/Archive/Delete move into a ⋯ menu.
   - Stats: **known %** of running words (the headline), **new words** (unique, unknown), **words**, a thin status bar (known / learning / new) and a difficulty chip (Easy ≥98%, Comfortable 95-98%, Challenging 90-95%, Hard <90%; a heuristic). Reading time (words / 150) and audio length on hover. "Known" means status 4, 5 or 99; ignored (98) words count as neither.
   - Sort by Recently read, Difficulty, Progress, Title; filter Has audio.
   - Engine: a per-book word index (word -> count), built in the background when a book is added, edited or first seen; stats are one SQL join with the current statuses, so they are exact and always fresh. Measured: parsing runs at 16,000 to 58,000 words/s, so a 100,000-word novel indexes in a few seconds, once. Lute's own `bookstats` is not used (5-page sample, unique words, stale until a page is read).
   - Also: a few small unit tests for pure logic (difficulty thresholds, the stats join, typography to CSS), since the frontend has none.

## Models you add (2026-11-04)
A model added from Hugging Face is looked up (type, support, memory), then tried once after its download; failures are explained in plain words, flagged, and kept out of the voice menus. Higgs TTS 3-4b works (PyTorch-free loading shim). Not yet checked in the packaged app: rebuild, then try Test on a model there.

## Decisions
- **Hard fork** (2026-11-03): no tracking of upstream `lute-v3`; Lute code is deleted once its React replacement exists.
- **Dropped with Lute's pages** (2026-11-03, recoverable from git history before the commit "Retire Lute's pages"): Anki export, term CSV import, audio bookmarks, Lute themes and its own settings screens (replaced by Appearance and Keyboard shortcuts), Lute's Bing image search (replaced by "Find pictures").
- **A new library starts empty** and shows the welcome screen; Lute's list of predefined languages is kept (65), also for "Add a language".
- **Second engine: Audio8** (2026-11-03), not CosyVoice2 (see benchmarks). **Dutch voice shipped**: your sample, with its transcript, is the default for Dutch books.
- **No early playback**: audio plays once the whole book is voiced. **No baked-in slow voice**: the model's pace can't be steered; use the player's speed. Audio8 happens to speak slower on its own.
- **Unsigned app** for now (open with right-click, Open). Revisit later.
- **Preferences on the server** (`ocarina_prefs.json`), not in the web view: its storage is lost with every new port.

## Round 2 after first use (2026-11-04, planned, not started)

Order: A, B, C, D (small fixes, one commit each), then E (design system), F (editor), G (audio sync).

- **A. Selection and clicks (done, not yet committed).** Reproduce drag-select and Cmd-click in the packaged app first (my tests used synthetic events; the real WKWebView may differ). Likely fix: our own pointer selection (pointer down/move/up, hit-testing words) instead of the browser's text selection, with a live outline while dragging; Cmd-click toggles multi-select (check what the web view does with it); Shift-click stays.
- **B. Esc (done, not yet committed).** Esc closes the innermost thing first (popover, menu, selection, drawer), then goes back one level (reader -> book page -> list). Try to stop macOS leaving full screen on Esc (capture phase, `preventDefault`); if the OS still takes it, handle it in the pywebview window. Remappable in Keyboard shortcuts.
- **C. Line length flicker.** The "Aa" popover sits inside the column whose width the slider changes, so the popover moves under the pointer. Anchor it to the window (fixed position, computed on open), and keep the column centred without transition while a slider is dragged.
- **D. Edit text.** A real editor: wide, full-height page that replaces the reading column; text in the reading font and size; sticky bar with Save / Cancel / word count; Cmd+Enter saves, Esc cancels (asks if there are unsaved changes); warns that editing a page invalidates its audio timings and word counts (the word index rebuilds by itself).
- **E. One button system.** Tokens for height (32 px), radius, padding, focus ring, hover and pressed states; variants primary, secondary, quiet (no border), danger; sizes small and normal; icon-only square buttons with tooltips. Toolbar becomes a real bar: left back + title + page; right Highlights as a toggle button, Edit, Aa, Keys, all the same height and alignment. Links that act become buttons; links that navigate stay links. Then sweep every page (books, book page, settings, audio, word panel, status buttons).
- **G. Sync audio you add yourself.** A "Sync with the text" action on a book with its own audio: a background job aligns the audio to the page text and writes the same timings file as generated audio, so highlight, follow, J/L and play-from-here all work. Engine decided (2026-11-04): the forced aligner in mlx-audio (precise; needs a model download). First check it supports Dutch, Polish and French; Whisper stays the fallback only if it does not. Needs chunking for long files, progress and cancel.
- **H. Reading space and a fixed page bar (added).** More room around the text (larger side and top/bottom padding, a little more space between paragraphs). The page controls become a bar pinned to the bottom of the window, always visible, edge to edge of the reading area: Previous at the left edge, "Finish page / Finish and mark the rest as known" at the right edge, and "page X of Y" centred between them (removed from the top toolbar). The bar is clear of the word panel on the right, sits above the audio player if it is at the bottom, and uses the new button system from E. Do after E, together with the toolbar redesign.
