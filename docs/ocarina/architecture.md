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
| `books.py` | `GET /books`, `GET /books/<id>/sentences` (with start times if audio is ours) |
| `pages.py` | `GET /books/<id>/pages/<n>` (opens the page), `POST .../finish`, `GET/PUT .../text` |
| `terms.py` | `GET /terms/<id>`, `POST /terms`, `GET /terms/lookup`, `PATCH /terms/<id>/status`, `POST /terms/bulk-status`, `GET /terms/<id>/popup`, `GET /terms/<id>/references`, `POST/DELETE /terms/<id>/image` |
| `audio.py` | `POST /books/<id>/audio` (job), `GET /books/<id>/audio/sentences` |
| `jobs.py` | `GET /jobs`, `GET /jobs/<id>`, `POST /jobs/<id>/cancel`; a FIFO queue run one job at a time by one thread (audio and downloads share it); jobs call `check()` to notice cancelling |
| `tts_models.py` | `GET /tts/models`, `POST /tts/models/<id>/download`, `POST /tts/models/<id>/import` (copy from a folder, matched by file name and size), `DELETE /tts/models/<id>` |
| `audio.py` also: `POST /books/<id>/audio/upload` (own audio file; removes a replaced generated file, keeps recordings) |
| `book_import.py` | `GET /languages`, `POST /books/extract` (file or URL, nothing saved), `POST /books` (save, optional own audio) |
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
`TermPanel.tsx` (word panel), `useAudioFollow.ts`, `useHoverCard.tsx`. Preferences load once at
start (`loadPrefs`) and are read with `getPref`.

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
