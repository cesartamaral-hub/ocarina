import os
from types import SimpleNamespace as NS

import pytest

from ocarina import importer, youtube


def test_video_id():
    for url in [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5s",
        "https://youtu.be/dQw4w9WgXcQ?si=x",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
    ]:
        assert youtube.video_id(url) == "dQw4w9WgXcQ"
    with pytest.raises(importer.ImportFailed):
        youtube.video_id("https://www.youtube.com/")
    with pytest.raises(importer.ImportFailed):
        youtube.video_id("https://www.youtube.com/watch?v=short")


def test_build_text_drops_noise_cuts_paragraphs_and_notes_where_words_are_said():
    lines = ["[Music]", "♪ la la ♪", "Hallo allemaal."] + ["en dan gaan we verder met woorden"] * 40
    text, anchors = youtube.build_text([(i * 2.0, line) for i, line in enumerate(lines)], generated=True)
    assert anchors[0] == [0, 2.0] and anchors[1] == [2, 4.0] and anchors[-1][0] == sum(len(p.split()) for p in text.split("\n\n"))  # "la la" starts at the second line; the noise line has no words
    assert "[Music]" not in text and "♪" not in text
    assert text.startswith("la la Hallo allemaal.")
    assert "\n\n" in text and all(len(p) < 700 for p in text.split("\n\n"))


def track(code, generated, translatable=False, text="x"):
    t = NS(
        language_code=code,
        language=code,
        is_generated=generated,
        is_translatable=translatable,
        translation_languages=[NS(language_code="nl")] if translatable else [],
    )
    t.fetch = lambda: [NS(text=f"{text} {code} {generated}.", start=1.5)]
    t.translate = lambda lang: track(lang, False, text="vertaald")
    return t


def test_prefers_written_then_automatic_then_translation():
    text, note, _ = youtube._pick_and_fetch([track("nl", True), track("nl", False)], "nl")
    assert "nl False" in text and note is None
    text, note, _ = youtube._pick_and_fetch([track("nl", True), track("en", False)], "nl")
    assert "nl True" in text and "automatically" in note
    text, note, _ = youtube._pick_and_fetch([track("en", False, translatable=True)], "nl")
    assert "vertaald" in text and "translation" in note
    assert youtube._pick_and_fetch([track("en", False)], "nl")[0] is None
    assert "en False" in youtube._pick_and_fetch([track("en", True), track("en", False)], None)[0]  # a language Ocarina has no code for: any captions


def fake(monkeypatch, captions):
    monkeypatch.setattr(youtube, "video_title", lambda url, vid: "Een video")
    monkeypatch.setattr(youtube, "_captions", lambda vid, lang: captions)


URL = "https://youtu.be/dQw4w9WgXcQ"


def test_from_youtube_uses_captions(monkeypatch):
    fake(monkeypatch, ("Tekst.", "note", [[0, 1.0]]))
    got = importer.import_url(URL, "nl")
    assert (got.title, got.text, got.note, got.source_uri) == ("Een video", "Tekst.", "note", URL)


def test_without_captions_and_without_whisper(monkeypatch):
    fake(monkeypatch, (None, "The video has no captions.", None))
    with pytest.raises(importer.ImportFailed, match="Whisper"):
        importer.import_url(URL, "nl")


def test_whisper_fallback_removes_the_audio(monkeypatch):
    fake(monkeypatch, (None, "no captions", None))
    seen = {}

    def download(url, folder, check=None, as_m4a=False):
        path = os.path.join(folder, "audio.m4a")
        open(path, "w").close()
        seen["folder"] = folder
        return path

    monkeypatch.setattr(youtube, "_download_audio", download)
    got = importer.import_url(URL, "nl", transcribe=lambda path, lang: (f"Gehoord in {lang}. Tweede regel", [(0.0, f"Gehoord in {lang}."), (2.5, "Tweede regel")]))
    assert got.text == "Gehoord in nl. Tweede regel" and "Whisper" in got.note and got.audio_path is None
    assert got.video_id == "dQw4w9WgXcQ" and got.anchors == [[0, 0.0], [3, 2.5], [5, 5.5]]
    assert not os.path.exists(seen["folder"])


def test_keep_audio_uses_the_captions_and_keeps_the_file(monkeypatch, tmp_path):
    fake(monkeypatch, ("Van de captions.", None, [[0, 1.0]]))
    monkeypatch.setattr(youtube.tempfile, "gettempdir", lambda: str(tmp_path))

    def download(url, folder, check=None, as_m4a=False):
        path = os.path.join(folder, "audio.m4a")
        open(path, "w").close()
        return path

    monkeypatch.setattr(youtube, "_download_audio", download)
    got = importer.import_url(URL, "nl", keep_audio=True)
    assert got.text == "Van de captions."
    assert os.path.exists(got.audio_path) and got.audio_path.endswith(".m4a")


def test_automatic_captions_give_way_to_whisper_and_return_when_it_fails(monkeypatch):
    fake(monkeypatch, ("zonder leestekens", youtube.AUTOMATIC, [[0, 1.0]]))
    monkeypatch.setattr(youtube, "_download_audio", lambda url, folder, check=None, as_m4a=False: open(os.path.join(folder, "a.m4a"), "w").close() or os.path.join(folder, "a.m4a"))
    got = importer.import_url(URL, "nl", transcribe=lambda p, l: ("Met leestekens.", [(0.0, "Met leestekens.")]))
    assert got.text == "Met leestekens." and "Whisper" in got.note

    def broken(path, lang):
        raise RuntimeError("model failed")

    got = importer.import_url(URL, "nl", transcribe=broken)
    assert got.text == "zonder leestekens" and got.note == youtube.AUTOMATIC
    assert importer.import_url(URL, "nl").text == "zonder leestekens"  # no Whisper at all: the captions
