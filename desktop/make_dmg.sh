#!/bin/bash
# Makes dist/Ocarina.dmg from dist/Ocarina.app: the app, a shortcut to Applications, and a note about the first start.
# The app is not signed with an Apple ID, so macOS asks once: right-click the app, Open, Open.
set -euo pipefail
cd "$(dirname "$0")"
[ -d dist/Ocarina.app ] || { echo "Build the app first: ./build.sh" >&2; exit 1; }
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
cp -R dist/Ocarina.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cat > "$STAGE/Read me first.txt" <<'T'
Ocarina

1. Drag Ocarina into the Applications folder.
2. The first time, do not double-click it. Right-click (or Control-click) Ocarina, choose Open, then Open again.
   macOS asks because the app is not signed with an Apple ID; it is only needed once.
   If you only see "Done" and "Move to Trash": open System Settings > Privacy & Security, scroll down, press "Open Anyway".
3. Needs a Mac with Apple silicon (M1 or later) and macOS 13 or later.

Models (voices, translation) are downloaded from inside the app, so the first start needs the internet.
Credits and licences: Settings > About and licences, or NOTICE.md inside the app.
T
rm -f dist/Ocarina.dmg
hdiutil create -volname "Ocarina" -srcfolder "$STAGE" -fs HFS+ -format UDZO -imagekey zlib-level=9 dist/Ocarina.dmg >/dev/null
du -sh dist/Ocarina.dmg
