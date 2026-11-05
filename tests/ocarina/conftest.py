import os

os.environ.setdefault("OCARINA_NO_MODEL_MIGRATION", "1")  # tests never copy the real models

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


@pytest.fixture(autouse=True)
def _no_builtin_dictionaries(request, monkeypatch, tmp_path_factory):
    "The dictionaries that come with the app are not in the tests (a lookup would find them and never reach the Wiktionary code); mark with `packs` to use them."
    if request.node.get_closest_marker("packs") is None:
        monkeypatch.setattr("ocarina.dictionaries.registry.BUILTIN_DIR", str(tmp_path_factory.mktemp("no-builtin")))


@pytest.fixture(autouse=True)
def _no_dictionary_downloads(request, monkeypatch):
    "Adding a language starts the download of its small dictionary; the tests must not go to the internet (mark with `dictionary_setup` to test it)."
    if request.node.get_closest_marker("dictionary_setup") is None:
        monkeypatch.setattr("ocarina.dictionaries.setup.ensure_default", lambda datapath, name: None)
