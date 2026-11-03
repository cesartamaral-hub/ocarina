"""
Reference voices: the short clips Chatterbox imitates.

One clip ships with the app ("default"); the user's own clips live in <data folder>/voices as wav
files (whatever they upload is converted to mono wav, so the model always gets a format it can read).
"""

import io
import os
import re

import numpy as np
import soundfile as sf

from ocarina.tts.service import DEFAULT_VOICE

BUILTIN_ID = "default"
MIN_SECONDS, MAX_SECONDS = 3, 60
MAX_BYTES = 25 * 1024 * 1024
READABLE = (".wav", ".mp3", ".flac", ".ogg")

SAMPLE_TEXT = {
    "nl": "Goedemorgen! Vandaag is het mooi weer, dus ik ga naar het strand.",
    "pl": "Dzień dobry! Dzisiaj jest ładna pogoda, więc idę na plażę.",
    "fr": "Bonjour ! Aujourd'hui il fait beau, alors je vais à la plage.",
}


class VoiceError(Exception):
    "A voice clip can't be used; the message says why."


def voices_dir(datapath):
    "Where the user's clips live."
    return os.path.join(datapath, "voices")


def _slug(name):
    slug = re.sub(r"[^\w\-]+", "-", name.strip(), flags=re.UNICODE).strip("-_")
    return slug[:60]


def _seconds(path):
    info = sf.info(path)
    return round(info.duration, 1)


def list_voices(datapath):
    "All voices: the built-in one first, then the user's, by name."
    voices = [{"id": BUILTIN_ID, "name": "Default", "builtin": True, "seconds": _seconds(DEFAULT_VOICE), "transcript": ""}]
    folder = voices_dir(datapath)
    if os.path.isdir(folder):
        for filename in sorted(os.listdir(folder), key=str.lower):
            stem, ext = os.path.splitext(filename)
            if ext == ".wav":
                voices.append(
                    {
                        "id": stem,
                        "name": stem,
                        "builtin": False,
                        "seconds": _seconds(os.path.join(folder, filename)),
                        "transcript": transcript_of(datapath, stem) or "",
                    }
                )
    return voices


def path_of(datapath, voice_id):
    "File path of a voice, or None if there is no such voice."
    if not voice_id or voice_id == BUILTIN_ID:
        return DEFAULT_VOICE
    if voice_id != _slug(voice_id):
        return None
    path = os.path.join(voices_dir(datapath), voice_id + ".wav")
    return path if os.path.isfile(path) else None


def transcript_of(datapath, voice_id):
    "The words spoken in a voice clip, if the user gave them; else None."
    path = os.path.join(voices_dir(datapath), voice_id + ".txt")
    if voice_id == BUILTIN_ID or not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read().strip() or None


def add_voice(datapath, filename, stream, name=None, transcript=None):
    "Check an uploaded clip, save it as mono wav (and the words spoken in it), and return its entry."
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in READABLE:
        raise VoiceError("Use a wav, mp3, flac or ogg file.")
    data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise VoiceError("The file is larger than 25 MB.")
    voice_id = _slug(name or os.path.splitext(os.path.basename(filename))[0])
    if not voice_id or voice_id == BUILTIN_ID:
        raise VoiceError("Give the voice a name.")
    try:
        audio, rate = sf.read(io.BytesIO(data), always_2d=True)
    except Exception as e:  # pylint: disable=broad-exception-caught
        raise VoiceError(f"Can't read that audio file ({e}).") from e
    seconds = len(audio) / rate
    if not MIN_SECONDS <= seconds <= MAX_SECONDS:
        raise VoiceError(f"The clip is {seconds:.0f} seconds; use one between {MIN_SECONDS} and {MAX_SECONDS}. 10 to 20 seconds of clean speech works best.")
    folder = voices_dir(datapath)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, voice_id + ".wav")
    if os.path.exists(path):
        raise VoiceError(f'A voice named "{voice_id}" already exists.')
    sf.write(path, np.mean(audio, axis=1), rate, subtype="PCM_16")
    transcript = (transcript or "").strip()
    if transcript:
        with open(os.path.join(folder, voice_id + ".txt"), "w", encoding="utf-8") as f:
            f.write(transcript)
    return {"id": voice_id, "name": voice_id, "builtin": False, "seconds": round(seconds, 1), "transcript": transcript}


def delete_voice(datapath, voice_id):
    "Remove one of the user's clips; False if there is none."
    path = path_of(datapath, voice_id)
    if voice_id == BUILTIN_ID or path is None:
        return False
    os.remove(path)
    if os.path.exists(path[:-4] + ".txt"):
        os.remove(path[:-4] + ".txt")
    return True
