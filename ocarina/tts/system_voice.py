"""
The Mac voice as a speech engine for books: each sentence is spoken with `say` into a wav, like the other engines, so the rest of the
pipeline (sentence cache, stitching, timings) does not change. It has the same two methods as the worker supervisor.

The voice is named in a small marker file, passed where the other engines get a voice clip: its content is part of the sentence cache
key, so another Mac voice never reuses sentences made by a different one.
"""

import hashlib
import os
import subprocess

from ocarina import tools


class SystemVoiceError(Exception):
    "A sentence could not be spoken; the message says why."


def marker(cache_dir, name):
    "The marker file for a Mac voice (made when missing); its path stands for the voice in the cache key."
    folder = os.path.join(cache_dir, "macvoice")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, hashlib.sha256(name.encode("utf-8")).hexdigest()[:16] + ".txt")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(name)
    return path


class SystemSupervisor:
    "synth(text, lang, voice, out, ref_text) like the worker supervisor; `voice` is a marker file naming the Mac voice."

    def synth(self, text, lang, voice, out, ref_text=None):  # pylint: disable=unused-argument
        say = tools.find("say")
        if not say:
            raise SystemVoiceError("This Mac cannot speak: the say program was not found.")
        with open(voice, encoding="utf-8") as f:
            name = f.read().strip()
        os.makedirs(os.path.dirname(out), exist_ok=True)
        part = out[:-4] + ".part.wav"
        done = subprocess.run(
            [say, "-v", name, "-o", part, "--data-format=LEI16@24000", "-f", "-"],
            input=text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=120,
        )
        if done.returncode != 0 or not os.path.exists(part):
            raise SystemVoiceError(f"The voice {name} could not speak this sentence.")
        os.replace(part, out)

    def unload(self):
        "Nothing is kept loaded."
