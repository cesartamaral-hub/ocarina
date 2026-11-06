"""
The log file (see ocarina/logs.py).

    GET  /ocarina/api/log        {path, folder, bytes}
    POST /ocarina/api/log/open   show the log folder in Finder
"""

import os
import subprocess

from flask import Blueprint, current_app, jsonify

from ocarina import logs

bp = Blueprint("ocarina_diagnostics", __name__, url_prefix="/ocarina/api")


def _datapath():
    return current_app.env_config.datapath


@bp.route("/log", methods=["GET"])
def info():
    path = logs.log_path(_datapath())
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0
    return jsonify({"path": path, "folder": logs.log_dir(_datapath()), "bytes": size})


@bp.route("/log/open", methods=["POST"])
def open_folder():
    folder = logs.log_dir(_datapath())
    os.makedirs(folder, exist_ok=True)
    if current_app.config.get("TESTING") or os.environ.get("OCARINA_NO_OPEN"):
        return jsonify({"opened": False, "folder": folder})
    subprocess.run(["open", folder], check=False, timeout=10)
    return jsonify({"opened": True, "folder": folder})
