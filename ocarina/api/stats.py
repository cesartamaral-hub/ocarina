"""
JSON API for reading statistics (words read, from the pages you finish).

    GET /ocarina/api/stats   reading streak, words read per language by period, and daily history, and per language
                             (languages, totals): terms by status, what the texts hold and how much is known, books,
                             reading and streak, growth of the known words
"""

from flask import Blueprint, current_app, jsonify

from lute.db import db
from sqlalchemy import text as sql
from lute.stats.service import get_chart_data, get_reading_streak, get_table_data
from ocarina import book_index, language_stats, prefs, status_log

bp = Blueprint("ocarina_stats", __name__, url_prefix="/ocarina/api")


def _prefs():
    return prefs.load(prefs.path_for(current_app.env_config.datapath))


def _prior():
    "Ids of the languages whose already-known words count as learned (a choice per language)."
    return [int(k.rsplit(".", 1)[1]) for k, v in _prefs().items() if k.startswith("learned.prior.") and v is True and k.rsplit(".", 1)[1].isdigit()]


@bp.route("/stats", methods=["GET"])
def stats():
    "Streak in days; per language the words read today, this week, month, year and in all; the history."
    stale = book_index.stale_book_ids()
    if stale:
        book_index.build_in_background(current_app._get_current_object(), stale)  # pylint: disable=protected-access
    return jsonify(
        {
            "streak": get_reading_streak(db.session),
            "table": get_table_data(db.session),
            "chart": get_chart_data(db.session),
            **language_stats.summary(db.session, current_app.env_config.useraudiopath, _prior()),
        }
    )


@bp.route("/stats/vocabulary", methods=["GET"])
def vocabulary():
    "Per language the words you know and the words you are learning (a light call, for the book list)."
    terms = language_stats._terms(db.session)  # pylint: disable=protected-access
    names = dict(db.session.execute(sql("select LgID, LgName from languages")).all())
    prior = _prior()
    learned = status_log.learned_counts(db.session, prior)
    out = []
    for language_id, by_status in sorted(terms.items(), key=lambda kv: names.get(kv[0], "")):
        if language_id in names:
            summary = language_stats._term_summary(by_status)  # pylint: disable=protected-access
            goal = _prefs().get(f"learned.goal.{language_id}")
            out.append(
                {
                    "id": language_id,
                    "name": names[language_id],
                    "known": summary["known"],
                    "learning": summary["learning"],
                    "learned": learned.get(language_id, 0),
                    "goal": goal if isinstance(goal, int) and goal > 0 else None,
                    "countsPrior": language_id in prior,
                }
            )
    return jsonify(out)
