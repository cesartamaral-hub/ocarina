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
