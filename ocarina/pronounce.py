"""
Hear a word or a few words said aloud.

    say(...)  -> (path of an audio file, the source that made it, a note or None)

Sources, in the order the user prefers them (the setting "pronounce.source", "voice" by default):

    voice    the model and voice chosen for the language under Settings (the same voice as the book audio); the model stays loaded
             for a few minutes so the next word is quick
    speaker  a recording of a person saying the word, from Wiktionary (single words only)
    google   Google Translate's voice (an unofficial address that can stop working; the text is sent to Google; online)
    system   the voice of this Mac (instant, offline)

A source that cannot be used (no model, no recording, no internet) gives way to the system voice, with a note saying so. Results
are kept in <data folder>/pronounce_cache, so a word heard once plays at once, offline.
"""

import hashlib
import os
import re
import subprocess
import tempfile
import threading

import requests

from ocarina import tools
from ocarina.tts import models as model_files
from ocarina.tts import voices
from ocarina.tts.service import voice_digest
from ocarina.tts.supervisor import Supervisor, TtsError

SOURCES = ("voice", "speaker", "google", "system")
MAX_TEXT = 300
GOOGLE_MAX = 190  # the address takes about 200 characters
TIMEOUT = 8
USER_AGENT = "Ocarina/1.0 (personal language-learning app; https://github.com/cesartamaral-hub/ocarina)"
IDLE_SECONDS = 300
SECTIONS = {"nl": "Dutch", "pl": "Polish", "fr": "French"}  # Wiktionary's language sections
MAC_LOCALES = {"nl": ("nl_NL", "nl_BE"), "pl": ("pl_PL",), "fr": ("fr_FR", "fr_CA")}


class Unavailable(Exception):
    "A source cannot say this text; the message says why (shown as the note)."


def cache_dir(datapath):
    return os.path.join(datapath, "pronounce_cache")


def cache_path(datapath, key, ext="wav"):
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return os.path.join(cache_dir(datapath), digest[:2], f"{digest}.{ext}")


def _convert(src, dst):
    "Any audio file to a mono wav that every player reads (the web view of this app cannot play Ogg)."
    ffmpeg = tools.ffmpeg()
    if not ffmpeg:
        raise Unavailable("ffmpeg is needed to play this and was not found.")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    part = dst + ".part.wav"
    subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", src, "-ac", "1", "-ar", "24000", part], check=True, timeout=60)
    os.replace(part, dst)


# --- the voice chosen for the language, kept loaded for a few minutes --------------------------------------------------------


class _WarmVoice:
    "One speech model in a worker, loaded on first use and unloaded after a quiet spell."

    def __init__(self):
        self._lock = threading.Lock()
        self._supervisor = None
        self._key = None
        self._timer = None

    def synth(self, model, engine, text, code, voice_path, out, ref_text):  # pylint: disable=too-many-arguments,too-many-positional-arguments
        with self._lock:
            key = (model["id"], engine)
            if self._supervisor is None or self._key != key:
                self._stop()
                self._supervisor = Supervisor(engine, repo=model["repositories"][0]["id"])
                self._key = key
            try:
                self._supervisor.synth(text, code, voice_path, out, ref_text)
            finally:
                self._arm()

    def unload(self):
        with self._lock:
            self._stop()

    def _stop(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if self._supervisor:
            self._supervisor.unload()
            self._supervisor, self._key = None, None

    def _arm(self):
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(IDLE_SECONDS, self.unload)
        self._timer.daemon = True
        self._timer.start()


warm_voice = _WarmVoice()


def _from_voice(cfg, app_config, text, code, saved, busy):
    "The model and voice chosen for the language."
    if busy:
        raise Unavailable("Ocarina is making audio right now, so your voice is busy.")
    model = model_files.choose_model(None, saved.get(f"model.{code}"))
    if model is None:
        raise Unavailable("No voice model is chosen.")
    fake = app_config.get("OCARINA_TTS_ENGINE")
    if not fake and not model_files.is_installed(model):
        raise Unavailable(f"{model['name']} is not downloaded yet.")
    voice_id = saved.get(f"voice.{code}") or voices.default_voice_id(code)
    voice_path = voices.path_of(cfg.datapath, voice_id)
    if voice_path is None:
        raise Unavailable("The chosen voice was not found.")
    ref_text = voices.transcript_of(cfg.datapath, voice_id)
    out = cache_path(cfg.datapath, f"voice\n{model['id']}\n{code}\n{voice_digest(voice_path, ref_text)}\n{text}")
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        part = out[:-4] + ".part.wav"
        warm_voice.synth(model, fake or model["engine"], text, code, voice_path, part, ref_text)
        _trim(part)
        os.replace(part, out)
    return out


def _trim(path, level=0.02, keep=0.12):
    "Cut the silence the model leaves before and after a short text (keeping a little), so a word plays at once."
    import numpy as np  # pylint: disable=import-outside-toplevel
    import soundfile as sf  # pylint: disable=import-outside-toplevel

    try:
        samples, rate = sf.read(path)
    except (OSError, RuntimeError):
        return
    loud = np.abs(samples if samples.ndim == 1 else samples[:, 0])
    if not len(loud) or loud.max() == 0:
        return
    found = np.where(loud > level * loud.max())[0]
    start, end = max(int(found[0] - keep * rate), 0), min(int(found[-1] + keep * rate), len(loud))
    if end - start < len(loud):
        sf.write(path, samples[start:end], rate, format="WAV")


# --- a person saying the word ------------------------------------------------------------------------------------------------


def speaker_file(word, code):
    "Name of a recording of the word on Wikimedia Commons, from the word's Wiktionary entry; None when there is none."
    section = SECTIONS.get(code)
    if not section:
        return None
    r = requests.get(
        "https://en.wiktionary.org/w/api.php",
        params={"action": "parse", "page": word, "prop": "wikitext", "format": "json", "redirects": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    wikitext = (r.json().get("parse") or {}).get("wikitext", {}).get("*", "")
    body = re.search(rf"^=={section}==\s*$(.*?)(?=^==[^=]|\Z)", wikitext, re.M | re.S)
    if not body:
        return None
    files = re.findall(r"\{\{audio\|" + re.escape(code) + r"\|([^|}]+)", body.group(1))
    return files[0].strip() if files else None


def _from_speaker(cfg, text, code):
    if len(text.split()) != 1:
        raise Unavailable("Recordings of people exist for single words only.")
    out = cache_path(cfg.datapath, f"speaker\n{code}\n{text.lower()}")
    if os.path.exists(out):
        return out
    try:
        name = speaker_file(text.lower(), code) or speaker_file(text, code)
        if not name:
            raise Unavailable("Wiktionary has no recording of this word.")
        r = requests.get(
            "https://commons.wikimedia.org/wiki/Special:FilePath/" + requests.utils.quote(name),
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Unavailable("Wiktionary could not be reached.") from e
    with tempfile.TemporaryDirectory() as folder:
        raw = os.path.join(folder, "recording" + (os.path.splitext(name)[1] or ".ogg"))
        with open(raw, "wb") as f:
            f.write(r.content)
        _convert(raw, out)
    return out


# --- Google Translate's voice ------------------------------------------------------------------------------------------------


def _from_google(cfg, text, code):
    if len(text) > GOOGLE_MAX:
        raise Unavailable("Google's voice takes about 190 characters at most.")
    out = cache_path(cfg.datapath, f"google\n{code}\n{text}", "mp3")
    if os.path.exists(out):
        return out
    try:
        r = requests.get(
            "https://translate.google.com/translate_tts",
            params={"ie": "UTF-8", "q": text, "tl": code, "client": "tw-ob"},
            headers={"User-Agent": "Mozilla/5.0 (Macintosh) Ocarina/1.0"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Unavailable("Google's voice could not be reached (it is an unofficial address and may have stopped working).") from e
    if "audio" not in r.headers.get("Content-Type", "") or not r.content:
        raise Unavailable("Google did not answer with sound (the unofficial address may have stopped working).")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out + ".part", "wb") as f:
        f.write(r.content)
    os.replace(out + ".part", out)
    return out


# --- the voice of this Mac ---------------------------------------------------------------------------------------------------


def mac_voice(code):
    "Name of an installed macOS voice for the language, or None."
    say = tools.find("say")
    if not say:
        return None
    try:
        listing = subprocess.run([say, "-v", "?"], capture_output=True, text=True, timeout=10, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for locale in MAC_LOCALES.get(code, ()):
        for line in listing.splitlines():
            m = re.match(r"^(.+?)\s+" + locale + r"\s", line)
            if m:
                return m.group(1).strip()
    return None


def _from_system(cfg, text, code):
    voice = mac_voice(code)
    if voice is None:
        raise Unavailable("This Mac has no voice for this language.")
    out = cache_path(cfg.datapath, f"system\n{voice}\n{text}")
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        part = out[:-4] + ".part.wav"
        subprocess.run([tools.find("say"), "-v", voice, "-o", part, "--data-format=LEI16@24000", text], check=True, timeout=30)
        os.replace(part, out)
    return out


# --- choosing ----------------------------------------------------------------------------------------------------------------


def say(cfg, app_config, text, code, source, saved, busy=False):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """
    (path, source used, note). `source` is the one asked for; when it cannot be used the system voice answers instead, and the note says
    why. Raises Unavailable only when even the system voice cannot.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise Unavailable("Nothing to say.")
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT].rsplit(" ", 1)[0] or text[:MAX_TEXT]
    source = source if source in SOURCES else "voice"
    try:
        if source == "voice":
            return _from_voice(cfg, app_config, text, code, saved, busy), "voice", None
        if source == "speaker":
            return _from_speaker(cfg, text, code), "speaker", None
        if source == "google":
            return _from_google(cfg, text, code), "google", None
        return _from_system(cfg, text, code), "system", None
    except (Unavailable, TtsError, subprocess.SubprocessError, OSError) as e:
        reason = str(e) if isinstance(e, Unavailable) else "That voice failed."
        if source == "system":
            raise Unavailable(reason) from e
        return _from_system(cfg, text, code), "system", f"{reason} The voice of this Mac was used."
