"""
Adding a book: extracting text from files and web pages, and saving.
"""

import io
import os

import requests

from lute.db import db
from lute.models.repositories import BookRepository
from tests.conftest import _get_test_language

EXTRACT = "/ocarina/api/books/extract"
BOOKS = "/ocarina/api/books"


def _upload(client, name, data):
    return client.post(
        EXTRACT, data={"file": (io.BytesIO(data), name)}, content_type="multipart/form-data"
    )


def test_languages_are_listed(app_context, client):
    "The import form needs the language choices."
    _get_test_language("Dutch")
    names = [lang["name"] for lang in client.get("/ocarina/api/languages").json]
    assert "Dutch" in names


def test_extract_text_file_uses_filename_as_title(client):
    "A .txt file gives its text and a title from the file name."
    r = _upload(client, "Mijn verhaal.txt", "Hallo wereld.".encode("utf-8"))
    assert r.status_code == 200
    assert r.json["title"] == "Mijn verhaal" and r.json["text"] == "Hallo wereld."
    assert r.json["note"] is None


def test_extract_subtitles_keeps_only_the_spoken_text(client):
    "An .srt file loses its numbers and times."
    srt = "1\n00:00:01,000 --> 00:00:02,000\nGoedemorgen.\n\n2\n00:00:03,000 --> 00:00:04,000\nHoe gaat het?\n"
    r = _upload(client, "show.srt", srt.encode("utf-8"))
    assert r.json["text"] == "Goedemorgen.\nHoe gaat het?"


def test_extract_refuses_unknown_empty_and_non_utf8_files(client):
    "Bad files are a 400 with a readable message."
    assert "Unknown file extension" in _upload(client, "x.docx", b"x").json["error"]
    assert "empty" in _upload(client, "x.txt", b"  \n").json["error"]
    assert "utf-8" in _upload(client, "x.txt", b"\xff\xfe\x00bad").json["error"]
    assert client.post(EXTRACT, json={"url": "file:///etc/passwd"}).status_code == 400


def test_extract_from_web_page(client, monkeypatch):
    "A web page gives its headings and paragraphs, and its title."
    html = b"<html><title>Nieuws</title><body><h1>Kop</h1><p>Eerste alinea.</p><p>Tweede.</p></body></html>"

    class Response:
        content = html

        def raise_for_status(self):
            pass

    monkeypatch.setattr(requests, "get", lambda *a, **k: Response())
    r = client.post(EXTRACT, json={"url": "https://example.com/a"})
    assert r.json == {
        "title": "Nieuws",
        "text": "Kop\n\nEerste alinea.\n\nTweede.",
        "sourceUri": "https://example.com/a",
        "note": None,
    }


def test_extract_reports_unreachable_page(client, monkeypatch):
    "A failed download is an error message, not a crash."

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("no network")

    monkeypatch.setattr(requests, "get", boom)
    r = client.post(EXTRACT, json={"url": "https://example.com/a"})
    assert r.status_code == 400 and "no network" in r.json["error"]


def _save(client, **fields):
    data = {"title": "Nieuw boek", "text": "Dit is een zin.", **fields}
    return client.post(BOOKS, data=data, content_type="multipart/form-data")


def test_save_book_then_it_is_readable(app, client):
    "The saved book has its pages parsed and appears in the list."
    with app.app_context():
        lang_id = _get_test_language("Dutch").id
    r = _save(client, languageId=str(lang_id), sourceUri="https://example.com")
    assert r.status_code == 201
    with app.app_context():
        book = BookRepository(db.session).find(r.json["id"])
        assert book.title == "Nieuw boek" and book.language.name == "Dutch"
        assert book.page_count == 1 and book.source_uri == "https://example.com"
    assert "Nieuw boek" in [b["title"] for b in client.get(BOOKS).json]


def test_save_book_with_own_audio(app, client):
    "An uploaded audio file is attached as the book's own audio; other formats are refused."
    with app.app_context():
        lang_id = _get_test_language("Dutch").id
    good = _save(client, title="Met audio", languageId=str(lang_id), audio=(io.BytesIO(b"ID3x"), "a.mp3"))
    assert good.status_code == 201
    with app.app_context():
        assert BookRepository(db.session).find(good.json["id"]).audio_filename.endswith(".mp3")
    bad = _save(client, title="Slecht", languageId=str(lang_id), audio=(io.BytesIO(b"x"), "a.exe"))
    assert bad.status_code == 400


def test_save_book_validation(app, client):
    "Missing language, title or text, unknown language and duplicate titles are refused."
    with app.app_context():
        lang_id = _get_test_language("Dutch").id
    ok = str(lang_id)
    assert _save(client).status_code == 400
    assert _save(client, languageId="99999").json["error"] == "Unknown language"
    assert _save(client, languageId=ok, title=" ").status_code == 400
    assert _save(client, languageId=ok, text=" ").status_code == 400
    assert _save(client, languageId=ok, title="x" * 256).status_code == 400
    assert _save(client, languageId=ok, title="Dubbel").status_code == 201
    assert _save(client, languageId=ok, title="Dubbel").status_code == 409


def test_extract_pdf_runs_the_pdf_reader(client):
    "A PDF goes through the PDF reader (a blank one has no text, so it is reported as empty)."
    from pypdf import PdfWriter  # pylint: disable=import-outside-toplevel

    out = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(out)
    r = _upload(client, "blank.pdf", out.getvalue())
    assert r.status_code == 400 and "empty" in r.json["error"]


def test_upload_audio_to_an_existing_book(app, client):
    "Own audio is attached; an earlier recording of the user is kept when it is replaced."
    from tests.ocarina.helpers import make_dutch_book  # pylint: disable=import-outside-toplevel

    with app.app_context():
        book_id = make_dutch_book("Upload").id
    url = f"/ocarina/api/books/{book_id}/audio/upload"
    send = lambda name: client.post(url, data={"audio": (io.BytesIO(b"ID3x"), name)}, content_type="multipart/form-data")  # noqa: E731
    first = send("mijn.mp3")
    assert first.status_code == 201
    with app.app_context():
        assert BookRepository(db.session).find(book_id).audio_filename == first.json["audio_filename"]
    assert send("x.exe").status_code == 400
    assert client.post(url, data={}, content_type="multipart/form-data").status_code == 400
    assert client.post("/ocarina/api/books/99999/audio/upload", data={}).status_code == 404
    second = send("tweede.mp3")  # a user's own recording is kept when replaced
    audio_dir = app.env_config.useraudiopath
    assert os.path.exists(os.path.join(audio_dir, first.json["audio_filename"]))
    assert second.json["audio_filename"] != first.json["audio_filename"]


def test_upload_audio_keeps_generated_audio_as_another_version(app, client):
    "A file made by Ocarina (with timings) stays when the user uploads their own; both are versions."
    from tests.ocarina.helpers import make_dutch_book, wait_for_job  # pylint: disable=import-outside-toplevel

    app.config["OCARINA_TTS_ENGINE"] = "fake"
    with app.app_context():
        book_id = make_dutch_book("Generated").id
    job = wait_for_job(client, client.post(f"/ocarina/api/books/{book_id}/audio", json={}).json["id"])
    generated = os.path.join(app.env_config.useraudiopath, job["audio_filename"])
    assert os.path.exists(generated) and os.path.exists(generated + ".sentences.json")
    r = client.post(
        f"/ocarina/api/books/{book_id}/audio/upload",
        data={"audio": (io.BytesIO(b"ID3x"), "mine.mp3")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 201
    assert os.path.exists(generated) and os.path.exists(generated + ".sentences.json")
    kinds = [(v["kind"], v["selected"]) for v in client.get(f"/ocarina/api/books/{book_id}/audio/versions").json]
    assert kinds == [("generated", False), ("own", True)]
