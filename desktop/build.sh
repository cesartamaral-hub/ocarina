#!/bin/bash
# Build dist/Ocarina.app. Run from the desktop/ folder.
# Needs ../.venv-build (pyenv Python 3.12) and a built frontend (cd ../frontend && npm run build).
set -e
cd "$(dirname "$0")"
PY=../.venv-build/bin/python
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
du -sh dist/Ocarina.app
