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

## The translated version of a book

Table `booktranslations` (migration `20261105_...`): one row per sentence, found by page and by the sentence's place among the sentences of that page that contain a word (the numbering the audio timings use), with the text, a hash of the sentence it was translated from, and the service (or "manual"). `ocarina/book_translation.py` makes it with `translate.translate` (so the Translation settings decide the service, the model and the target language, and each service's own cache and limits apply); each sentence is saved as soon as it is done, quota, connection and key problems stop the job and keep what was finished. A sentence whose hash no longer matches (the text was edited) shows as out of date and is the only thing translated again; a sentence corrected by hand is never replaced. API in `api/book_translation.py` (`GET`/`POST`/`DELETE /books/<id>/translation`, `PUT .../<page>/<index>`); the job kind is `translate`.
In the reader (`reader/translationView.ts`, `useBookTranslation.ts`, `TranslationPanel.tsx`): modes original, side by side (a grid per paragraph, stacked when the column is under 760 px) and translation only, chosen in the toolbar's Translation popover or with T (remembered as `reader.translationMode`; a page with no translation shows the original). Translated sentences carry the same sentence number (`data-sent`) as the original, so the audio highlight, the selection band and the hover pairing mark both sides; clicking a translated sentence selects the original sentence. The popover also makes the translation (this page first, or the whole book, with progress, Cancel and a warning when a service's daily limit would run out), shows what is left and removes it.

## Shortcuts, speed, title and Now Playing

Every key the app acts on is marked as handled (`preventDefault`): an unhandled key makes the web view hand it to macOS, which beeps. This holds for the reader's handler, for J/K/L even when the page has no player, and for the status keys. New shortcuts must do the same. Playback speed is 0.5 to 2.0 (`speeds.ts`, `SpeedMenu.tsx` for the presets 0.50, 0.75, 0.85, 1.00, 1.50, 2.00), remembered per language. `desktop.ts` sets the window title through the bridge (`Bridge.set_title`, pywebview) to the book being read, and `nowPlaying.ts` fills `navigator.mediaSession` (title, language as artist, icon, play, pause, previous and next sentence, 10 s, seeking and the position) so the system's Now Playing and the media keys know what plays; whether the desktop web view passes it on to Now Playing has to be checked in the packaged app.

T with no translation on the page opens the Translation popover (the popover's anchor lives in `Reader`, so keys and the toolbar open the same one). "Translate this page" and "Translate the whole book" are `TranslateSplit` buttons: the main part uses the default service and model, the arrow lists the other ways (`methods` in `GET /books/<id>/translation`, `provider` and `model` on `POST` for one run only, refused with the reason when a model is not downloaded or DeepL has no key). `TranslationModes.tsx` is the row of three icons centred above the text; with no translation the two translation icons open the popover.

## Focus mode

Key F (or the "Focus" button in the toolbar; Esc leaves it, after any popover or selection that is open). `Reader` keeps `focus` in state (not saved) and puts `focus-mode` on the document element; `ReaderLayout` gets `focus`. In CSS: the app header is hidden (`--header-h` is 0), the vocabulary panel is gone, the word panel is a drawer that opens for a word you click (as on a narrow window), the toolbar sits hidden in the bottom-right corner (not clickable while hidden; a small handle, `focus-reveal`, brings it out, and it hides again when the pointer leaves; `focus-peek` on the document element), the player stays without the version picker and hints, and the page bar becomes a quiet pill at the bottom. The translation mode icons, highlighting, the sentence highlight, hover meanings and the keys all keep working.

## The sentence card

`reader/SentenceCard.tsx` is the one card for a sentence or a picked text, in the word panel and for a selection: a small heading ("Sentence", or "Selected text · 12 words"), icon buttons (play from here, copy, translate in your browser), the text as a quote, and below a dashed rule its translation: a full-width Translate button with a line saying where the text goes ("Stays on this Mac" or "Sent to MyMemory") until there is a result; a loading placeholder; the result with the target language and service in small print and an ⓘ note that it is a machine translation. A translation the book already has for exactly that sentence (`isWholeSentence` in `cardWording.ts`) shows at once, with no button. A long selection also gets "Learn it as a phrase", with a line on what that does.

## Settings sections

Settings is one page with a left navigation (`SettingsShell.tsx`, routes in `settingsRoutes.ts`): `#/settings/<section>` with sections Appearance, Keyboard shortcuts, Languages (list, `/new`, `/<id>` editor), Tags, Models, Voices, Translation, Backups and Storage, grouped as Reading, Languages, Audio and translation, Library. On windows under 820px the nav becomes a row of tabs. `#/settings` opens the last section used (pref `settings.section`, else Appearance); the old routes (`#/appearance`, `#/tags`, …) redirect through `legacyRedirect`. `Settings.tsx` renders the `models` or `voices` part. Esc goes to the library, or from a language editor to the languages list (`parentRoute`).

## Adding study material from a link

`POST /api/books/extract` takes a file, or `{url, languageId, keepAudio}`. `ocarina/importer.py` fetches a web page (15 s timeout), reads it with trafilatura (the paragraphs of the page's headings and `<p>` as the fallback, with a note) and returns `{title, text, sourceUri, note}`; it is also a command (`python -m ocarina.importer --url … --language nl --save` writes `./imports/<title>.txt`). A YouTube link goes to `ocarina/youtube.py`: captions first (`youtube-transcript-api`: written in the language, then automatic, then YouTube's translation; no language code means any), cut into paragraphs of about 450 characters. Automatic captions have no punctuation, so when the transcription model is installed they are replaced by Whisper's text (a job); the captions remain the fallback if Whisper fails. The endpoint answers at once for a page or a video with captions. For a video without captions (or with `keepAudio`) it starts a job of kind `import` (the queue is shared with audio and translation jobs); the page polls it and reads `result`. The job downloads the sound with yt-dlp (needs ffmpeg), transcribes it with `ocarina/transcribe.py` (engine `mlx-whisper` in the model worker, op `transcribe`, catalog model `whisper-large-v3-turbo-mlx`, kind `transcriber`, shown under Models) and deletes the sound. With `keepAudio` the sound is converted to m4a, kept in `<data>/temp/<token>.m4a` and attached when the book is saved (`importAudio` in `POST /api/books`; the file is removed afterwards). Without the model the endpoint answers 409 `model_not_installed`.

## Playing the video of a book

A book made from a YouTube link can keep the link instead of the sound (`bookvideos`, `ocarina/video.py`): the video id and *anchors*, `[[words before, seconds], ...]` closed by `[all the words, end]`, from the captions' start times or from the segments Whisper heard (`youtube.build_text`). `GET /api/books/<id>/sentences` adds `video: {videoId}` and, when the book has no timed audio of its own, each sentence's `start`, worked out from the anchors in proportion to the words (so small edits to the text keep following). In the reader, `AudioPanel` shows `VideoBar` instead of the audio bar: the YouTube player (`youtube.ts` loads its script once) wrapped in `YouTubeMedia`, which has the same members as an audio element (`Playable` in `media.ts`), so `useAudioFollow`, the J/K/L keys, the speed menu (YouTube rounds to its 0.25 to 2 steps) and Now Playing work unchanged. A video whose owner blocks embedding (errors 101, 150) or that cannot be reached shows the reason and a link to YouTube. Add study material has a checkbox "Play the video in the reader".

## Hearing a word

`POST /api/pronounce {text, languageId, source?}` returns `{url, source, note}` (`ocarina/pronounce.py`, `api/pronounce.py`); the audio is in `<data>/pronounce_cache` (a wav or mp3 named by a hash of source, language, voice and text, so a word heard once plays at once and offline). Sources: `voice` (the model and voice chosen for the language, through a worker that stays loaded for 5 minutes, `_WarmVoice`; its silence is trimmed), `speaker` (the recording of a person that the word's English Wiktionary entry names through `{{audio|nl|…}}`, fetched from Wikimedia Commons and converted to wav by ffmpeg, because the web view cannot play Ogg; single words only), `google` (the unofficial `translate.google.com/translate_tts`, up to about 190 characters), and `system` (macOS `say` with a voice for the language). A source that cannot be used (no model, an audio or preview job holds the speech model, no recording, no internet) gives way to `system`, and the note says why; the page shows it as a notice. In the reader (`pronouncer.ts`) one thing is said at a time (the same button again stops), and the book's audio or video is paused while a word is said and resumed after. The speaker button is in the word panel's heading and in the sentence card (`SpeakButton`); its arrow says it another way for one time; the S key says the selection; Settings → Voices has the default source (`pronounce.source`).

A double click on a word (the second press, in `Reader.onMouseDown`) plays that word's sentence, from `LEAD_IN` (0.4 s) before its start so the first word is not cut (`useAudioFollow.playSentence`). The scrim that dims the text behind the drawer (focus mode, narrow windows) takes no clicks, so the second press reaches the word; a press on the text away from the words closes the drawer (`ReaderLayout`).

## The Models page

Each kind of model (voice, translation, audio sync, transcription) is a `ModelList` of compact rows (`ModelList.tsx`): a circle (a tick when the model is in use, a download arrow when it is not downloaded), name with a badge, a one-line description, a grade for each language of the library (NL, PL, FR, in that order), four speed bars, the size and a ⋯ menu (test, import from a folder, remove from the list, delete). The grades, the speed rating (1 to 4) and the badge are fields of the catalog (`grades`, `speed`, `badge`); they are written by hand, and a model added by the user has none ("—"). The speed bars follow the measured time once a model has been tested on this Mac (`modelRows.speedLevel`). What "in use" means differs by kind: a voice model is ticked when it is the one used for all the languages shown, and clicking another sets `model.<code>` for each language it speaks, in one request (`setPrefs`; separate requests overwrote each other); a language with its own choice from Voices shows "used for NL" on its row. A translation model is ticked when Translation is set to this Mac with that model, and clicking it sets both. The audio sync and transcription models have one model each: it is ticked when it is installed.

## The Vocabulary page

`#/vocabulary` (the old `#/terms` redirects to it; `Vocabulary.tsx`, helpers in `vocabularyRows.ts`) lists the words that have a status of 1 to 5 or "well known" (99), and 98 (ignored) when its chip is on; status 0 never. It is laid out like the reader (`ReaderLayout`: the list on the left, the same word panel, `TermPanel`, on the right; a drawer on a narrow window). `TermPanel` now takes the language and the book and page (`where`) instead of a reader page, so both pages use it. Filters are chips: language (only with more than one; the Language column is hidden when one is chosen), status chips with counts (`GET /api/term-list?statuses=1,2,3&counts=true`), a tag select, a search box, and a sort menu; rows are loaded 100 at a time as the end of the list comes near (`pageSize` up to 500; after a change the loaded rows are asked for again in one request). Keys: ↑ ↓ Home End move (the panel follows after 140 ms), S or Return says the word with the default source (`pronouncer.say`), Space ticks it, `/` searches, the status keys set the status of the word in the panel. Ticked words get a bulk bar (status, tag, parent, delete).

The "In context" column is the sentence the word was saved from. The reader sends it with the save (`POST /api/terms` takes `context: {sentence, bookId, page}`), and `term_context.remember` keeps the first one recorded in `termcontexts`. Words saved before that have none: at start a background pass (`term_context.backfill`, `prepare_library`) gives each the first sentence of the language's books that has it (`TcFound = 1`, the earliest read page first); a word no book has is marked as looked for, and stays empty. The word is marked in the sentence in the page, not stored (`contextParts`). The link beside a sentence opens the book at that page.

## The CEFR level bar

`CefrBar.tsx` shows where a language's known words (status 4, 5 and well known, the same count as the Reading page) stand on the CEFR scale (`cefr.ts`): A1 500, A2 1,200, B1 2,500, B2 4,000, C1 8,000, C2 16,000 words, the usual frequency-based guides. Six equal stretches, one per level, each running from the previous level's words to its own, so the early levels are not squeezed; the level is the last stretch completed ("A0" below 500). On the book list it sits under each language's heading (`GET /api/stats/vocabulary`: known and learning per language, a light call); on the Reading page, in a language's detail view, it is bigger and has a table of the levels with what each looks like, its words, and how many are to go, plus a note that the figures are estimates (they differ by study and by active or passive vocabulary, and every form of a word counts separately here).

## Audio synced when added, translation when saved

Every own recording added to a material is synced with its text at once: `audio_versions.queue_sync` (API module) queues the job, and `sync_new_audio` is called from `POST /books` (a recording saved with the material) and `POST /books/<id>/audio/upload`; the answer carries `sync: {state: started | model_missing | busy}` (the page shows the job, or says to download the audio sync model; the audio is kept either way). `POST /books` also takes `translate=1`, `translateProvider`, `translateModel`: the whole text is translated by a queued job (`book_translation.queue_translation`, shared with the Translation menu) and a failure only comes back as `translation: {state: failed, error}`, the material is saved. In Add study material the translate box is ticked for a text of up to 1,200 words (`LONG_TEXT_WORDS`) and left off for a longer one (it can be translated page by page in the reader); the method list is the models on this Mac plus the online services that can be used (`newMaterial.translateChoices`). In the reader a one-page material's Translation menu has one button, "Translate this material"; the vocabulary panel shows the statistics of the whole material in one section (words, time to read, known share, counts), with the new words of the page under it.
