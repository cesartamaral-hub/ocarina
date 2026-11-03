"""
Ocarina's routes, registered on the Lute app. One module per area; see each module's docstring.
"""

from ocarina.api import (
    audio,
    book_import,
    books,
    jobs,
    pages,
    system,
    terms,
    tts_models,
    web,
)


def register(app):
    "Register all Ocarina blueprints."
    for module in (audio, book_import, books, jobs, pages, system, terms, tts_models, web):
        app.register_blueprint(module.bp)
