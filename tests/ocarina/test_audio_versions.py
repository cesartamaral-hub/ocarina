"""
Audio versions: your own recordings and generated audio kept side by side.
"""

import io
import os

from lute.db import db
from lute.models.repositories import BookRepository
from tests.ocarina.helpers import make_dutch_book, wait_for_job

BOOKS = "/ocarina/api/books"


def _versions(client, book_id):
    return client.get(f"{BOOKS}/{book_id}/audio/versions").json


def _upload(client, book_id, name="opname.mp3"):
    return client.post(
        f"{BOOKS}/{book_id}/audio/upload", data={"audio": (io.BytesIO(b"ID3x"), name)}, content_type="multipart/form-data"
    )


def _generate(client, book_id, **body):
    return wait_for_job(client, client.post(f"{BOOKS}/{book_id}/audio", json=body).json["id"])


def _book(app, name):
    with app.app_context():
        return make_dutch_book(name).id


def test_existing_audio_becomes_the_first_version(app, client):
    "A book that had one audio file before versions existed shows it as 'Original', selected."
    with app.app_context():
        b = make_dutch_book("Oud")
        b.audio_filename = "old_recording.mp3"
        db.session.add(b)
        db.session.commit()
        book_id = b.id
    versions = _versions(client, book_id)
    assert [(v["label"], v["kind"], v["selected"]) for v in versions] == [("Original", "own", True)]
    assert len(_versions(client, book_id)) == 1  # looking again does not add it twice


def test_original_is_kept_when_generating_and_you_can_switch_back(app, client):
    "Generate adds a version and selects it; the original stays and can be selected again."
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    book_id = _book(app, "Beide")
    first = _upload(client, book_id, "hoorspel.mp3")
    assert first.status_code == 201
    assert _generate(client, book_id)["state"] == "done"
    own, made = _versions(client, book_id)
    assert (own["label"], own["kind"], own["selected"]) == ("hoorspel", "own", False)
    assert made["kind"] == "generated" and made["selected"] is True and made["hasTimings"] is True
    audio_dir = app.env_config.useraudiopath
    assert os.path.exists(os.path.join(audio_dir, first.json["audio_filename"]))
    assert client.put(f"{BOOKS}/{book_id}/audio/versions/{own['id']}/select").status_code == 200
    with app.app_context():
        assert BookRepository(db.session).find(book_id).audio_filename == first.json["audio_filename"]
    assert [v["selected"] for v in _versions(client, book_id)] == [True, False]
    assert client.get(f"{BOOKS}/{book_id}/sentences").json["hasTimings"] is False  # an original has no timings
    client.put(f"{BOOKS}/{book_id}/audio/versions/{made['id']}/select")
    assert client.get(f"{BOOKS}/{book_id}/sentences").json["hasTimings"] is True


def test_same_settings_replace_that_version_but_other_settings_add_one(app, client):
    "Generating again with the same model, voice and pause replaces that version; a different pause adds one."
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    book_id = _book(app, "Dubbel")
    _generate(client, book_id, pause=0.5)
    first = _versions(client, book_id)[0]
    audio_dir = app.env_config.useraudiopath
    with app.app_context():
        first_file = BookRepository(db.session).find(book_id).audio_filename
    _generate(client, book_id, pause=0.5)
    again = _versions(client, book_id)
    assert len(again) == 1 and again[0]["id"] != first["id"] and again[0]["selected"] is True
    assert not os.path.exists(os.path.join(audio_dir, first_file))  # the replaced file is gone
    _generate(client, book_id, pause=1.0)
    labels = [v["label"] for v in _versions(client, book_id)]
    assert len(labels) == 2 and labels[1].endswith("pause 1.0 s")


def test_rename_and_delete_versions(app, client):
    "Rename changes the label; deleting a generated version removes its file, an own one only its entry."
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    book_id = _book(app, "Beheer")
    own_file = _upload(client, book_id).json["audio_filename"]
    _generate(client, book_id)
    own, made = _versions(client, book_id)
    audio_dir = app.env_config.useraudiopath
    assert client.patch(f"{BOOKS}/{book_id}/audio/versions/{own['id']}", json={"label": "Mijn opname"}).json[0]["label"] == "Mijn opname"
    assert client.patch(f"{BOOKS}/{book_id}/audio/versions/{own['id']}", json={"label": " "}).status_code == 400
    with app.app_context():
        made_file = BookRepository(db.session).find(book_id).audio_filename
    removed = client.delete(f"{BOOKS}/{book_id}/audio/versions/{made['id']}")
    assert removed.status_code == 200
    assert not os.path.exists(os.path.join(audio_dir, made_file)) and not os.path.exists(os.path.join(audio_dir, made_file + ".sentences.json"))
    left = removed.json["versions"]
    assert len(left) == 1 and left[0]["selected"] is True  # the selected one was removed, so the remaining one is selected
    assert client.delete(f"{BOOKS}/{book_id}/audio/versions/{own['id']}").status_code == 200
    assert os.path.exists(os.path.join(audio_dir, own_file))  # your recording stays on disk
    with app.app_context():
        assert BookRepository(db.session).find(book_id).audio_filename is None
    assert _versions(client, book_id) == []
    assert client.delete(f"{BOOKS}/{book_id}/audio/versions/{own['id']}").status_code == 404


def test_unknown_book_or_version_is_a_404(app, client):
    "Nothing leaks across books."
    one, two = _book(app, "Een"), _book(app, "Twee")
    _upload(client, one)
    version = _versions(client, one)[0]["id"]
    assert client.get(f"{BOOKS}/99999/audio/versions").status_code == 404
    assert client.put(f"{BOOKS}/{two}/audio/versions/{version}/select").status_code == 404
    assert client.patch(f"{BOOKS}/{two}/audio/versions/{version}", json={"label": "x"}).status_code == 404
    assert client.delete(f"{BOOKS}/{two}/audio/versions/{version}").status_code == 404


def test_deleting_a_book_removes_all_its_generated_versions(app, client):
    "Every generated file goes with the book, your own recording stays."
    app.config["OCARINA_TTS_ENGINE"] = "fake"
    book_id = _book(app, "Weg")
    own_file = _upload(client, book_id).json["audio_filename"]
    audio_dir = app.env_config.useraudiopath
    before = set(os.listdir(audio_dir))  # the folder is shared with other tests: look only at what this test adds
    _generate(client, book_id, pause=0.5)
    _generate(client, book_id, pause=1.0)
    made = [f for f in set(os.listdir(audio_dir)) - before if f.endswith(".mp3")]
    assert len(made) == 2
    assert client.delete(f"{BOOKS}/{book_id}").status_code == 200
    assert os.path.exists(os.path.join(audio_dir, own_file))
    for name in made:
        assert not os.path.exists(os.path.join(audio_dir, name))
        assert not os.path.exists(os.path.join(audio_dir, name + ".sentences.json"))


def test_a_book_created_with_audio_gets_it_as_its_first_version(app, client):
    "Audio sent with a new book shows as Original."
    from tests.conftest import _get_test_language  # pylint: disable=import-outside-toplevel

    with app.app_context():
        lang_id = _get_test_language("Dutch").id
    made = client.post(
        BOOKS,
        data={"title": "Met opname", "languageId": str(lang_id), "text": "Hallo wereld.", "audio": (io.BytesIO(b"ID3x"), "x.mp3")},
        content_type="multipart/form-data",
    )
    assert made.status_code == 201
    assert [v["label"] for v in _versions(client, made.json["id"])] == ["Original"]
