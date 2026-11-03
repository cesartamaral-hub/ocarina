# Ocarina plan

Personal macOS app for studying Dutch, Polish and French. Fork of Lute v3 (MIT).
Fork: `cesartamaral-hub/ocarina` (remote `upstream` = `LuteOrg/lute-v3`).

## Goals

1. Double-clickable Mac app: no terminal, no visible localhost.
2. Keep Lute's Python backend; replace the Flask HTML screens with a React frontend.
3. Generate audio for texts with a local TTS engine, with a model picker.

Not goals: Japanese (MeCab not installed, those tests are ignored), Windows/Linux, App Store.

## Environment (verified 2026-11-03)

- M1 Max, 32 GB, macOS 27.0, Xcode installed. ffmpeg 9.0.2, uv, pyenv, brew present.
- Node 26.13.0 / npm 11.20.0 (Homebrew), for the React frontend.
- Project: `~/Lute-Ocarina/ocarina` (branch `develop`).
- Submodule `lute/db/language_defs` is initialized. `.gitmodules` uses an SSH URL that fails
  here; the local git config overrides it to HTTPS. Decide whether to commit the HTTPS URL.
- Python venvs:
  - `.venv`: uv Python 3.12.13, for development and tests. **Cannot be packaged by py2app.**
  - `.venv-build`: pyenv Python 3.12.13 (`--enable-shared`), for py2app builds.
- Tests need `lute/config/config.yml` (git-ignored) with `ENV: dev`, a `DATAPATH`, and
  `DBNAME: test_lute.db` (same three lines as Lute's CI).

### Test baseline

`pytest --ignore=tests/acceptance --ignore=tests/playwright`: **495 passed, 12 failed.**

- All 12 failures are Japanese/MeCab. Ignore them.
  Unconfirmed: `test_rendering.py::test_bug_fix_ru_at_end_of_sentence` (assumed Japanese).
- pytest must be `<9` (venv has 8.4.2): pytest-bdd 7.3 breaks on pytest 9. This pin is only in
  the venv, not in `pyproject.toml` (kept out to stay merge-friendly with upstream).

## Packaging spike (done, `spike/`)

`spike/ocarina_app.py` writes its own `config.yml` to `~/Library/Application Support/Ocarina`,
runs waitress on `127.0.0.1` on a random free port in a thread, and opens a pywebview window.
`spike/setup.py` builds it with py2app.

- Result: `Ocarina.app`, 56 MB. Opened with `open`, it served the index page and static CSS (HTTP 200).
- **Not verified:** the window itself (no screenshot possible), code signing, notarization.
- Gotchas:
  - py2app 0.28.10 fails on uv's standalone Python (`zlib` has no `__file__`). Use the pyenv build.
  - perth (a Chatterbox dependency) needs `setuptools<81`.

## TTS benchmark (done, `~/Lute-Ocarina/bench`)

Test: Chatterbox Multilingual, ~25-word text per language, second (post-warmup) run.

| Engine | Dutch | Polish | French | Time per second of audio | Load | Peak RAM |
|---|---|---|---|---|---|---|
| MLX (`mlx-audio`, `mlx-community/chatterbox-multilingual-v3`) | 3.3 s | 3.8 s | 3.3 s | **~0.54** | 2.5 s | 3.5 GB |
| PyTorch MPS | 27.7 s | 30.3 s | 27.0 s | ~4.2 | 11.5 s | 5.3 GB |
| PyTorch CPU | 33.2 s | 37.5 s | 33.0 s | ~5.3 | 11.7 s | 7.2 GB |

- **Decision: MLX is the default engine.** Faster than real time; PyTorch MPS is only ~20% faster than CPU.
- Licenses: `mlx-audio` MIT; model MIT (based on `ResembleAI/chatterbox`).
- The MLX model has **no built-in voice**; it needs a reference clip (`ref_audio`). Ocarina must
  ship a default reference clip and let the user choose others (voice cloning is built in).
  The benchmark used `out_cpu_nl.wav` for all three languages.
- **Not verified:** audio quality (nobody has listened to the clips yet), long texts, whether the
  MLX model works in a worker process, first-launch weight download (88 s on this connection).

## Architecture

```
Ocarina.app (py2app)
 ├─ pywebview window ──► React frontend (built static files)
 ├─ Flask/waitress backend on 127.0.0.1:<random port>  (Lute, JSON API added)
 └─ TTS worker process (MLX by default) ◄── job queue ── backend
User data: ~/Library/Application Support/Ocarina  (db, config, audio, models)
```

- **Frontend:** React, built with Node/Vite, served as static files by Flask. Screens are replaced
  one at a time; Lute's HTML routes stay until their React replacement exists.
- **Backend:** keep Lute's models and services. Add JSON endpoints beside the existing routes
  instead of rewriting them, so upstream merges stay manageable.
- **Models are not bundled.** Weights download on demand into the user data folder.

### TTS service

- Interface: `load(model)`, `synthesize(text, language, voice)`, `unload()`.
- Runs in a **child process** (idea from Handy): a crash or out-of-memory kill takes down only
  the worker; the supervisor can retry on another device and unload to give memory back.
- Audio is generated **sentence by sentence in the background**, saved per sentence (so edits
  re-generate only what changed), and playable as soon as the first sentences are ready.
- **Pace for learners.** The MLX voice sounds fine but is too fast for a learner (user feedback,
  2026-11-03). Requirements:
  - Playback speed control in the reader (about 0.6x to 1.0x), using the browser's
    pitch-preserving playback (`preservesPitch`). Audio is stored at its natural speed; no
    regeneration needed to change pace. Remember the chosen speed per language.
  - Adjustable pause between sentences.
  - Later: ship a slower, clearer reference voice (the reference clip sets speaking style).
    Not tested yet. Slowed samples made with ffmpeg `atempo` (0.85x, 0.7x) are in `bench/`;
    their quality is unchecked.
- Attach the result to the book via Lute's existing audio mechanism (`lute/useraudio`);
  check whether per-sentence files need a new mapping for sentence-level playback.

### Model catalog (inspired by Handy's `catalog.json`)

`tts_catalog.json`, one entry per engine/model: `id`, `name`, `description`, `languages`,
`license`, `family`, `repository`, pinned `revision`, `files` (size, sha256), `device`
(`mlx` / `mps` / `cpu` / `auto`), and measured speed from our benchmark. The Settings screen
filters by the text's language and offers download, progress, delete, and "preview voice".

| Engine | Role | Notes |
|---|---|---|
| Chatterbox Multilingual v3 (MLX) | Default | nl, pl, fr; MIT; measured above |
| Chatterbox Multilingual (PyTorch) | Fallback | Slower; keep only if MLX proves unreliable |
| CosyVoice2 | Backup | Not benchmarked yet |
| Parkiet | Optional, Dutch only | Not benchmarked yet |
| Voxtral TTS (MLX) | Candidate | Lists nl and fr but not pl; not tested |

Check each model's license before recommending or bundling it.

## Milestones

1. **Listen and decide.** DONE: all three MLX voices sound OK; too fast for a learner (see Pace).
2. **Housekeeping.** DONE: Node 26.13.0 / npm 11.20.0 installed (Homebrew). `.gitmodules` left
   as upstream (SSH); the HTTPS override stays in local git config only, to keep upstream merges
   clean. Test leftover `tests/zz_bkp/` is excluded via `.git/info/exclude`. Old Lute data
   (3 languages, 7 books, 543 terms, 5 audio files) was imported into
   `~/Library/Application Support/Ocarina`.
3. **TTS service.** DONE (`ocarina/tts/`): worker process with restart, MLX engine, reference
   voice, per-sentence cache, CLI (`python -m ocarina.tts say ...`). Still open: a long-text
   test and a first-run model download manager (dev venv downloads from Hugging Face).
4. **Backend API.** IN PROGRESS. Done (`ocarina/api/tts_routes.py`, registered with 2 lines in
   `lute/app_factory.py`): `GET /ocarina/api/tts/models`, `POST /ocarina/api/books/<id>/audio`
   (background job, one at a time; refuses to overwrite a user's own audio without
   `replace=true`), `GET /ocarina/api/jobs/<id>`, `GET /ocarina/api/books/<id>/audio/sentences`.
   Sentences come from Lute's language parser. The book's mp3 goes in Lute's single audio slot;
   sentence start times go in a sidecar `<audio>.sentences.json` (Lute's bookmarks stay the
   user's). Checked end to end with the real model on a scratch copy of your data (17 sentences
   of "Mijn naam is Carla", 36 s). Language to TTS code is by name (Dutch, Polish/Polski,
   French only). Still open: audio is only playable when the whole job finishes (no early
   playback), JSON endpoints for books/terms, cancel/queue, and `soundfile` MP3 writing must be
   checked inside the py2app bundle.
5. **React shell.** IN PROGRESS. Done: Vite + React + TypeScript in `frontend/`, built into
   `ocarina/web/dist` (git-ignored) and served by Flask at `/ocarina/app/`. Screens: book list
   (by language) and a book view with generate-audio button and progress, audio player with
   playback speed (0.5x to 1.0x, pitch preserved, remembered per language), pause setting,
   sentence list that highlights while playing and seeks on click. Checked in the browser on a
   scratch copy of your data: playback at 0.7x, click-to-seek, and a full generate job (23
   sentences). Still open: the real reader (word click, terms, statuses) still lives in Lute's
   screens (link "Open in Lute reader"). Build with `cd frontend && npm run build`.
   **Packaged app now includes the frontend and TTS** (`spike/build.sh`): the launcher opens
   `/ocarina/app/`, and a full audio job (23 sentences, real model) ran inside `Ocarina.app`
   on a scratch copy of the data (`OCARINA_APP_DIR` overrides the data folder for testing).
   Lessons: (1) mlx is a namespace package, so `build.sh` copies it into the bundle by hand and
   `setup.py` excludes it; (2) the TTS worker must run on the bundle's bare interpreter
   (`Contents/MacOS/python`, UTF-8 mode, with `PYTHONPATH` set from `RESOURCEPATH`), not through
   the app launcher, which starts Python in ASCII mode and breaks `mlx_audio`;
   (3) the bundle is 550 MB (transformers, scipy and others): trim later. Not yet checked: the
   window itself by eye, double-clicking from Finder, code signing, a Mac without the Hugging
   Face cache (first run must download the 2.7 GB model).
6. **Settings: TTS model catalog.** Picker, download manager, voice preview.
7. **Packaging for real.** Add the React build and TTS worker to the py2app bundle, confirm the
   window opens by double-click, then sign and (optionally) notarize.
8. **Port the remaining screens**, then retire the Flask templates one by one.

## Open questions

- Do the MLX clips sound good in all three languages, and which reference voice(s) to ship?
- Is `lute/db/language_defs` still the right place for Dutch, Polish and French definitions, or
  do we want to trim the language list?
- Keep tracking upstream `lute-v3`, or treat Ocarina as a hard fork once the React frontend lands?
- Sign with a personal developer certificate, or leave the app unsigned (right-click open)?
- Later, optional: speech-to-text for pronunciation or shadowing practice (Handy-style).
