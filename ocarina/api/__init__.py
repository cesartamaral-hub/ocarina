"""
Ocarina's routes, registered on the Lute app. One module per area; see each module's docstring.
"""

from ocarina import offline, paths
from ocarina.tts import models
from ocarina.api import (
    audio,
    audio_versions,
    backups,
    book_import,
    book_translation,
    books,
    dictionaries,
    dictionary,
    jobs,
    languages,
    offline_mode,
    pages,
    pronounce,
    stats,
    storage,
    system,
    tags,
    term_list,
    terms,
    translate,
    update,
    tts_models,
    voices,
    web,
)


def register(app):
    "Register all Ocarina blueprints."
    paths.configure(getattr(getattr(app, "env_config", None), "datapath", None))
    models.configure(getattr(getattr(app, "env_config", None), "datapath", None))
    offline.configure(getattr(getattr(app, "env_config", None), "datapath", None))
    offline.install_guard()  # while Work offline is on, nothing of this process reaches another computer
    for module in (audio, audio_versions, backups, book_import, book_translation, books, dictionaries, dictionary, jobs, languages, offline_mode, pages, pronounce, stats, storage, system, tags, term_list, terms, translate, tts_models, update, voices, web):
        app.register_blueprint(module.bp)
