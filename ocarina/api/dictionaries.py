"""
JSON API for the dictionaries on this Mac (see ocarina/dictionaries).

    GET    /ocarina/api/dictionaries                the packs (on or off, in the order they are asked), the ones that can be downloaded
                                                    and the languages of your library
    PUT    /ocarina/api/dictionaries/choice         {"order": [ids], "off": [ids]}
    DELETE /ocarina/api/dictionaries/<id>           delete a pack of yours (the built-in ones stay)
    POST   /ocarina/api/dictionaries/<id>/download  start downloading one of the packs of the list (a job)
    POST   /ocarina/api/dictionaries/import         add a StarDict dictionary (form: files, language, name?, meaning? "en" or the language itself) (a job)
"""

import os
import shutil
import tempfile

from flask import Blueprint, current_app, jsonify, request

from lute.db import db
from lute.models.language import Language
from ocarina import offline, translate
from ocarina.api import jobs
from ocarina.dictionaries import install, registry, stardict

bp = Blueprint("ocarina_dictionaries", __name__, url_prefix="/ocarina/api")


def _datapath():
    return current_app.env_config.datapath


def _languages():
    found = []
    for language in db.session.query(Language).all():
        code = translate.code_for(language.name)
        if code and all(code != f["code"] for f in found):
            found.append({"code": code, "name": language.name})
    return found


@bp.route("/dictionaries", methods=["GET"])
def listing():
    "Everything the Dictionaries page shows."
    have = {p["id"] for p in registry.listing(_datapath())}
    active = jobs.active(kind="dictionary")
    languages = _languages()
    available = [
        {**p, "installed": p["id"] in have, "job": next((j["id"] for j in active if j.get("pack_id") == p["id"]), None)}
        for p in install.catalog({l["code"] for l in languages})
    ]
    return jsonify({"packs": registry.listing(_datapath()), "available": available, "languages": languages})


@bp.route("/dictionaries/choice", methods=["PUT"])
def choose():
    "Which packs are on and in what order."
    body = request.get_json(silent=True) or {}
    order, off = body.get("order"), body.get("off")
    if (order is not None and not isinstance(order, list)) or (off is not None and not isinstance(off, list)):
        return jsonify({"error": "order and off are lists of dictionary ids"}), 400
    registry.save_choice(_datapath(), order=order, off=off)
    return jsonify({"packs": registry.listing(_datapath())})


@bp.route("/dictionaries/<pack_id>", methods=["DELETE"])
def delete(pack_id):
    "Delete a pack of the user's."
    if not registry.remove(_datapath(), pack_id):
        return jsonify({"error": "No such dictionary of yours (the ones that come with Ocarina cannot be deleted; switch them off instead)."}), 404
    return jsonify({"deleted": pack_id})


@bp.route("/dictionaries/<pack_id>/download", methods=["POST"])
def download(pack_id):
    "Download one of the packs of the list."
    entry = install.find(pack_id)
    if entry is None:
        return jsonify({"error": "Unknown dictionary"}), 404
    if offline.is_on():
        return jsonify({"error": "Work offline is on, so nothing can be downloaded. Turn it off in Settings → General.", "code": "offline_mode"}), 409
    if jobs.active(kind="dictionary", pack_id=pack_id):
        return jsonify({"error": "It is already being downloaded.", "code": "already_queued"}), 409
    datapath = _datapath()

    def run(job, check):
        def progress(done, total):
            job["done"], job["total"] = done, total

        check()
        install.download(entry, datapath, progress, check)

    return jsonify(jobs.submit("dictionary", run, pack_id=pack_id, title=entry["name"])), 202


@bp.route("/dictionaries/import", methods=["POST"])
def import_files():
    "Add a StarDict dictionary from the files (or one archive) sent."
    code = (request.form.get("language") or "").strip()
    if code not in {l["code"] for l in _languages()}:
        return jsonify({"error": "Choose the language of the dictionary."}), 400
    files = [f for f in request.files.getlist("files") if f.filename]
    if not files:
        return jsonify({"error": "Choose the dictionary files (.ifo, .idx and .dict or .dict.dz), or one .zip or .tar.gz of them."}), 400
    staging = tempfile.mkdtemp(prefix="ocarina-dict-")
    try:
        for f in files:
            f.save(os.path.join(staging, os.path.basename(f.filename)))
        if len(files) == 1 and not files[0].filename.endswith(".ifo"):
            archive = os.path.join(staging, os.path.basename(files[0].filename))
            folder = tempfile.mkdtemp(prefix="ocarina-dict-")
            try:
                stardict.unpack(archive, folder)
            except stardict.StarDictError as e:
                shutil.rmtree(folder, ignore_errors=True)
                shutil.rmtree(staging, ignore_errors=True)
                return jsonify({"error": str(e)}), 400
            shutil.rmtree(staging, ignore_errors=True)
            staging = folder
    except OSError as e:
        shutil.rmtree(staging, ignore_errors=True)
        return jsonify({"error": f"The files could not be read ({e})."}), 400
    name = (request.form.get("name") or "").strip() or None
    meaning = request.form.get("meaning") or "en"
    if meaning not in ("en", code):
        return jsonify({"error": "The meanings are in English or in the language of the dictionary."}), 400
    datapath = _datapath()

    def run(job, check):
        try:
            check()
            job["phase"] = "importing"
            install.import_stardict(staging, datapath, code, name, meaning)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    return jsonify(jobs.submit("dictionary", run, title=name or files[0].filename)), 202
