# Architecture

```
Ocarina.app (py2app, desktop/)
 ├─ pywebview window ──► React app (frontend/, built into ocarina/web/dist)
 ├─ Flask + waitress on 127.0.0.1:<random port>
 │    ├─ lute/      Lute v3: models, parsers, term and read services, DB migrations (kept)
 │    └─ ocarina/api/   our JSON API, one blueprint per area
 └─ TTS worker process (ocarina/tts/worker.py), started on demand, killed after each job
Data: ~/Library/Application Support/Ocarina   ocarina.db, useraudio/, userimages/, tts_cache/, ocarina_prefs.json
Models: ~/.cache/huggingface/hub (the MLX library looks there)
```

## API (all under `/ocarina/api`)
| Module | Endpoints |
|---|---|
| `books.py` | `PATCH/DELETE /books/<id>` (title, source, tags, archive; delete removes generated audio), `GET /books`, `GET /books/<id>/sentences` (with start times if audio is ours) |
| `pages.py` | `GET /books/<id>/pages/<n>` (opens the page), `POST .../finish`, `GET/PUT .../text` |
| `terms.py` | `GET /terms/<id>`, `POST /terms`, `GET /terms/lookup`, `PATCH /terms/<id>/status`, `POST /terms/bulk-status`, `GET /terms/<id>/popup`, `GET /terms/<id>/references`, `POST/DELETE /terms/<id>/image` |
| `audio_versions.py` | `GET /books/<id>/audio/versions`, `PUT .../<version>/select`, `PATCH .../<version>` (rename), `DELETE .../<version>`. A book keeps several audio versions (table `bookaudios`, migration `20261103_create_bookaudios.sql`; logic in `ocarina/audio_versions.py`); `books.BkAudioFilename` stays the selected one, so the player and sentence following are unchanged. Generating and uploading add versions; the same model + voice + pause replaces that generated version only; deleting removes generated files but leaves your own recording on disk. |
| `translate.py` | `GET/PUT /translate/settings` (service: the model on this Mac, MyMemory or DeepL; target language; optional MyMemory email; DeepL key; the local model is the default once downloaded), `POST /translate` (a sentence), `POST /translate/test`. MyMemory (free) or DeepL (your key); results cached in `<data>/translation_cache`; the key lives in `<data>/ocarina_secrets.json` (mode 600, never sent to the page; see `ocarina/keystore.py`). Logic in `ocarina/translate.py`. The local model (`qwen3-4b-instruct-mlx`, catalog kind `text`, engine `mlx-lm`) runs in the same kind of worker process as the voices (`ocarina/localllm.py`: loaded on first use, unloaded after 5 idle minutes). |
| `dictionary.py` | `GET /dictionary/define?languageId=&text=[&cacheOnly=true]`: definitions from Wiktionary (English, per language section), plus the base form's meaning for inflected words; cached in `<data>/dictionary_cache` (90 days, 2 days for missing words), old copies are used offline. Logic in `ocarina/dictionary.py`. Lute's dictionary list is only shown as "Open in browser" links. |
| `audio.py` | `POST /books/<id>/audio` (job), `GET /books/<id>/audio/sentences` |
| `jobs.py` | `GET /jobs`, `GET /jobs/<id>`, `POST /jobs/<id>/cancel`; a FIFO queue run one job at a time by one thread (audio and downloads share it); jobs call `check()` to notice cancelling; they carry a `title` (book or model name) so the header can say what runs |
| `tts_models.py` | `GET /tts/models`, `GET /tts/engines`, `POST /tts/models/lookup`, `POST /tts/models/custom`, `DELETE /tts/models/<id>/entry`, `POST /tts/models/<id>/download`, `POST /tts/models/<id>/import` (copy from a folder, matched by file name and size), `DELETE /tts/models/<id>` |
| `audio.py` also: `GET /books/<id>/audio/options` (the language's default model and voice, and what can be chosen for one generation; the generate call takes `model` and `voice`),  `POST /books/<id>/audio/upload` (own audio file; removes a replaced generated file, keeps recordings) |
| `term_list.py` | `GET /term-list` (filters, sort, paging), `GET /term-list/export` (CSV), `GET /tags`, `POST /terms/bulk` (status, tags, parent, delete) |
| `backups.py` | `GET /backups`, `PUT /backups/settings`, `POST /backups` (now; `manual` keeps it), `POST /backups/skip`, `GET /backups/<name>/download`; the app makes a due backup when it opens |
| `stats.py` | `GET /stats` (streak, words read per language and period, daily history) |
| `voices.py` | `GET/POST /tts/voices`, `DELETE /tts/voices/<id>`, `POST /tts/voices/preview` (a job), `GET /tts/previews/<name>`; clips in `<data>/voices/` as mono wav with an optional `.txt` of the words spoken |
| `languages.py` also `POST /languages/predefined` (first run) |
| `tags.py` | `GET /tag-list/<term|book>`, `PATCH/DELETE /tag-list/<kind>/<id>` |
| `tts_models.py` also: `POST /tts/models/lookup` now describes the repo (model type, whether mlx-audio has code for it via a helper process `ocarina/tts/inspect_model.py`, memory estimate, notes) and `POST /tts/models/<id>/check` tries an installed model once (job kind `check`; `ocarina/model_check.py` stores `model_checks.json`; a model you add is tried automatically after its download, phase `testing`). A failing model is flagged, left out of the voice menus and never chosen by itself. Job errors are explained in plain words by `ocarina/tts/errors.py` (original text kept as `detail`). |
| `languages.py` | `GET /languages` (with counts), `GET/PUT/DELETE /languages/<id>`, `POST /languages`, `GET /languages/template` (blank or predefined), `GET /languages/parsers`; delete needs `force=true` when it holds books or terms |
| `book_import.py` | `POST /books/extract` (file or URL, nothing saved), `POST /books` (save, optional own audio) |
| `system.py` | `POST /open-external` (http/https only), `GET/PUT /prefs` |
| `web.py` | serves the built frontend at `/ocarina/app/` (any sub-path gets `index.html`) |

## Book audio
Sentences come from Lute's language parser (`tts/book_audio.py`), each is voiced (`tts/service.py`,
cached per model+language+voice+text in `tts/cache.py`), stitched with pauses (`tts/stitch.py`) into
one mp3 in Lute's single audio slot. Start times go in a sidecar `<audio>.sentences.json`, so
Lute's own bookmarks stay the user's. A book with the user's own recording is only replaced with
`replace=true`. The reader matches audio to text by order: sentences with a word, per page, in the
same order. If the counts differ the text was edited since, and following switches off.

## TTS process model
`Supervisor` owns one worker (`python -m ocarina.tts.worker`, JSON lines over stdin/stdout). A dead
worker is restarted once per request; `unload()` kills it so memory returns to the OS. The worker
sees `HF_HUB_OFFLINE=1`; the model for a book is `choose_model`: request, then pref `model.<nl|pl|fr>`, then first installed; model files are installed by `tts/models.py` (pinned revision, file sizes
checked, `refs/main` pointed at the pinned revision).

## Frontend
Hash routes (`#/`, `#/book/<id>`, `#/book/<id>/read/<page>`, `#/settings`) in `App.tsx`. API calls
in `src/api/<area>.ts` mirror the backend modules. Reader: `Reader.tsx` (page, selection, keys),
`ReaderLayout.tsx` (the frame: reading column plus the word panel pinned to the window's right edge, resizable
(`sidePanel.ts` holds the width rules), collapsible with `P`, a drawer under 1000 px), `ReaderToolbar.tsx`,
`AudioPanel.tsx` (the sticky player bar), `TermPanel.tsx` (word panel), `useAudioFollow.ts`,
`useHoverCard.tsx`. Page layout: the header is sticky; `main` has a width scale (`w-full` for the reader,
`w-medium` for the book and term lists, 760 px otherwise), chosen in `App.tsx`. Preferences load once at
start (`loadPrefs`) and are read with `getPref`; the panel keeps `reader.sideWidth` and `reader.sideCollapsed`.
Unit tests of pure logic (`*.test.ts`) run with `npm test`.

## Decisions
- Hard fork; Lute code may be changed or removed once its React replacement exists.
- Language to TTS language code is by name (Dutch, Polish/Polski, French) in `tts/book_audio.py`.
- No accounts, no cloud, one user. Unsigned app for now.

## Known debt
- Language name to TTS code mapping is fragile (renaming a language breaks it); move it to a per-language setting.
- Jobs are in memory (lost on restart); a queued job does not survive closing the app. Cancelling is noticed between sentences (or between file chunks in a download).
- "Installed" model check compares file sizes only, not hashes.
- Lute's old screens still serve everything not yet ported (term lists, import, backups, stats).
- Bundle is ~470 MB (mlx, scipy, transformers); trim later.

## Reader text settings

`frontend/src/typography.ts` holds the rules (defaults, limits, normalising saved data, the CSS variables) and is unit tested. The settings are saved as one server preference, `reader.typography`; until it exists the older `readerSize` and `readerFont` are used. `applyAppearance()` writes the `--r-*` variables on the document, and the reader article, the Appearance sample and the line length (`--r-measure`, kept in characters) read them. `TypographyControls.tsx` is shared by the "Aa" popover in the reader toolbar and the Appearance page. The article gets `lang` from the book's language so justified text can hyphenate.

## Selecting text in the reader

`reader/selection.ts` (`classify`, unit tested) decides what a drag or Shift-click range means: 2 to 6 words in one sentence is a phrase (word panel, as before); more words or a sentence end inside it is text. Text opens "Selected text" in the side panel (translate, play from the first sentence, "Save as phrase anyway") and outlines the span; Option-click on a word selects its whole sentence as text.

## Book statistics

`ocarina/book_index.py` keeps a word index per book (tables `bookwords`, `bookindex`; migration `20261104_create_bookwords.sql`). `GET /books` starts a background thread for books whose index is missing or built from other text (a SHA-1 of all pages), and returns `stats: null, indexing: true` for them; the book list polls every 1.5 s until the numbers arrive. Statistics are one SQL join with `words`, so they follow status changes at once. "Known" is status 4, 5, 99; learning 1–3; 98 (ignored) is left out of the percentage; only single-word terms count. Reading time is words / 150 per minute. The list's sorting, difficulty chips (98 / 95 / 90 %) and bar are pure functions in `frontend/src/bookStats.ts` with tests.

## The Esc key

`frontend/src/escape.ts`: one capture-phase handler on the window (installed in `App.tsx`) always cancels Esc's default (so the window does not leave full screen). It closes the innermost open thing, and when nothing is open it blurs a focused text field, else goes to the route's parent (reader -> book -> list; settings pages -> settings). Anything that can be dismissed registers with `useEscape(active, close)` while it is open (the Aa popover, the book ⋯ menu, the audio options menu, the key-recording mode, the reader's selection, and the text editor, which asks before discarding changes). New popovers and dialogs should do the same.

## Buttons

One system in `index.css` ("Buttons" section at the end): tokens `--control-h` (34 px), `--control-h-sm` (28 px), `--radius`. A plain `button` or `a.button` is the primary action; `.secondary` is outlined; `.quiet` has no border until hovered (toolbars; `aria-pressed` shows a toggle as on); `.danger` is for destructive actions; `.small` is for rows; `.icon` is a square. `.link-button` is a text link that acts. Use links only to navigate. The reader's toolbar (`ReaderToolbar.tsx`) and the page bar pinned to the bottom of the reading area (previous at the left edge, page count in the middle, finish at the right edge) are built from these.

## Syncing your own recordings

`ocarina/audio_sync.py`: a forced aligner (catalog model `qwen3-forced-aligner-mlx`, kind `aligner`, engine `mlx-aligner` in the TTS worker, ops `duration` and `align`) places every word of the book's text in the recording; the sentences' start times are written to the same `<audio>.sentences.json` that generated audio has, with `"aligned": true`, so highlighting, J/L and play-from-here work unchanged. The version stays `own`: `is_ocarina_audio` (generated) is false for synced audio, removing the version keeps the recording and drops the timings. Long recordings are aligned in 240 s windows: each gets more text than it will hold and only sentences ending in the first 75% are kept; the next window starts at the first one not kept (tested against one-window results on Dutch and Polish: within 0.1 s). The aligner starts a word where the one before it ended, and after a long pause it can pile words onto silence or onto the end of the previous sentence, so each start is then moved to the first real sound (`refine_starts`; the worker's `onsets` op and `first_speech`, using loudness against the recording's own noise floor and skipping a short tail of the sentence before). Measured on generated recordings with known sentence starts: Dutch 256 s, 60 sentences, all within 0.24 s (mean 0.07 s), synced in 7 s once the model is loaded; French 21 sentences, all within 0.12 s. A recording that does not match the text (more than a fifth of the sentences too quick or too slow) is refused and nothing is written. The aligner does not list Dutch or Polish but works on them (the language argument is ignored). `.m4a`, `.ogg` and similar need `ffmpeg` to be decoded; mp3, wav and flac do not.
Job: `POST /books/<id>/audio/versions/<version>/sync` (kind `sync`, progress in sentences). UI: "Sync with the text" / "Sync again" on the book page; the model is listed and tested under "Audio sync model" in Settings.

## The reader frame

The reader is exactly as tall as the window below the header (`.reader`, `100dvh`); the window itself never scrolls there. Inside the main column: the audio player (if any), `.reader-scroll` (toolbar and text, the only part that scrolls), and `.reader-foot` (the bar for words picked with ⌘-click, when there are any, above the page bar). So the page bar is at the window's bottom whatever the text length. Picked words are `.w.multi` (dashed outline); `applyMulti` sets their status by text, creating terms as needed.

## Storage

`ocarina/storage.py` and `GET /storage`, `POST /storage/clear`, page `#/storage`. Models live in the Hugging Face cache (`~/.cache/huggingface/hub`), which newer `huggingface_hub` versions fill from one store shared by the whole cache (`hub/blobs/<xx>/<hash>`): a repository's `blobs` entries are links into it. Sizes follow the links (a file two repositories share counts once per model); `models.delete` now also removes the shared files that no other repository links to (it used to leave them, so deleting a model freed nothing). Files in the shared store that nothing links to ("leftovers" of deletions by older versions) can be freed from the Storage page. What belongs to other programs is only reported. The Settings page shows the total and the size per kind of model. Cache clearing is refused while any job runs.

## The Appearance page

`Appearance.tsx`: Theme as three cards with real mini pages drawn in each palette (`.pal-light`, `.pal-dark`; "Match my Mac" shows both halves), then Reading text: presets (`PRESETS` and `matchingPreset` in `typography.ts`, tested; a preset is a full set of settings and is highlighted only while nothing differs from it), font cards that show each font, size with A−/A+, line length and spacing, alignment, and folded-away fine tuning. A sticky live preview (`.appearance-sample`, reading the same `--r-*` variables as the reader, with word-status colours) sits beside the controls on wide windows and above them on narrow ones. `RadioCards.tsx` is a row of cards made of real radio buttons (keyboard and screen readers for free); `AlignPicker.tsx` and `useTypography.ts` are shared with the reader's "Aa" popover.

## Books and the audio page

Clicking a book opens the reader on the page you were on (`#/book/<id>` redirects there: `BookRedirect.tsx` asks `GET /books/<id>` for the current page and replaces the history entry). The old book page is the **Audio page** at `#/book/<id>/audio` (`AudioPage.tsx`): a job strip under the title (making audio or syncing, progress, Cancel, and the plain-language errors, always in the same place), then three cards, Listen (version picker with Sync / Rename / Delete, player, speed), Make new audio (model and voice as a line with Change, pause, Generate), Your own recording (Add), then the sentence list. It is opened from "Audio…" in the ⋯ menu of a book row and of the reader toolbar (`MoreMenu.tsx`, shared; items are actions or links). Esc goes reader -> Books and audio -> reader (`parentRoute`); the header chip for audio jobs links to the audio page.

## Styles that must not go missing, popovers, hover meanings

`cssCoverage.test.ts` fails when a class used in a component has no rule in `index.css` (a few hook-only names are listed in it). It exists because the audio highlight (`.sentence.playing`), the hover card and the word panel's chips were once deleted from the stylesheet while the code kept working invisibly. Popovers and menus opened from a button (the Aa popover, the ⋯ menus) are drawn by `Popover.tsx` in a portal on the page, placed by `placement.ts` from the button's position (fixed, inside the window, above the panels), so a scrolling area cannot clip them. The hover card (`useHoverCard.tsx`) shows for every word: your translation, else the first Wiktionary meaning (cached per word), else a hint; it goes away on scroll, click or Esc; Appearance has its on/off and delay (`reader.hoverMeaning`, `reader.hoverDelay`).

## The vocabulary panel

`reader/vocabulary.ts` (`pageVocabulary`, tested) turns the page's items into known / learning (1, 2, 3) / new (status 0) / ignored counts, the known share (ignored words left out), difficulty, reading time and the list of new words by frequency; since it works on the page already in memory, it follows every status change at once. `VocabularyPanel.tsx` shows it with the book's numbers from `GET /books/<id>` (asked again a moment after each change, and again while the word index is still being built). It is the left column of the reader frame (`ReaderLayout` `left` / `leftOpen`, key V, button "Vocabulary" in the toolbar, remembered as `reader.vocabOpen`); under 1100 px it is a drawer over the text that is closed by default and closes with Esc. In the footer, a narrow bar (`.page-bar` is a container) uses shorter labels so it stays on one row.

## The Reading page

`GET /stats` keeps its old fields (`streak`, `table`, `chart`) and adds `languages` and `totals`, built by `ocarina/language_stats.py` for every language that has books or reading: terms by status (vocabulary = started on = known + learning; "seen but not started" is status 0), what the texts hold (word index sums over books that are not archived: known share, new words, reading time left from the pages not yet reached), books with progress and known share, words read per period, streak, first and last read, and known words over time (by the day each word last changed status, so a word that is raised from 4 to 5 moves to that day). The endpoint starts building any missing word indexes; the page asks again until none are pending. `Stats.tsx`: a language filter (All languages or one, remembered as `stats.language`), summary cards, a card per language; with one language chosen it adds the words-read and known-words charts and the book list. `readingStats.ts` has the date wording, the filter and the chart points (tested).
