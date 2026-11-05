"""
Make the dictionaries that come with the app: WikDict's Dutch, Polish and French to English, as Ocarina packs in ocarina/dictionaries/builtin.

    python scripts/build_wikdict.py [--force]

About 50 MB are downloaded once (kept in a cache folder); the packs are not in git. desktop/build.sh runs this before it packs the app, and the
app makes any that are missing when it starts from the source.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ocarina.dictionaries import registry, wikdict  # noqa: E402  pylint: disable=wrong-import-position

if __name__ == "__main__":
    wikdict.build_all(registry.BUILTIN_DIR, os.path.join(tempfile.gettempdir(), "ocarina-wikdict-cache"), force="--force" in sys.argv)
