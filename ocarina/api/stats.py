"""
JSON API for reading statistics (words read, from the pages you finish).

    GET /ocarina/api/stats   reading streak, words read per language by period, and daily history
"""

from flask import Blueprint, jsonify

from lute.db import db
from lute.stats.service import get_chart_data, get_reading_streak, get_table_data

bp = Blueprint("ocarina_stats", __name__, url_prefix="/ocarina/api")


@bp.route("/stats", methods=["GET"])
def stats():
    "Streak in days; per language the words read today, this week, month, year and in all; the history."
    return jsonify(
        {
            "streak": get_reading_streak(db.session),
            "table": get_table_data(db.session),
            "chart": get_chart_data(db.session),
        }
    )
