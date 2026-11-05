"""
JSON API for updates (see ocarina/updater.py).

    GET  /ocarina/api/update              {current, enabled, canInstall, latest: {...} | null, show, skipped, download: {...}, error?}
                                          ?force=1 asks GitHub again and ignores "check for updates" being off (Check now)
    PUT  /ocarina/api/update/settings     {"check": true | false}
    POST /ocarina/api/update/skip         {"version"}: never tell about this version again
    POST /ocarina/api/update/later        remind again tomorrow
    POST /ocarina/api/update/unskip       tell about the skipped version again
    POST /ocarina/api/update/download     start downloading the latest release
    POST /ocarina/api/update/install      unpack it and restart into it (the app quits)
"""

import os
import threading
import time

from flask import Blueprint, current_app, jsonify, request

from ocarina import offline, prefs, updater
from ocarina.version import VERSION

bp = Blueprint("ocarina_update", __name__, url_prefix="/ocarina/api")


def _prefs():
    return prefs.path_for(current_app.env_config.datapath)


def _quit():
    threading.Timer(1.0, lambda: os._exit(0)).start()  # after the reply has gone out


@bp.route("/update", methods=["GET"])
def status():
    "The state of updates; asks GitHub unless checking is off."
    saved = prefs.load(_prefs())
    force = request.args.get("force") == "1"
    enabled = saved.get(updater.PREF_CHECK, True) is not False
    body = {
        "current": VERSION,
        "enabled": enabled,
        "offline": offline.is_on(),
        "canInstall": updater.can_install(),
        "latest": None,
        "show": False,
        "skipped": saved.get(updater.PREF_SKIP) or None,
        "download": updater.state(),
    }
    if offline.is_on() or not (enabled or force):
        return jsonify(body)
    try:
        release = updater.latest(force=force)
    except updater.UpdateError as e:
        body["error"] = str(e)
        return jsonify(body)
    if release:
        body["latest"] = {k: release[k] for k in ("version", "notes", "url", "size")} | {"newer": updater.is_newer(release["version"])}
        body["show"] = updater.should_show(release, saved)
    return jsonify(body)


@bp.route("/update/settings", methods=["PUT"])
def settings():
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get("check"), bool):
        return jsonify({"error": "check must be true or false"}), 400
    prefs.update(_prefs(), {updater.PREF_CHECK: body["check"]})
    return jsonify({"check": body["check"]})


@bp.route("/update/skip", methods=["POST"])
def skip():
    version = (request.get_json(silent=True) or {}).get("version")
    if updater.version_key(version or "") is None:
        return jsonify({"error": "Which version?"}), 400
    prefs.update(_prefs(), {updater.PREF_SKIP: version})
    return jsonify({"skipped": version})


@bp.route("/update/unskip", methods=["POST"])
def unskip():
    prefs.update(_prefs(), {updater.PREF_SKIP: ""})
    return jsonify({"skipped": None})


@bp.route("/update/later", methods=["POST"])
def later():
    prefs.update(_prefs(), {updater.PREF_SNOOZE: time.time() + updater.SNOOZE_SECONDS})
    return jsonify({"ok": True})


@bp.route("/update/download", methods=["POST"])
def download():
    if offline.is_on():
        return jsonify({"error": "Work offline is on (Settings → General).", "code": "offline_mode"}), 409
    try:
        release = updater.latest()
    except updater.UpdateError as e:
        return jsonify({"error": str(e)}), 502
    if not release or not updater.is_newer(release["version"]):
        return jsonify({"error": "There is no newer version."}), 409
    updater.start_download(release, current_app.env_config.datapath)
    return jsonify(updater.state()), 202


@bp.route("/update/install", methods=["POST"])
def install():
    try:
        updater.install(current_app.env_config.datapath, _quit)
    except updater.UpdateError as e:
        return jsonify({"error": str(e)}), 409
    return jsonify({"restarting": True})
