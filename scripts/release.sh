#!/bin/bash
# Makes and publishes a release: ./scripts/release.sh 0.2.0 ["notes for the release"]
# Sets the version, runs the checks, builds the app and the disk image, commits, tags, and (after you say yes) pushes and creates the
# GitHub release with Ocarina.dmg and its checksum. Installed apps find it by themselves (ocarina/updater.py).
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="${1:?Usage: scripts/release.sh X.Y.Z [notes]}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "The version must look like 1.2.3" >&2; exit 1; }
TAG="v$VERSION"
command -v gh >/dev/null || { echo "The GitHub command line tool (gh) is needed." >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Sign in first: gh auth login" >&2; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "Commit or stash your changes first." >&2; exit 1; }
git rev-parse "$TAG" >/dev/null 2>&1 && { echo "$TAG already exists." >&2; exit 1; }
CURRENT=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' ocarina/version.py)
[ "$(printf '%s\n%s\n' "$CURRENT" "$VERSION" | sort -V | tail -1)" = "$VERSION" ] && [ "$CURRENT" != "$VERSION" ] || { echo "$VERSION is not newer than $CURRENT." >&2; exit 1; }
NOTES="${2:-}"
if [ -z "$NOTES" ]; then
  LAST=$(git describe --tags --abbrev=0 2>/dev/null || true)
  echo "Changes since ${LAST:-the start}:"
  git log -n 15 ${LAST:+$LAST..}HEAD --pretty='  - %s' | cut -c1-110
  echo
  read -r -p "What is new in $VERSION? One or two lines for the release page: " NOTES
  [ -n "$NOTES" ] || { echo "Write a short note (or pass it as the second argument)." >&2; exit 1; }
fi

echo "Releasing $VERSION (now $CURRENT)"
sed -i '' "s/^VERSION = \".*\"/VERSION = \"$VERSION\"/" ocarina/version.py

source .venv/bin/activate
pytest tests/ocarina -q
(cd frontend && npx tsc -b && npm run lint && npm test && npm run build)
OCARINA_RELEASE=1 ./desktop/build.sh
./desktop/make_dmg.sh
cd desktop/dist
shasum -a 256 Ocarina.dmg | awk '{print $1"  Ocarina.dmg"}' > Ocarina.dmg.sha256
cat Ocarina.dmg.sha256
cd ../..

git add ocarina/version.py
git commit -m "Release $VERSION"
git tag -a "$TAG" -m "Ocarina $VERSION"
echo
echo "Notes:"; echo "$NOTES"; echo
read -r -p "Push $TAG and publish the release on GitHub? [y/N] " answer
if [ "$answer" = "y" ]; then
  git push && git push origin "$TAG"
  gh release create "$TAG" desktop/dist/Ocarina.dmg desktop/dist/Ocarina.dmg.sha256 --repo cesartamaral-hub/ocarina --title "Ocarina $VERSION" --notes "$NOTES"
  echo "Published. Installed apps will offer $VERSION the next time they start."
else
  echo "Not published. The commit and tag are local: undo with  git tag -d $TAG && git reset --hard HEAD~1"
fi
