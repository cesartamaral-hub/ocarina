"""
The video a book was made from: sentence start times from where the words are said, saved with the book.
"""

from ocarina import video
from tests.conftest import _get_test_language

BOOKS = "/ocarina/api/books"


def test_starts_follow_the_anchors():
    sentences = [{"text": "een twee drie"}, {"text": "vier vijf"}, {"text": "zes"}]
    anchors = [[0, 10.0], [3, 20.0], [5, 30.0], [6, 33.0]]  # words 0-2 from 10 s, 3-4 from 20 s, 5 from 30 s, the end
    assert video.starts_for(sentences, anchors) == [10.0, 20.0, 30.0]


def test_starts_are_found_between_anchors():
    sentences = [{"text": "a b"}, {"text": "c d"}, {"text": "e f"}]
    assert video.starts_for(sentences, [[0, 0.0], [2, 4.0], [4, 8.0], [6, 12.0]]) == [0.0, 4.0, 8.0]


def test_starts_cope_with_a_text_that_has_a_few_words_more_or_less():
    sentences = [{"text": "a b c d"}, {"text": "e f g h i j"}]  # 10 words; the video said 8
    starts = video.starts_for(sentences, [[0, 0.0], [4, 8.0], [8, 12.0]])
    assert starts[0] == 0.0 and 0 < starts[1] < 12


def test_nothing_to_follow_without_anchors():
    assert video.starts_for([{"text": "a"}], []) == []
    assert video.starts_for([], [[0, 1.0]]) == []


def _save(client, **fields):
    with client.application.app_context():
        lang_id = _get_test_language("Dutch").id
    data = {"title": "Met video", "text": "Dit is een zin. Dit is er nog een.", "languageId": str(lang_id), **fields}
    return client.post(BOOKS, data=data, content_type="multipart/form-data")


def test_a_saved_video_gives_the_sentences_their_start_times(client):
    r = _save(client, videoId="dQw4w9WgXcQ", videoAnchors="[[0, 5.0], [4, 12.0], [8, 16.0]]")
    assert r.status_code == 201
    got = client.get(f"{BOOKS}/{r.json['id']}/sentences").json
    assert got["video"] == {"videoId": "dQw4w9WgXcQ"} and got["hasTimings"]
    starts = [s["start"] for s in got["sentences"]]
    assert starts[0] == 5.0 and starts[1] > starts[0]
    assert client.delete(f"{BOOKS}/{r.json['id']}").status_code == 200


def test_a_book_without_a_video_has_none(client):
    r = _save(client, title="Zonder")
    got = client.get(f"{BOOKS}/{r.json['id']}/sentences").json
    assert "video" not in got and not got["hasTimings"]


def test_a_bad_video_id_is_ignored_but_the_book_is_saved(client):
    r = _save(client, title="Slecht id", videoId="../x", videoAnchors="[[0, 1]]")
    assert r.status_code == 201
    assert "video" not in client.get(f"{BOOKS}/{r.json['id']}/sentences").json
