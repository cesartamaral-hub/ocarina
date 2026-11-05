#!/bin/bash
# Build dist/Ocarina.app. Run from the desktop/ folder.
# Needs ../.venv-build (pyenv Python 3.12) and a built frontend (cd ../frontend && npm run build).
set -e
cd "$(dirname "$0")"
PY=../.venv-build/bin/python
[ -f ../ocarina/web/dist/index.html ] || { echo "The frontend is not built (ocarina/web/dist/index.html is missing): run npm run build in frontend/ first and look at its errors." >&2; exit 1; }
$PY ../scripts/build_wikdict.py  # the dictionaries that come with the app (WikDict; made once, not in git)
rm -rf build dist
$PY setup.py py2app
# mlx is a namespace package (no __init__.py), which py2app cannot discover:
# copy it, with its native libraries and Metal shaders, into the bundle by hand.
SP=$($PY -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")
cp -R "$SP/mlx" dist/Ocarina.app/Contents/Resources/lib/python3.12/mlx

# Trim what the app never loads: test suites bundled inside packages, MLX's C++ headers and cmake files, type stubs.
# (The 214 MB mlx.metallib holds the Metal shaders and must stay.)
LIB=dist/Ocarina.app/Contents/Resources/lib/python3.12
rm -rf "$LIB/mlx/include" "$LIB/mlx/lib/cmake"
find "$LIB" -type d \( -name tests -o -name test \) -prune -exec rm -rf {} +
find "$LIB" -name "*.pyi" -delete

# ffmpeg: our own small LGPL build (scripts/build_ffmpeg.sh makes it once). Without it the app uses Homebrew's, when there is one.
RES=dist/Ocarina.app/Contents/Resources
if [ -x vendor/ffmpeg ]; then
  mkdir -p "$RES/bin" && cp vendor/ffmpeg "$RES/bin/ffmpeg" && cp vendor/ffmpeg-LICENSE.txt "$RES/ffmpeg-LICENSE.txt"
else
  echo "Note: desktop/vendor/ffmpeg is missing, so this app will not carry ffmpeg (run scripts/build_ffmpeg.sh)." >&2
fi
codesign --force --deep --sign - dist/Ocarina.app  # ad hoc: not an Apple ID signature, but keeps the bundle consistent
du -sh dist/Ocarina.app
