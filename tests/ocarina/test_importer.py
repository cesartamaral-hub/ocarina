import pytest

from ocarina import importer

PAGE = """<html><head><title>Een   titel</title></head><body>
<nav>Menu Home Contact</nav>
<article><h1>Een titel</h1>
<p>Dit is de eerste alinea van het artikel, met genoeg woorden om als tekst te tellen.</p>
<p>Dit is de tweede alinea. Er staat nog meer in, zodat de pagina echt een artikel lijkt.</p></article>
<footer>Copyright</footer></body></html>"""


def test_check_url():
    assert importer.check_url("example.com/a") == "https://example.com/a"
    assert importer.check_url(" http://x.org ") == "http://x.org"
    for bad in ["", "not a url", "ftp://x.org", "javascript:alert(1)"]:
        with pytest.raises(importer.ImportFailed):
            importer.check_url(bad)


def test_is_youtube():
    assert importer.is_youtube("https://www.youtube.com/watch?v=abc")
    assert importer.is_youtube("https://youtu.be/abc")
    assert not importer.is_youtube("https://example.com/youtube.com")


def test_clean_paragraphs_joins_wrapped_lines():
    assert importer.clean_paragraphs("one\ntwo  three\n\n\nfour\n") == "one two three\n\nfour"
    assert importer.clean_paragraphs("one\ntwo\n", lines_are_paragraphs=True) == "one\n\ntwo"


def test_sanitize_title():
    assert importer.sanitize_title('A/B: "c"?  d.') == "AB c d"
    assert importer.sanitize_title("///") == "material"
    assert len(importer.sanitize_title("x" * 500)) == importer.MAX_TITLE


def test_from_web(monkeypatch):
    monkeypatch.setattr(importer, "_fetch", lambda url: PAGE.encode())
    got = importer.import_url("https://example.com/a", "nl")
    assert got.source_uri == "https://example.com/a"
    assert "eerste alinea" in got.text and "tweede alinea" in got.text
    assert "Copyright" not in got.text and "Menu" not in got.text
    assert "\n\n" in got.text


def test_from_web_falls_back_to_paragraphs(monkeypatch):
    monkeypatch.setattr(importer, "_fetch", lambda url: b"<html><title>T</title><body><p>Kort.</p></body></html>")
    monkeypatch.setattr("trafilatura.extract", lambda *a, **k: None)
    got = importer.import_url("https://example.com/a")
    assert got.text == "Kort." and got.note


def test_from_web_without_text(monkeypatch):
    monkeypatch.setattr(importer, "_fetch", lambda url: b"<html><body><div></div></body></html>")
    with pytest.raises(importer.ImportFailed):
        importer.import_url("https://example.com/a")


def test_fetch_errors(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(requests, "get", boom)
    with pytest.raises(importer.ImportFailed, match="did not answer"):
        importer.import_url("https://example.com")


def test_save_text_file(tmp_path):
    path = importer.save_text_file(importer.Imported("A: b", "text", "u"), str(tmp_path))
    assert path.endswith("A b.txt") and open(path, encoding="utf-8").read() == "text\n"
