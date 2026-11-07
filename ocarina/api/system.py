"""
Small app-level endpoints.

    POST /ocarina/api/open-external   open a dictionary page in the system browser
    GET  /ocarina/api/system/hardware  {chip, ramGb, tier} of this Mac (small up to 8 GB, medium up to 16, large)
    GET  /ocarina/api/prefs           saved preferences (PUT merges new values in)
"""

import webbrowser
from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, request

from ocarina import hardware, prefs

bp = Blueprint("ocarina_system", __name__, url_prefix="/ocarina/api")


@bp.route("/open-external", methods=["POST"])
def open_external():
    "Open a dictionary page in the system browser (web pages only)."
    url = (request.get_json(silent=True) or {}).get("url", "")
    if urlparse(url).scheme not in ("http", "https"):
        return jsonify({"error": "Only http and https links can be opened"}), 400
    webbrowser.open(url)
    return jsonify({"ok": True})


@bp.route("/prefs", methods=["GET", "PUT"])
def preferences():
    "Preferences live in the data folder, so they survive restarts (the web view's storage does not)."
    path = prefs.path_for(current_app.env_config.datapath)
    if request.method == "PUT":
        values = request.get_json(silent=True)
        if not isinstance(values, dict):
            return jsonify({"error": "A JSON object is required"}), 400
        return jsonify(prefs.update(path, values))
    return jsonify(prefs.load(path))


@bp.route("/system/hardware", methods=["GET"])
def hardware_info():
    "The chip and memory of this Mac, and the tier Ocarina treats it as."
    return jsonify(hardware.info())
