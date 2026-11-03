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
- **Node/npm: not installed yet** (needed for the React frontend).
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

1. **Listen and decide.** Play the Dutch, Polish and French clips from MLX (and PyTorch for
   comparison). If a language sounds bad, test CosyVoice2 and Voxtral for it before going further.
2. **Housekeeping.** Install Node. Decide on `.gitmodules` URL. Add `spike/`, `bench/` handling
   and `.gitignore` entries. First commit on `develop` (ask before committing).
3. **TTS service.** Worker process, MLX engine, reference-voice handling, per-sentence cache,
   CLI test (no UI). Include a long-text test and a first-run download test.
4. **Backend API.** JSON endpoints for books, terms and TTS jobs, next to the existing routes.
5. **React shell.** Vite project, served by Flask, loaded in the pywebview window; first screen:
   book list and reader.
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
