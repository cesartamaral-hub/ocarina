# Packaging notes (py2app + pywebview)

- `desktop/ocarina_app.py` writes its own `config.yml` into the data folder, runs waitress on a
  random free port in a thread, and opens a pywebview window on `/ocarina/app/`.
  `OCARINA_APP_DIR` overrides the data folder (for testing against a copy).
- py2app 0.28 cannot package uv's standalone Python (`zlib` has no `__file__`): build with the
  python.org Python 3.12 (`.venv-build2`; see "Running on other Macs" below).
- `mlx` is a namespace package (no `__init__.py`): `setup.py` excludes it and `build.sh` copies it
  into `Contents/Resources/lib/python3.12/` by hand.
- The TTS worker cannot go through the app launcher (it starts Python in ASCII mode and
  `mlx_audio` fails reading a file). `ocarina/tts/supervisor.py` runs `Contents/MacOS/python -m
  ocarina.tts.worker` with `PYTHONPATH` built from `RESOURCEPATH`.
- Icon: `assets/Ocarina.icns` (made from `assets/ocarina-app-icon.svg`: render PNGs 16 to 1024,
  `iconutil -c icns`). Colours: paper `#fbfaf8`, green `#3d8b74` to `#265b4d`.
- Bundle size ~470 MB. Not done: signing and notarization (decided: unsigned for now), checking
  the window by double-click from Finder, first run without the model cached (Settings downloads it).

- The translation model needs `mlx-lm` in both venvs (`pip install mlx-lm`), and `mlx_lm` is listed in `desktop/setup.py`. The packaged worker loads it from the same HF cache as the voices (about 2.5 GB of memory while loaded, 7 MB more in the bundle).

## Disk image, ffmpeg and first start

- `scripts/build_ffmpeg.sh` builds a small LGPL-only static ffmpeg from the official source into `desktop/vendor/` (not in git). `desktop/build.sh` copies it to `Ocarina.app/Contents/Resources/bin`; `ocarina/tools.py` and `path_with_tools` look there first, so the model workers and yt-dlp use it too. Without it the app falls back to Homebrew's ffmpeg.
- `desktop/make_dmg.sh` makes `dist/Ocarina.dmg` (the app, an Applications shortcut, a "Read me first" note). The app is ad-hoc signed only, so the first start on another Mac needs right-click, Open.
- First start: `Welcome.tsx` asks for the languages, then offers the Recommended models (voice, translation, audio sync, transcription) with their sizes, downloaded one after another.

## Running on other Macs (macOS 14 and later)

A Python built on a new macOS only runs on that macOS (the pyenv Python of the first builds had a minimum of macOS 27 and crashed with "Symbol missing" on other Macs). `.venv-build2` is made from the python.org installer's Python 3.12.10 (minimum macOS 11, its own OpenSSL): download `python-3.12.10-macos11.pkg`, `pkgutil --expand-full` it (no install), copy `Python_Framework.pkg/Payload` to a folder, point every `/Library/Frameworks/Python.framework/Versions/3.12` reference in its binaries to that folder with `install_name_tool -change` and re-sign them ad hoc, then `python3.12 -m venv .venv-build2`, `pip install -r` the pinned packages, `pip install -e .`. `build.sh` also installs the macOS 14 builds of mlx and mlx-metal. The app sets `LSMinimumSystemVersion` 14.0 (MLX does not run on older macOS). Check a build with `vtool -show-build` over its `.so` and `.dylib` files: nothing may say `minos` above 14.0.

## Updates and releases

- `ocarina/version.py` holds the version; `desktop/setup.py` puts it in the app. `scripts/release.sh X.Y.Z` bumps it, runs the checks, builds the app and the DMG, writes `Ocarina.dmg.sha256`, commits, tags, and after a yes pushes and runs `gh release create` with both files.
- On each start the app asks GitHub for the latest release (`ocarina/updater.py`, `/ocarina/api/update`; off with Settings → General → Updates, and never while Work offline is on). A newer release that has `Ocarina.dmg` and a checksum shows a banner: Update now, Remind me tomorrow, Skip this version.
- Update now downloads the DMG inside the app (so macOS does not mark it as downloaded and no `xattr` step is needed), checks the SHA-256, unpacks the new app next to the installed one (`Ocarina.app.new`), checks its signature, and starts a helper that waits for the app to quit, swaps the two, opens the new one, and puts the old one back if the new one is not running 20 seconds later. The data folder is not touched.
- It only works for an app in a folder the user can write to (Applications). Drafts and pre-releases are ignored.

## Log file and bundle size

- `ocarina/logs.py` writes `<data folder>/logs/ocarina.log` (kept as `.log.1` when over 2 MB at the next start). In the app bundle it also takes over the process's stdout and stderr, so what the model workers print is in it too. Failed jobs, the folder move and update steps are logged. Settings → About and licences has "Open the log folder".
- Size: the app is about 690 MB (the DMG about 290 MB). The big parts are all needed: MLX and its Metal library (~170 MB), `transformers` (~120 MB; its architectures are not trimmed because models you add yourself may need any of them), the bundled WikDict packs (~90 MB), scipy, babel's locale data (courlan uses it). Removing setuptools and the Python test modules would save about 7 MB, which was not worth the risk.
- `scripts/release.sh` asks for a one or two line note for the release page (or take it as the second argument).
