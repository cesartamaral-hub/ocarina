"""
Library start-up shared by the desktop app and the development server.
"""

from lute.app_factory import data_initialization
from lute.db import db
from lute.models.book import Book
from ocarina import audio_versions, term_context
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
        # Audio that books had before versions existed becomes each book's first version.
        for book in db.session.query(Book).filter(Book.audio_filename.isnot(None)).all():
            audio_versions.sync(book, app.env_config.useraudiopath)
    term_context.backfill_in_background(app)  # a sentence for each word saved before they were kept
