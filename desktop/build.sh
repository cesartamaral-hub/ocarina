#!/bin/bash
# Build dist/Ocarina.app. Run from the desktop/ folder.
# Needs ../.venv-build2 (Python 3.12 from python.org, which runs on old macOS; see docs/ocarina/packaging.md) and a built frontend (cd ../frontend && npm run build).
set -e
cd "$(dirname "$0")"
PY=../.venv-build2/bin/python
[ -f ../ocarina/web/dist/index.html ] || { echo "The frontend is not built (ocarina/web/dist/index.html is missing): run npm run build in frontend/ first and look at its errors." >&2; exit 1; }
# MLX comes in one build per macOS; pip takes the newest this Mac allows, which then needs that macOS. Take the one for macOS 14, the oldest MLX supports.
$PY -m pip download -q mlx==0.32.4 mlx-metal==0.32.4 --no-deps --platform macosx_14_0_arm64 --python-version 3.12 --only-binary=:all: -d ../.mlx14
$PY -m pip install -q --force-reinstall --no-deps ../.mlx14/*.whl
$PY ../scripts/build_wikdict.py  # the dictionaries that come with the app (WikDict; made once, not in git)
# py2app's tkinter recipe starts Tcl; the python.org Python used here is not in /Library/Frameworks, so say where its Tcl is
FW=$(cd "$($PY -c 'import sys; print(sys.base_prefix)')" && pwd)
export TCL_LIBRARY="$FW/lib/tcl8.6" TK_LIBRARY="$FW/lib/tk8.6"
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
# Contents/MacOS/python (what runs downloads, voices and sync) is copied from the python.org framework with its loader path unchanged,
# "@executable_path/../../../../Python", which only holds inside that framework: point it at the Python the bundle carries.
install_name_tool -change "@executable_path/../../../../Python" "@executable_path/../Frameworks/Python.framework/Versions/3.12/Python" dist/Ocarina.app/Contents/MacOS/python
codesign --force --deep --sign - dist/Ocarina.app  # ad hoc: not an Apple ID signature, but keeps the bundle consistent
# The helper must start, and import what the workers need and make an HTTPS context (a build whose helper cannot start looks fine until a model is downloaded).
RES="$PWD/dist/Ocarina.app/Contents/Resources"
PYTHONHOME="" PYTHONUTF8=1 PYTHONPATH="$RES/lib/python3.12:$RES/lib/python312.zip:$RES/lib/python3.12/lib-dynload" dist/Ocarina.app/Contents/MacOS/python -c "import os, ssl; os.environ['SSL_CERT_FILE'] = os.environ['SSL_CERT_DIR'] = '/no/such/file'  # as the launcher sets them
import huggingface_hub, mlx.core
from ocarina import certs; certs.use_bundled(); ssl.create_default_context()" || { echo "The bundled helper python cannot start: downloads and voices would fail." >&2; exit 1; }
du -sh dist/Ocarina.app
