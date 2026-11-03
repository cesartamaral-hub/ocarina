"""
Serves the built React frontend at /ocarina/app/.
"""

import os

from flask import Blueprint, send_from_directory

DIST = os.path.join(os.path.dirname(__file__), "..", "web", "dist")

bp = Blueprint("ocarina_web", __name__, url_prefix="/ocarina/app")


@bp.route("/", defaults={"path": ""})
@bp.route("/<path:path>")
def frontend(path):
    "Static files from the build; any other path gets index.html (client-side routes)."
    if path and os.path.exists(os.path.join(DIST, path)):
        return send_from_directory(DIST, path)
    return send_from_directory(DIST, "index.html")
