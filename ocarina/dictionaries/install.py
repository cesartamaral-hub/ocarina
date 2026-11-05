"""Putting packs in the user's folder: downloading the Wiktionary packs, importing StarDict dictionaries."""

import gzip
import hashlib
import json
import os
import shutil
import tempfile

import requests

from ocarina.dictionaries import languages, registry, stardict, wikdict, wiktextract

def catalog(codes=None):
    """
    The dictionaries that can be downloaded, for the languages with these codes (all the catalog knows when None): for each language the small
    WikDict one, the full Wiktionary one with English meanings, and where there is a Wiktionary edition in the language, the one in the language
    itself. Each is {id, type, name, language, languageName, meaning, description, bytes (of the data as read), download (on the wire), ...}.
    """
    found = []
    for code, e in languages.data()["languages"].items():
        if codes is not None and code not in codes:
            continue
        name = e["name"]
        base = {"language": code, "languageName": name}
        if "wikdict" in e:
            found.append(
                {
                    **base,
                    "id": f"wikdict-{code}-en",
                    "type": "wikdict",
                    "name": f"WikDict · {name} to English",
                    "meaning": "en",
                    "description": "Small and quick: the English words for each meaning. It has no inflected forms, so a form of a word may be missing.",
                    "bytes": e["wikdict"]["download"],
                    "download": e["wikdict"]["download"],
                }
            )
        if "wiktionary" in e:
            found.append(
                {
                    **base,
                    "id": f"wiktionary-{code}-en",
                    "type": "wiktionary",
                    "name": f"Wiktionary · {name} (full)",
                    "meaning": "en",
                    "description": "Every entry of the English Wiktionary for the language: meanings with example sentences, and the inflected forms, so a form leads to its base word.",
                    "kaikki": e["wiktionary"]["kaikki"],
                    "bytes": e["wiktionary"]["bytes"],
                    "download": e["wiktionary"]["download"],
                    "prebuilt": None,
                }
            )
        if "edition" in e:
            found.append(
                {
                    **base,
                    "id": f"wiktionary-{code}-{code}",
                    "type": "wiktionary",
                    "name": f"Wiktionary · {name}, in {name}",
                    "meaning": code,
                    "description": f"The {name} Wiktionary: words explained in {name} itself, with examples and inflected forms. Larger than the English one.",
                    "url": e["edition"]["url"],
                    "bytes": e["edition"]["bytes"],
                    "download": e["edition"]["download"],
                    "prebuilt": None,
                }
            )
    return found


def find(pack_id):
    return next((p for p in catalog() if p["id"] == pack_id), None)


def _destination(datapath, pack_id):
    return os.path.join(registry.user_dir(datapath), f"{pack_id}.sqlite")


def _finish(datapath, pack_id, temp):
    "Put a finished pack in place (replacing an older one) and forget the old open copy."
    target = _destination(datapath, pack_id)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    for pack in registry.all_packs(datapath):
        if pack.id == pack_id and pack.path == target:
            pack.close()
            registry._open.pop(target, None)  # pylint: disable=protected-access
    os.replace(temp, target)
    return target


def _fetch_prebuilt(entry, temp, on_progress, check):
    "Fetch a ready-made pack (gzipped) to `temp` and check it against the sum in the catalog; raises when it cannot be had."
    raw = temp + ".gz"
    digest = hashlib.sha256()
    with requests.get(entry["prebuilt"], stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or entry.get("prebuiltBytes") or 0)
        done = 0
        with open(raw, "wb") as out:
            for block in r.iter_content(1 << 20):
                check()
                out.write(block)
                digest.update(block)
                done += len(block)
                on_progress(done, total)
    if entry.get("sha256") and digest.hexdigest() != entry["sha256"]:
        raise ValueError("The downloaded dictionary is not the one that was published (its checksum differs).")
    with gzip.open(raw, "rb") as src, open(temp, "wb") as out:
        shutil.copyfileobj(src, out)
    os.remove(raw)


def _build_from_wikdict(entry, temp, on_progress, check):
    "Fetch WikDict's pair file for the language and make it into a pack."
    raw = temp + ".wikdict"
    try:
        with requests.get(wikdict.URL.format(pair=f"{entry['language']}-en"), stream=True, timeout=30, headers={"User-Agent": "Ocarina/1.0 (personal language-learning app)"}) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length") or entry.get("download") or 0)
            done = 0
            with open(raw, "wb") as out:
                for block in r.iter_content(1 << 20):
                    check()
                    out.write(block)
                    done += len(block)
                    on_progress(done, total)
        wikdict.convert(raw, temp, entry["language"], version="", kind="wikdict")
    finally:
        if os.path.exists(raw):
            os.remove(raw)


def _build_from_wiktextract(entry, temp, on_progress, check):
    url = entry.get("url") or wiktextract.URL.format(name=entry["kaikki"])
    total, lines = wiktextract.stream(url, check)
    total = entry.get("bytes") or total  # the size of the data as it is read; the Content-Length of a compressed answer is smaller
    seen = {"bytes": 0}

    def progress(n):
        seen["bytes"] += n + 1
        on_progress(min(seen["bytes"], total), total)

    wiktextract.convert_lines(lines, temp, entry["language"], {"id": entry["id"], "name": entry["name"], "meaning": entry["meaning"]}, progress)


def download(entry, datapath, on_progress, check):
    """
    Get one of the catalog's packs. A pack that is already made (entry["prebuilt"], a gzipped pack at an address, with its SHA-256 sum) is
    fetched and unpacked; when that cannot be had (not published yet, no longer there, a wrong sum) the Wiktextract data of the language is
    read as it arrives and made into a pack here, which downloads more and takes longer. on_progress(done, total) is in bytes.
    """
    fd, temp = tempfile.mkstemp(suffix=".sqlite", dir=_ensure(registry.user_dir(datapath)))
    os.close(fd)
    try:
        made = False
        if entry.get("type") == "wikdict":
            _build_from_wikdict(entry, temp, on_progress, check)
            made = True
        elif entry.get("prebuilt"):
            try:
                _fetch_prebuilt(entry, temp, on_progress, check)
                made = True
            except (requests.exceptions.RequestException, ValueError, OSError, EOFError) as e:
                if isinstance(e, ValueError) and "checksum" not in str(e):
                    raise
                on_progress(0, entry.get("bytes") or 0)  # start over with the data it is made from
        if not made:
            _build_from_wiktextract(entry, temp, on_progress, check)
        return _finish(datapath, entry["id"], temp)
    except BaseException:
        for path in (temp, temp + ".gz", temp + ".wikdict"):
            if os.path.exists(path):
                os.remove(path)
        raise


def _ensure(folder):
    os.makedirs(folder, exist_ok=True)
    return folder


def import_stardict(folder, datapath, code, name=None, meaning="en"):
    "Make a pack of a folder of StarDict files; returns (pack id, entries)."
    fd, temp = tempfile.mkstemp(suffix=".sqlite", dir=_ensure(registry.user_dir(datapath)))
    os.close(fd)
    try:
        count = stardict.convert(folder, temp, code, name=name, meaning=meaning)
        from ocarina.dictionaries.pack import Pack  # pylint: disable=import-outside-toplevel

        probe = Pack(temp)
        pack_id = probe.id
        probe.close()
        _finish(datapath, pack_id, temp)
        return pack_id, count
    except BaseException:
        if os.path.exists(temp):
            os.remove(temp)
        raise
