"""
Ocarina's routes, registered on the Lute app. One module per area; see each module's docstring.
"""

from ocarina.api import (
    audio,
    backups,
    book_import,
    books,
    jobs,
    languages,
    pages,
    stats,
    system,
    term_list,
    terms,
    tts_models,
    voices,
    web,
)


def register(app):
    "Register all Ocarina blueprints."
    for module in (audio, backups, book_import, books, jobs, languages, pages, stats, system, term_list, terms, tts_models, voices, web):
        app.register_blueprint(module.bp)
