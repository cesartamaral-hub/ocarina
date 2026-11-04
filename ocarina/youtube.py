"""
Text of a YouTube video (used by ocarina/importer.py).

    from_youtube(url, language, ...) -> Imported

The captions of the video come first (the ones a person wrote, then the automatic ones, then a translation as the last resort).
A video without captions is downloaded as sound and transcribed on this Mac by the Whisper model (`transcribe`, given by the
caller); the sound is deleted afterwards unless the user asked to keep it as the book's audio.
"""

import logging
import os
import re
import shutil
import tempfile
from urllib.parse import parse_qs, urlparse

import requests

from ocarina.importer import HEADERS, TIMEOUT, ImportFailed, Imported, clean_paragraphs, short_title

log = logging.getLogger("ocarina.importer")

PARAGRAPH = 450  # characters, about where a paragraph of captions is cut
NOISE = re.compile(r"[\[\(][^\]\)]{0,40}[\]\)]|[♪♫♬]")  # [Music], (applause), music notes
SENTENCE_END = re.compile(r"[.!?…]['\")\]]*$")
ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def video_id(url):
    "The 11-character id in a watch, short, embed, shorts or live link."
    parts = urlparse(url)
    host = (parts.hostname or "").lower()
    candidate = None
    if host.endswith("youtu.be"):
        candidate = parts.path.strip("/").split("/")[0]
    else:
        query = parse_qs(parts.query)
        if "v" in query:
            candidate = query["v"][0]
        else:
            bits = [b for b in parts.path.split("/") if b]
            if len(bits) >= 2 and bits[0] in ("embed", "shorts", "live", "v"):
                candidate = bits[1]
    if not candidate or not ID.match(candidate):
        raise ImportFailed("That YouTube link has no video in it. Open the video and copy its address.")
    return candidate


def video_title(url, vid):
    "The title from YouTube's public embed information; a plain name when it cannot be had."
    try:
        r = requests.get("https://www.youtube.com/oembed", params={"url": url, "format": "json"}, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("title") or f"YouTube {vid}"
    except (requests.exceptions.RequestException, ValueError):
        return f"YouTube {vid}"


def captions_to_text(snippets, generated):
    """
    Paragraphs from caption lines. Captions are short fragments, often without punctuation (the automatic ones), so a paragraph
    is cut after about PARAGRAPH characters, at a sentence end when the captions have them.
    """
    paragraphs, current = [], ""
    for raw in snippets:
        piece = re.sub(r"\s+", " ", NOISE.sub(" ", raw)).strip()
        if not piece:
            continue
        current = f"{current} {piece}".strip()
        if len(current) >= PARAGRAPH and (generated or SENTENCE_END.search(current)):
            paragraphs.append(current)
            current = ""
    if current:
        paragraphs.append(current)
    return clean_paragraphs("\n\n".join(paragraphs))


def _captions(vid, language):
    """
    (text, note) from the captions of a video, or (None, reason). Order: written in the language, automatic in the language, any
    caption YouTube can translate into the language.
    """
    from youtube_transcript_api import YouTubeTranscriptApi  # pylint: disable=import-outside-toplevel
    from youtube_transcript_api._errors import (  # pylint: disable=import-outside-toplevel
        AgeRestricted,
        IpBlocked,
        RequestBlocked,
        TranscriptsDisabled,
        VideoUnavailable,
        VideoUnplayable,
        YouTubeTranscriptApiException,
    )

    try:
        return _pick_and_fetch(list(YouTubeTranscriptApi().list(vid)), language)
    except TranscriptsDisabled:
        return None, "The video has no captions."
    except (AgeRestricted, VideoUnplayable):
        raise ImportFailed("That video is age-restricted or cannot be played, so it cannot be read.") from None
    except VideoUnavailable:
        raise ImportFailed("That video is unavailable (private, removed or not found).") from None
    except (RequestBlocked, IpBlocked):
        return None, "YouTube refused to give the captions to this computer."
    except requests.exceptions.RequestException as e:
        raise ImportFailed("YouTube could not be reached. Check your connection.") from e
    except YouTubeTranscriptApiException:
        log.warning("The captions could not be read", exc_info=True)
        return None, "The captions could not be read."


def _pick_and_fetch(available, language):
    "The best caption track for the language, fetched; (None, reason) when there is none."

    def pick(generated):
        for t in available:
            if t.is_generated == generated and (not language or t.language_code.split("-")[0] == language):
                return t
        return None

    chosen = pick(False) or pick(True)
    note = None
    if chosen is None and language:
        for t in available:
            if t.is_translatable and any(code.language_code == language for code in t.translation_languages):
                chosen, note = t.translate(language), f"The captions are YouTube's translation of the {t.language} ones. Check them before saving."
                break
    if chosen is None:
        return None, "The video has no captions in this language."
    fetched = chosen.fetch()
    text = captions_to_text([s.text for s in fetched], chosen.is_generated)
    if chosen.is_generated and note is None:
        note = "These captions were made by YouTube automatically, so they can have mistakes and no punctuation. Check them before saving."
    return text, note


def _download_audio(url, folder, check=None, as_m4a=False):
    "The sound of the video as a file in `folder`; returns its path. as_m4a: converted to m4a, which every player and the sync read."
    import yt_dlp  # pylint: disable=import-outside-toplevel

    def hook(_):
        if check:
            check()

    options = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(folder, "audio.%(ext)s"),
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": TIMEOUT,
        "progress_hooks": [hook],
    }
    ffmpeg = shutil.which("ffmpeg") or next((p for p in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg") if os.path.exists(p)), None)
    if ffmpeg:
        options["ffmpeg_location"] = ffmpeg
    if as_m4a and ffmpeg:
        options["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "128"}]
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        raise ImportFailed(f"The sound of the video could not be downloaded: {str(e).splitlines()[0][:200]}") from e
    files = [f for f in os.listdir(folder) if f.startswith("audio.")]
    if not files:
        raise ImportFailed("The sound of the video could not be downloaded.")
    return os.path.join(folder, files[0])


def captions_only(url, language):
    "The video's captions as an Imported, or None when it has none (nothing is downloaded)."
    vid = video_id(url)
    text, note = _captions(vid, (language or "").split("-")[0].lower() or None)
    return Imported(short_title(video_title(url, vid), url), text, url, note) if text else None


def from_youtube(url, language, progress=None, keep_audio=False, check=None, transcribe=None):
    """
    `transcribe(audio_path, language)` turns sound into text (Whisper on this Mac); when it is None a video without captions fails.
    With keep_audio the downloaded sound stays (its path is in the result and the caller must move or delete it).
    """
    say = progress or log.info
    vid = video_id(url)
    title = short_title(video_title(url, vid), url)
    code = (language or "").split("-")[0].lower() or None

    say("Looking for the captions...")
    text, note = _captions(vid, code)
    if not text:
        log.info("No captions: %s", note)
        if transcribe is None:
            raise ImportFailed(f"{note or 'The video has no captions.'} Download the Whisper model in Settings to transcribe it on this Mac.")
    if text and not keep_audio:
        return Imported(title, text, url, note)

    folder = tempfile.mkdtemp(prefix="ocarina-import-")
    try:
        say("Downloading the sound of the video...")
        audio = _download_audio(url, folder, check, as_m4a=keep_audio)
        if check:
            check()
        if not text:
            say("Transcribing on this Mac (this can take a few minutes)...")
            text = clean_paragraphs(transcribe(audio, code))
            note = "Transcribed on this Mac by Whisper, so it can have mistakes. Check it before saving."
            if not text:
                raise ImportFailed("Nothing was heard in the video.")
        result = Imported(title, text, url, note)
        if keep_audio:
            kept = os.path.join(tempfile.gettempdir(), f"ocarina-import-{vid}{os.path.splitext(audio)[1]}")
            shutil.move(audio, kept)
            result.audio_path = kept
        return result
    finally:
        shutil.rmtree(folder, ignore_errors=True)
