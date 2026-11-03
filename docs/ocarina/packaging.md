# Packaging notes (py2app + pywebview)

- `desktop/ocarina_app.py` writes its own `config.yml` into the data folder, runs waitress on a
  random free port in a thread, and opens a pywebview window on `/ocarina/app/`.
  `OCARINA_APP_DIR` overrides the data folder (for testing against a copy).
- py2app 0.28 cannot package uv's standalone Python (`zlib` has no `__file__`): build with the
  pyenv Python 3.12 (`.venv-build`, created with `--enable-shared`).
- `mlx` is a namespace package (no `__init__.py`): `setup.py` excludes it and `build.sh` copies it
  into `Contents/Resources/lib/python3.12/` by hand.
- The TTS worker cannot go through the app launcher (it starts Python in ASCII mode and
  `mlx_audio` fails reading a file). `ocarina/tts/supervisor.py` runs `Contents/MacOS/python -m
  ocarina.tts.worker` with `PYTHONPATH` built from `RESOURCEPATH`.
- Icon: `assets/Ocarina.icns` (made from `assets/ocarina-app-icon.svg`: render PNGs 16 to 1024,
  `iconutil -c icns`). Colours: paper `#fbfaf8`, green `#3d8b74` to `#265b4d`.
- Bundle size ~470 MB. Not done: signing and notarization (decided: unsigned for now), checking
  the window by double-click from Finder, first run without the model cached (Settings downloads it).
