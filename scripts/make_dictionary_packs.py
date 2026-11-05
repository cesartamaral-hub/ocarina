"""
Make the Wiktionary packs of the catalog as ready-made files, to put somewhere permanent (a GitHub release) so that the app need not read
kaikki.org's data itself:

    python scripts/make_dictionary_packs.py [folder] [pack id ...]

For each pack: <id>.sqlite (what the app uses), <id>.sqlite.gz (what is uploaded) and a manifest.json with the sizes and SHA-256 sums. Takes a
few minutes and downloads about 1.2 GB (compressed) of Wiktextract data; nothing is uploaded.
"""

import gzip
import hashlib
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ocarina.dictionaries import install, wiktextract  # noqa: E402  pylint: disable=wrong-import-position


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(folder, only):
    os.makedirs(folder, exist_ok=True)
    manifest_path = os.path.join(folder, "manifest.json")
    manifest = json.load(open(manifest_path, encoding="utf-8")) if os.path.exists(manifest_path) else {}
    for entry in install.catalog():
        if only and entry["id"] not in only:
            continue
        started = time.time()
        pack_path = os.path.join(folder, f"{entry['id']}.sqlite")
        url = entry.get("url") or wiktextract.URL.format(name=entry["kaikki"])
        print(f"{entry['id']}: reading {url} …", flush=True)
        _, lines = wiktextract.stream(url)
        count = wiktextract.convert_lines(
            lines, pack_path, entry["language"], {"id": entry["id"], "name": entry["name"], "meaning": entry["meaning"], "version": time.strftime("%Y-%m-%d")}
        )
        gz_path = pack_path + ".gz"
        with open(pack_path, "rb") as src, gzip.open(gz_path, "wb", compresslevel=9) as out:
            shutil.copyfileobj(src, out)
        manifest[entry["id"]] = {
            "file": os.path.basename(gz_path),
            "entries": count,
            "bytes": os.path.getsize(pack_path),
            "gzBytes": os.path.getsize(gz_path),
            "sha256": sha256(gz_path),
            "made": time.strftime("%Y-%m-%d"),
        }
        print(f"{entry['id']}: {count:,} entries, {os.path.getsize(pack_path) / 1e6:.0f} MB, {os.path.getsize(gz_path) / 1e6:.0f} MB gzipped, {time.time() - started:.0f} s", flush=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    args = sys.argv[1:]
    target = args[0] if args and not args[0].startswith("wiktionary-") else os.path.expanduser("~/Lute-Ocarina/dictionary-packs")
    main(target, [a for a in args if a.startswith("wiktionary-")])
