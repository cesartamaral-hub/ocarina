"""A language gets a small dictionary of its own: when it is added (and at start, for those that have none), WikDict's is downloaded."""

import threading

from ocarina import offline, translate
from ocarina.api import jobs
from ocarina.dictionaries import install, registry


def has_pack(datapath, code):
    return any(p.language == code for p in registry.all_packs(datapath))


def ensure_default(datapath, language_name):
    "Start downloading the small dictionary of a language that has none; returns the job, or None when there is nothing to do."
    code = translate.code_for(language_name or "")
    if offline.is_on() or not code or has_pack(datapath, code):
        return None
    entry = next((p for p in install.catalog([code]) if p["type"] == "wikdict"), None)
    if entry is None or jobs.active(kind="dictionary", pack_id=entry["id"]):
        return None

    def run(job, check):
        def progress(done, total):
            job["done"], job["total"] = done, total

        check()
        install.download(entry, datapath, progress, check)

    return jobs.submit("dictionary", run, pack_id=entry["id"], title=entry["name"])


def ensure_defaults_in_background(app, language_names):
    "At start: the languages of the library that have no dictionary get one, when there is a connection (quietly, nothing is shown if there is not)."

    def work():
        with app.app_context():
            for name in language_names:
                try:
                    ensure_default(app.env_config.datapath, name)
                except Exception:  # pylint: disable=broad-exception-caught
                    pass

    threading.Thread(target=work, name="default-dictionaries", daemon=True).start()
