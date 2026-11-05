"""
StarDict dictionaries (the common format of free dictionaries: a .ifo, an .idx and a .dict or .dict.dz file) made into packs.

The .idx lists words, each with where its article is in the .dict file (offset and size, big endian). Articles are plain text, HTML or XDXF
(per the .ifo's sametypesequence): the tags are taken out and each line becomes a meaning.
"""

import gzip
import html
import json
import os
import re
import struct
import tarfile
import zipfile

from ocarina.dictionaries import pack

MAX_SENSES = 10
LICENSE_UNKNOWN = "as given by the dictionary"


class StarDictError(Exception):
    "The files are not a StarDict dictionary Ocarina can read; the message says why."


def read_ifo(path):
    "The key=value lines of an .ifo file."
    values = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    if not lines or not lines[0].startswith("StarDict"):
        raise StarDictError("That is not a StarDict dictionary (the .ifo file is wrong).")
    for line in lines[1:]:
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


_TAGS = re.compile(r"<[^>]+>")
_BREAKS = re.compile(r"<\s*(br|/p|/div|/li|/k|/def|/ex)\b[^>]*>|</?(ol|ul|p|div)\b[^>]*>", re.I)


def plain(article):
    "The text lines of an article, markup removed."
    text = _BREAKS.sub("\n", article)
    text = html.unescape(_TAGS.sub("", text))
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


def _articles(ifo, folder, base):
    """(word, article text) for every entry; reads the whole .dict file (dictzip is plain gzip to read from the start)."""
    idx_path = os.path.join(folder, base + ".idx")
    if not os.path.exists(idx_path):
        gz = idx_path + ".gz"
        if not os.path.exists(gz):
            raise StarDictError("The .idx file is missing.")
        with gzip.open(gz, "rb") as f:
            index = f.read()
    else:
        with open(idx_path, "rb") as f:
            index = f.read()
    dict_path = os.path.join(folder, base + ".dict.dz")
    if os.path.exists(dict_path):
        with gzip.open(dict_path, "rb") as f:
            data = f.read()
    elif os.path.exists(os.path.join(folder, base + ".dict")):
        with open(os.path.join(folder, base + ".dict"), "rb") as f:
            data = f.read()
    else:
        raise StarDictError("The .dict (or .dict.dz) file is missing.")
    offset_size = 8 if ifo.get("idxoffsetbits") == "64" else 4
    fmt = ">Q" if offset_size == 8 else ">I"
    position, length = 0, len(index)
    while position < length:
        end = index.index(b"\0", position)
        word = index[position:end].decode("utf-8", errors="replace")
        position = end + 1
        (offset,) = struct.unpack(fmt, index[position : position + offset_size])
        (size,) = struct.unpack(">I", index[position + offset_size : position + offset_size + 4])
        position += offset_size + 4
        yield word, data[offset : offset + size].decode("utf-8", errors="replace")


def convert(folder, destination, code, name=None, meaning="en", pack_id=None):
    "Make a pack from the StarDict files in a folder (the .ifo names the dictionary); returns the number of entries."
    ifos = [f for f in os.listdir(folder) if f.endswith(".ifo")]
    if not ifos:
        raise StarDictError("There is no .ifo file: a StarDict dictionary has an .ifo, an .idx and a .dict (or .dict.dz) file.")
    base = ifos[0][:-4]
    ifo = read_ifo(os.path.join(folder, ifos[0]))
    title = name or ifo.get("bookname") or base
    pid = pack_id or "stardict-" + re.sub(r"[^a-z0-9]+", "-", f"{code}-{title}".lower()).strip("-")
    db = pack.create(
        destination,
        {
            "id": pid,
            "name": title,
            "language": code,
            "meaning": meaning,
            "license": ifo.get("description") or LICENSE_UNKNOWN,
            "source": ifo.get("website") or "",
            "kind": "stardict",
        },
    )
    rows = []
    for word, article in _articles(ifo, folder, base):
        lines = plain(article)
        if lines:
            rows.append((word, pack.fold(word), "", 0, json.dumps([{"text": line} for line in lines[:MAX_SENSES]], ensure_ascii=False)))
    if not rows:
        raise StarDictError("The dictionary has no readable entries.")
    db.executemany("insert into entry (word, word_lc, pos, importance, senses) values (?, ?, ?, ?, ?)", rows)
    pack.finish(db)
    return len(rows)


def unpack(archive, folder):
    "Unpack a .zip or .tar(.gz/.bz2/.xz) of StarDict files into a folder (flat: names only, no paths)."
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                name = os.path.basename(info.filename)
                if name and not info.is_dir():
                    with z.open(info) as src, open(os.path.join(folder, name), "wb") as out:
                        out.write(src.read())
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive) as t:
            for member in t.getmembers():
                name = os.path.basename(member.name)
                if name and member.isfile():
                    src = t.extractfile(member)
                    with open(os.path.join(folder, name), "wb") as out:
                        out.write(src.read())
    else:
        raise StarDictError("That archive could not be opened (.zip, .tar.gz, .tar.bz2 and .tar.xz work).")
