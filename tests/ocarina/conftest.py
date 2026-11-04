import pytest

from ocarina import book_index


@pytest.fixture(autouse=True)
def _no_background_indexing_left_over():
    "A book list starts indexing in the background; wait for it before the next test resets the database."
    yield
    book_index.wait_until_idle()
