"""
Shared test helpers for Ocarina's tests.
"""

import time

from lute.db import db
from lute.models.book import Book, Text
from tests.conftest import _get_test_language


def make_dutch_book(title="Carla"):
    "A two-page Dutch book saved in the test database; returns the Book."
    book = Book(title, _get_test_language("Dutch"))
    book.texts = []
    Text(book, "Hallo! Mijn naam is Carla.\n\nIk woon in Nederland.", 1)
    Text(book, "Elke ochtend sta ik op.", 2)
    db.session.add(book)
    db.session.commit()
    return book


def wait_for_job(client, job_id, seconds=20):
    "Poll a job until it is no longer running; returns its final state."
    end = time.time() + seconds
    while time.time() < end:
        job = client.get(f"/ocarina/api/jobs/{job_id}").json
        if job["state"] not in ("queued", "running"):
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish")
