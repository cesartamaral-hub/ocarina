"""
Ocarina's routes, registered on the Lute app. One module per area; see each module's docstring.
"""

from ocarina.tts import models
from ocarina.api import (
    audio,
    audio_versions,
    backups,
    book_import,
    books,
    dictionary,
    jobs,
    languages,
    pages,
    stats,
    system,
    tags,
    term_list,
    terms,
    tts_models,
    voices,
    web,
)


def register(app):
    "Register all Ocarina blueprints."
    models.configure(getattr(getattr(app, "env_config", None), "datapath", None))
    for module in (audio, audio_versions, backups, book_import, books, dictionary, jobs, languages, pages, stats, system, tags, term_list, terms, tts_models, voices, web):
        app.register_blueprint(module.bp)
