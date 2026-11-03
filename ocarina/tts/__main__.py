"""
Command-line test for the TTS service:

    python -m ocarina.tts say --lang nl --out nl.wav "Hallo wereld. Hoe gaat het?"
    python -m ocarina.tts say --lang pl --out pl.wav --file tekst.txt
"""

import argparse
import json
import os
import sys

import soundfile as sf

from ocarina.tts.cache import SentenceCache
from ocarina.tts.service import DEFAULT_VOICE, synthesize_text
from ocarina.tts.stitch import stitch
from ocarina.tts.supervisor import Supervisor

CATALOG = os.path.join(os.path.dirname(__file__), "catalog.json")
APP_DIR = os.path.expanduser("~/Library/Application Support/Ocarina")


def _say(args):
    with open(CATALOG, encoding="utf-8") as f:
        model = next(m for m in json.load(f)["models"] if m["id"] == args.model)
    if args.lang not in model["languages"]:
        sys.exit(f"{model['name']} does not support '{args.lang}'")
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = args.text
    cache = SentenceCache(os.path.join(APP_DIR, "tts_cache"))
    sup = Supervisor(model["engine"], repo=model["repositories"][0]["id"])

    def progress(i, n, sentence, _path, cached, secs):
        tag = "cached" if cached else f"{secs:5.1f}s"
        print(f"[{i + 1}/{n}] {tag}  {sentence[:60]}", flush=True)

    try:
        parts = synthesize_text(
            sup, cache, model["id"], text, args.lang, args.voice, progress
        )
    finally:
        sup.unload()
    audio, sr, starts = stitch([p for _, p, _ in parts], args.pause)
    sf.write(args.out, audio, sr)
    print(f"wrote {args.out}: {len(audio) / sr:.1f}s, sentence starts {starts}")


def main():
    "Parse arguments and run."
    parser = argparse.ArgumentParser(prog="python -m ocarina.tts")
    sub = parser.add_subparsers(dest="cmd", required=True)
    say = sub.add_parser("say", help="Generate speech for some text")
    say.add_argument("text", nargs="?", default="")
    say.add_argument("--file")
    say.add_argument("--lang", required=True)
    say.add_argument("--out", required=True)
    say.add_argument("--model", default="chatterbox-multilingual-v3-mlx")
    say.add_argument("--voice", default=DEFAULT_VOICE)
    say.add_argument("--pause", type=float, default=0.5)
    args = parser.parse_args()
    _say(args)


if __name__ == "__main__":
    main()
