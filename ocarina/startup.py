"""
Library start-up shared by the desktop app and the development server.
"""

from lute.app_factory import data_initialization
from sqlalchemy import text as sql

from lute.db import db
from lute.models.book import Book
import os
import tempfile
import threading

from ocarina import audio_versions, book_translation, term_context
from ocarina.dictionaries import languages as dictionary_languages, registry as dictionary_registry, setup as dictionary_setup, wikdict
from lute.db.demo import Service as DemoService


def prepare_library(app):
    """
    Finish setting up the database. A new library starts empty: Lute would fill it with sample
    books in every language it knows, but Ocarina shows a first-run screen instead, where you pick
    the languages you study.
    """
    with app.app_context():
        DemoService(db.session).remove_load_demo_flag()
        data_initialization(db.session, lambda s: None)
        book_translation.clean_stored()
        # Audio that books had before versions existed becomes each book's first version.
        for book in db.session.query(Book).filter(Book.audio_filename.isnot(None)).all():
            audio_versions.sync(book, app.env_config.useraudiopath)
        names = [n for (n,) in db.session.execute(sql("select LgName from languages"))]
    term_context.backfill_in_background(app)  # a sentence for each word saved before they were kept
    _make_builtin_dictionaries()
    dictionary_setup.ensure_defaults_in_background(app, names)  # a language of the library with no dictionary gets its small one


def _make_builtin_dictionaries():
    "Running from the source, the dictionaries that come with the app are not there until they are made (the app bundle has them): do it in the background."
    missing = [c for c in dictionary_languages.bundled() if not os.path.exists(os.path.join(dictionary_registry.BUILTIN_DIR, f"wikdict-{c}-en.sqlite"))]
    if not missing:
        return

    def work():
        try:
            wikdict.build_all(dictionary_registry.BUILTIN_DIR, os.path.join(tempfile.gettempdir(), "ocarina-wikdict-cache"), say=lambda _: None)
        except Exception:  # pylint: disable=broad-exception-caught  # no connection: they are made the next time
            pass

    threading.Thread(target=work, name="builtin-dictionaries", daemon=True).start()
