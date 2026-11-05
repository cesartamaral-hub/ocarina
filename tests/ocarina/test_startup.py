"""
Starting the app: what prepare_library does must not fail, or the app does not open (it once did, in a way no other test saw).
"""

from ocarina import startup, term_context
from ocarina.dictionaries import setup
from tests.conftest import _get_test_language


def test_the_library_is_prepared_and_the_background_jobs_are_started(app, monkeypatch):
    started = {}
    monkeypatch.setattr(term_context, "backfill_in_background", lambda a: started.setdefault("sentences", True))
    monkeypatch.setattr(startup, "_make_builtin_dictionaries", lambda: started.setdefault("builtin", True))
    monkeypatch.setattr(setup, "ensure_defaults_in_background", lambda a, names: started.setdefault("defaults", list(names)))
    with app.app_context():
        _get_test_language("Dutch")
    startup.prepare_library(app)
    assert started["sentences"] and started["builtin"] and "Dutch" in started["defaults"]
