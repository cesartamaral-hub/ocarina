import pytest

from ocarina import book_index, term_context


@pytest.fixture(autouse=True)
def _no_background_indexing_left_over():
    "A book list starts indexing in the background; wait for it before the next test resets the database."
    yield
    book_index.wait_until_idle()
    term_context.wait_until_idle()


@pytest.fixture(autouse=True)
def _no_automatic_sync(request, monkeypatch):
    "A recording added to a book is synced at once; tests that only add audio should not start that job (mark with `autosync` to have it)."
    if request.node.get_closest_marker("autosync") is None:
        monkeypatch.setattr("ocarina.api.audio_versions.sync_new_audio", lambda book, version_id: None)
