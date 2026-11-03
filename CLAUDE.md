# Ocarina

Personal macOS app for studying Dutch, Polish and French. Hard fork of Lute v3 (MIT): Lute's
Python backend (`lute/`) is kept; the screens are being replaced by a React app (`frontend/`);
text-to-speech for books lives in `ocarina/`; `desktop/` packages it all as `Ocarina.app`.

Start here, then read only what the task needs:
- `PLAN.md` - status and roadmap (short). `docs/ocarina/architecture.md` - how the pieces fit.
- Every module in `ocarina/` starts with a docstring that says what it is and lists its endpoints.

## Commands
```bash
./desktop/dev.sh              # backend + Vite on a COPY of the library -> http://localhost:5173/ocarina/app/
./desktop/dev.sh --fresh      # new copy from the real library;  --real = the real library (careful)
source .venv/bin/activate && pytest tests/ocarina -q       # Ocarina tests, ~2 s
pytest --ignore=tests/acceptance --ignore=tests/playwright  # everything; all pass (Japanese tests need `brew install mecab mecab-ipadic`)
cd frontend && npx tsc -b && npm run lint && npm run build   # build goes to ocarina/web/dist (git-ignored)
cd desktop && ./build.sh      # builds desktop/dist/Ocarina.app (minutes); needs ../.venv-build
python -m ocarina.tts say --lang nl --out /tmp/x.wav "Hallo wereld."   # TTS from the command line
```
Two venvs: `.venv` (uv, Python 3.12: dev and tests; `pytest<9` is pinned because pytest-bdd breaks on 9)
and `.venv-build` (pyenv Python 3.12: only py2app can package that one). Tests need the git-ignored
`lute/config/config.yml` with `ENV: dev`, `DATAPATH: <repo>/data`, `DBNAME: test_lute.db`.

## Layout
- `ocarina/api/` one Flask blueprint per area (audio, books, jobs, pages, system, terms, tts_models, web); `__init__.register` wires them. Keep route functions thin; logic goes in `ocarina/tts/` or a service module.
- `ocarina/tts/` model-free TTS pipeline: sentences, cache, stitch, supervisor (worker process), worker, models (download), book_audio. `catalog.json` lists the voice models.
- `ocarina/prefs.py` preferences file in the data folder. `lute/` is Lute; change it only when a React screen replaces its behaviour; the only hook today is `register_ocarina(app)` in `lute/app_factory.py`.
- `frontend/src/`: `api/` (one file per area, import from `./api`), `reader/` (Reader, TermPanel, hooks), `BookList`, `BookView`, `Settings`, `AudioBar`. Hash routes: `#/`, `#/book/<id>`, `#/book/<id>/read/<page>`, `#/settings`.
- `desktop/` pywebview launcher, py2app `setup.py`, `build.sh`, dev scripts. `assets/` icon sources. `tests/ocarina/` our tests (use `helpers.py`).

## Rules that save time
- **Never test against the real library** (`~/Library/Application Support/Ocarina`): use `./desktop/dev.sh` (copy) or the test fixtures. Audio jobs overwrite book audio.
- Ask before committing or pushing. Commit messages end with the Co-Authored-By line from the session.
- Test in the browser before saying a UI change works; say plainly what was not checked.
- Settings go through `getPref`/`setPref` (server file), never `localStorage`: the packaged app uses a new port each launch, so web storage is lost.
- The TTS worker must never download: it runs with `HF_HUB_OFFLINE=1`; downloads go through `ocarina/tts/models.py`.
- In the packaged app the worker runs on `Contents/MacOS/python` with `PYTHONPATH` from `RESOURCEPATH` (the launcher starts Python in ASCII mode). `mlx` is copied into the bundle by `build.sh` (py2app cannot find namespace packages).
- React: lint warns on setState inside effects and on components defined in render; fix, don't silence.

## Adding a feature (one session each)
1. Read `PLAN.md` status and the one module you change. Don't read the whole repo.
2. Backend: add the route to the right `ocarina/api/*.py` (or a new module + one line in `__init__`), logic in a testable module, tests in `tests/ocarina/`.
3. Frontend: add API calls to `frontend/src/api/<area>.ts`; keep components under ~300 lines, hooks in their own files.
4. Run the checks above, try it in the dev copy, update `PLAN.md` (one or two lines) and the architecture doc if the shape changed.
