"""
Text for a new study material from a web address.

    import_url(url, language)   -> Imported(title, text, source_uri, note)

A web page goes through trafilatura (the article without menus, ads and footers), with the paragraphs of Lute's own reader as the
fallback. Nothing is saved here: the add-material page shows the result for the user to check, then saves it as a book.
Also runnable on its own, to look at what a page gives:

    python -m ocarina.importer --url https://example.com/article --language nl [--save]

--save writes ./imports/<title>.txt.
"""

import argparse
import logging
import os
import re
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("ocarina.importer")

TIMEOUT = 15  # seconds, for the page
MAX_TITLE = 150
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh) Ocarina/1.0"}
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}


class ImportFailed(Exception):
    "Something the user can read: a bad address, a page that cannot be reached, a page without text."


@dataclass
class Imported:
    title: str
    text: str
    source_uri: str
    note: str | None = None
    automatic: bool = False  # captions YouTube made by itself (no punctuation)
    video_id: str | None = None
    anchors: list | None = None  # [[word number, seconds], ...]: where in the video the words of the text are said
    audio_path: str | None = None  # a video's sound, kept only when asked (see youtube.py)


def check_url(url):
    "The address with the scheme it needs, or ImportFailed."
    url = (url or "").strip()
    if url and "://" not in url and "." in url.split("/")[0]:
        url = "https://" + url
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.netloc or " " in url:
        raise ImportFailed("That does not look like a web address. It should start with http:// or https://")
    return url


def is_youtube(url):
    return (urlparse(url).hostname or "").lower() in YOUTUBE_HOSTS


def clean_paragraphs(text, lines_are_paragraphs=False):
    """
    Paragraphs separated by one blank line, each on one line. A text that wraps its lines (a subtitle file, a copied page) has the
    lines of a paragraph joined; one that has a paragraph per line (trafilatura) keeps them.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    blocks = re.split(r"\n\s*\n", text) if not lines_are_paragraphs else text.split("\n")
    paragraphs = []
    for block in blocks:
        joined = re.sub(r"\s+", " ", block.replace("\n", " ")).strip()
        if joined:
            paragraphs.append(joined)
    return "\n\n".join(paragraphs)


def sanitize_title(title, fallback="material"):
    "A title that is safe as a file name and short enough to read."
    title = re.sub(r"\s+", " ", title or "").strip()
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", title).strip(" .")
    return (name[:MAX_TITLE].rstrip() or fallback)


def short_title(title, url):
    title = re.sub(r"\s+", " ", title or "").strip() or url
    return title if len(title) <= MAX_TITLE else title[:MAX_TITLE].rstrip() + " ..."


def _fetch(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout as e:
        raise ImportFailed(f"The page did not answer within {TIMEOUT} seconds.") from e
    except requests.exceptions.HTTPError as e:
        raise ImportFailed(f"The page answered with an error ({e.response.status_code}).") from e
    except requests.exceptions.RequestException as e:
        raise ImportFailed("The page could not be reached. Check the address and your connection.") from e
    return response.content


def _soup_text(html):
    "The headings and paragraphs of a page, in order (what Lute's own import takes)."
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    parts = [el.get_text(" ", strip=True) for el in soup.find_all(["h1", "h2", "h3", "h4", "p"])]
    title = soup.find("title")
    return "\n".join(p for p in parts if p), (title.get_text() if title else "")


def from_web(url):
    "The article of a web page."
    import trafilatura  # pylint: disable=import-outside-toplevel  # slow to load, and only this path needs it

    log.info("Downloading the page...")
    html = _fetch(url)
    text, title, note = None, "", None
    try:
        text = trafilatura.extract(html, include_comments=False, include_tables=False, favor_recall=True, url=url)
        meta = trafilatura.extract_metadata(html, default_url=url)
        title = (meta.title if meta else "") or ""
    except Exception:  # pylint: disable=broad-exception-caught  # a page that trips it still has the fallback
        log.warning("trafilatura could not read the page", exc_info=True)
    if not text or not text.strip():
        log.info("Reading the page with the simpler extractor...")
        text, soup_title = _soup_text(html)
        title = title or soup_title
        note = "This page has no clear article, so everything on it was taken. Remove what you do not want."
    text = clean_paragraphs(text or "", lines_are_paragraphs=True)
    if not text:
        raise ImportFailed("No text was found on that page. It may need you to sign in, or build its text with scripts.")
    return Imported(short_title(title, url), text, url, note)


def import_url(url, language=None, progress=None, keep_audio=False, check=None, transcribe=None):
    """
    The text behind a web address or a YouTube link. `language` (a code such as "nl") picks the subtitles of a video; `progress`
    is called with a short message and `check()` raises to stop a long job. `transcribe(audio_path, language)` is the speech
    recognition for a video without captions.
    """
    url = check_url(url)
    if is_youtube(url):
        from ocarina import youtube  # pylint: disable=import-outside-toplevel

        return youtube.from_youtube(url, language, progress=progress, keep_audio=keep_audio, check=check, transcribe=transcribe)
    return from_web(url)


def save_text_file(imported, folder="imports"):
    "Write the text to <folder>/<title>.txt and return the path."
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, sanitize_title(imported.title) + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(imported.text + "\n")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Get the text of a web page or a YouTube video.")
    parser.add_argument("--url", required=True, help="a web page or a YouTube link")
    parser.add_argument("--language", default="nl", help="language code of the material, for subtitles (default: nl)")
    parser.add_argument("--save", action="store_true", help="write ./imports/<title>.txt instead of printing the text")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        got = import_url(args.url, args.language, progress=log.info)
    except ImportFailed as e:
        log.error("%s", e)
        return 1
    if got.note:
        log.warning("Note: %s", got.note)
    if args.save:
        log.info("Saved to %s", save_text_file(got))
    else:
        print(f"# {got.title}\n\n{got.text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
