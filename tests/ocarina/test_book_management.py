"""
Editing, archiving and deleting books.
"""

import os

from lute.db import db
from lute.models.repositories import BookRepository
from tests.ocarina.helpers import make_dutch_book, wait_for_job

BOOKS = "/ocarina/api/books"


def test_list_has_progress_tags_and_hides_archived(app, client):
    "The list shows the page you are on; archived books only show with ?archived=true."
    with app.app_context():
        book_id = make_dutch_book("Voortgang").id
    row = next(b for b in client.get(BOOKS).json if b["id"] == book_id)
    assert row["currentPage"] == 1 and row["pages"] == 2 and row["tags"] == [] and row["sourceUri"] == ""
    assert client.patch(f"{BOOKS}/{book_id}", json={"archived": True}).json["archived"] is True
    assert book_id not in [b["id"] for b in client.get(BOOKS).json]
    assert book_id in [b["id"] for b in client.get(f"{BOOKS}?archived=true").json]
    client.patch(f"{BOOKS}/{book_id}", json={"archived": False})
    assert book_id in [b["id"] for b in client.get(BOOKS).json]


def test_change_title_source_and_tags(app, client):
    "Title, source and tags can be changed; tags are tidied and shared between books."
    with app.app_context():
        one = make_dutch_book("Eerste").id
        two = make_dutch_book("Tweede").id
    r = client.patch(f"{BOOKS}/{one}", json={"title": " Nieuw ", "sourceUri": "https://x.nl", "tags": ["b", "a", "a", " "]})
    assert r.status_code == 200
    assert (r.json["title"], r.json["sourceUri"], r.json["tags"]) == ("Nieuw", "https://x.nl", ["a", "b"])
    assert client.patch(f"{BOOKS}/{two}", json={"tags": ["a"]}).json["tags"] == ["a"]
    assert client.patch(f"{BOOKS}/{one}", json={"tags": [], "sourceUri": ""}).json["tags"] == []


def test_change_book_validation(app, client):
    "Bad titles, long tags, duplicates and unknown books are refused."
    with app.app_context():
        one = make_dutch_book("Een").id
        make_dutch_book("Twee")
    assert client.patch(f"{BOOKS}/{one}", json={"title": " "}).status_code == 400
    assert client.patch(f"{BOOKS}/{one}", json={"title": "x" * 201}).status_code == 400
    assert client.patch(f"{BOOKS}/{one}", json={"tags": ["t" * 21]}).status_code == 400
    assert client.patch(f"{BOOKS}/{one}", json={"title": "Twee"}).status_code == 409
    assert client.patch(f"{BOOKS}/{one}", json={"title": "Een"}).status_code == 200  # its own title is fine
    assert client.patch(f"{BOOKS}/99999", json={}).status_code == 404


def test_delete_removes_generated_audio_but_keeps_own_recordings(app, client):
    "Deleting a book removes audio Ocarina made for it, not a recording of the user's."
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    with app.app_context():
        generated_id = make_dutch_book("Gegenereerd").id
        own_id = make_dutch_book("Eigen").id
    job = wait_for_job(client, client.post(f"{BOOKS}/{generated_id}/audio", json={}).json["id"])
    audio_dir = app.env_config.useraudiopath
    generated = os.path.join(audio_dir, job["audio_filename"])
    own = os.path.join(audio_dir, "own.mp3")
    with open(own, "wb") as f:
        f.write(b"ID3")
    with app.app_context():
        book = BookRepository(db.session).find(own_id)
        book.audio_filename = "own.mp3"
        db.session.commit()
    assert client.delete(f"{BOOKS}/{generated_id}").json == {"deleted": generated_id}
    assert client.delete(f"{BOOKS}/{own_id}").status_code == 200
    assert not os.path.exists(generated) and not os.path.exists(generated + ".sentences.json")
    assert os.path.exists(own)
    ids = [b["id"] for b in client.get(BOOKS).json]
    assert generated_id not in ids and own_id not in ids
    assert client.delete(f"{BOOKS}/{own_id}").status_code == 404


def test_one_book_can_be_fetched_with_its_current_page(app, client):
    with app.app_context():
        book_id = make_dutch_book("Eén boek").id
    r = client.get(f"{BOOKS}/{book_id}")
    assert r.status_code == 200 and r.json["id"] == book_id and r.json["currentPage"] == 1 and r.json["pages"] == 2
    assert client.get(f"{BOOKS}/99999").status_code == 404
