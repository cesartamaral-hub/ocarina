"""
JSON API for the list of all terms: search, filters, sorting, paging, bulk changes, CSV export.

    GET  /ocarina/api/term-list          a page of terms (filters and sorting as query parameters)
    GET  /ocarina/api/term-list/export   the same filter as a CSV file, all rows
    GET  /ocarina/api/tags               all term tags
    POST /ocarina/api/terms/bulk         change or delete several terms of one language

Filters: language, q (text, translation or parent), statusMin, statusMax, includeIgnored,
parentsOnly, tag. Sorting: sort (text, translation, status, created, parent, language), order.
Editing a single term uses the endpoints in terms.py.
"""

import csv
import io

from flask import Blueprint, Response, jsonify, request
from sqlalchemy import text as sql

from lute.db import db
from lute.term.model import Repository as TermRepository
from lute.term.service import BulkTermUpdateData, Service as TermService, TermServiceException
from lute.utils.data_tables import supported_parser_type_criteria
from ocarina.api.common import clean
from ocarina.api.terms import STATUSES

bp = Blueprint("ocarina_term_list", __name__, url_prefix="/ocarina/api")

MAX_PAGE = 500
SORTS = {
    "text": "lower(replace(w.WoText, char(8203), ''))",
    "translation": "lower(ifnull(w.WoTranslation, ''))",
    "status": "w.WoStatus",
    "created": "w.WoCreated",
    "parent": "lower(ifnull(parents.parentlist, ''))",
    "language": "L.LgName",
}
SEP = ";;"

BASE = """
FROM words w
INNER JOIN languages L ON L.LgID = w.WoLgID
LEFT OUTER JOIN (
  SELECT WpWoID AS WoID, GROUP_CONCAT(PText, ';;') AS parentlist FROM (
    SELECT WpWoID, WoText AS PText FROM wordparents wp
    INNER JOIN words ON WoID = WpParentWoID ORDER BY WoText
  ) GROUP BY WpWoID
) AS parents ON parents.WoID = w.WoID
LEFT OUTER JOIN termcontexts tc ON tc.TcWoID = w.WoID
LEFT OUTER JOIN (
  SELECT WtWoID AS WoID, GROUP_CONCAT(TgText, ';;') AS taglist FROM (
    SELECT WtWoID, TgText FROM wordtags wt INNER JOIN tags t ON t.TgID = wt.WtTgID ORDER BY TgText
  ) GROUP BY WtWoID
) AS tags ON tags.WoID = w.WoID
"""


def _int(name, default):
    try:
        return int(request.args.get(name, default))
    except ValueError:
        return default


def _like(value):
    "A LIKE pattern matching the text anywhere, with the wildcard characters escaped."
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.lower()}%"


def _statuses():
    "The statuses asked for in `statuses` (like 1,2,3,99), or None when the parameter is not there."
    raw = request.args.get("statuses")
    if raw is None:
        return None
    return sorted({int(x) for x in raw.split(",") if x.strip().isdigit() and int(x) in STATUSES and int(x) > 0})  # 0 is a word with no status yet: not vocabulary


def _where(with_status=True):
    "WHERE clause and bound values for the filters in the query string (with_status=False leaves the status out, to count each)."
    wheres = [f"L.LgParserType IN ({supported_parser_type_criteria()})"]
    values = {}
    if _int("language", 0):
        wheres.append("L.LgID = :language")
        values["language"] = _int("language", 0)
    statuses = _statuses()
    if with_status and statuses is not None:
        wheres.append("w.WoStatus IN (" + ",".join(str(s) for s in statuses) + ")" if statuses else "0")
    elif with_status:
        in_range = "w.WoStatus >= :smin AND w.WoStatus <= :smax AND w.WoStatus != 98"
        if request.args.get("includeIgnored") == "true":
            in_range = f"(({in_range}) OR w.WoStatus = 98)"
        wheres.append(in_range)
        values["smin"], values["smax"] = _int("statusMin", 0), _int("statusMax", 99)
    if request.args.get("parentsOnly") == "true":
        wheres.append("parents.parentlist IS NULL")
    q = request.args.get("q", "").strip()
    if q:
        wheres.append(
            "(lower(replace(w.WoText, char(8203), '')) LIKE :q ESCAPE '\\' "
            "OR lower(ifnull(w.WoTranslation, '')) LIKE :q ESCAPE '\\' "
            "OR lower(ifnull(parents.parentlist, '')) LIKE :q ESCAPE '\\')"
        )
        values["q"] = _like(q)
    tag = request.args.get("tag", "").strip()
    if tag:
        wheres.append(
            "w.WoID IN (SELECT WtWoID FROM wordtags INNER JOIN tags ON TgID = WtTgID WHERE TgText = :tag)"
        )
        values["tag"] = tag
    return " WHERE " + " AND ".join(wheres), values


def _order():
    column = SORTS.get(request.args.get("sort", "text"), SORTS["text"])
    direction = "DESC" if request.args.get("order") == "desc" else "ASC"
    return f" ORDER BY {column} {direction}, w.WoID"


SELECT = (
    "SELECT w.WoID, w.WoText, parents.parentlist, w.WoTranslation, L.LgName, L.LgID, "
    "ifnull(tags.taglist, ''), w.WoStatus, datetime(w.WoCreated, 'localtime'), "
    "tc.TcSentence, tc.TcBkID, tc.TcPage, tc.TcFound "
)


def _row(r):
    return {
        "id": r[0],
        "text": clean(r[1]),
        "parents": [clean(p) for p in r[2].split(SEP)] if r[2] else [],
        "translation": r[3] or "",
        "language": r[4],
        "languageId": r[5],
        "tags": r[6].split(SEP) if r[6] else [],
        "status": r[7],
        "created": r[8],
        "context": {"sentence": r[9], "bookId": r[10], "page": r[11], "found": bool(r[12])} if r[9] else None,
    }


@bp.route("/term-list", methods=["GET"])
def term_list():
    "One page of terms matching the filters, and how many match in all."
    where, values = _where()
    size = min(max(_int("pageSize", 50), 1), MAX_PAGE)
    page = max(1, _int("page", 1))
    total = db.session.execute(sql("SELECT count(*) " + BASE + where), values).scalar()
    rows = db.session.execute(
        sql(SELECT + BASE + where + _order() + " LIMIT :limit OFFSET :offset"),
        {**values, "limit": size, "offset": (page - 1) * size},
    )
    body = {"total": total, "page": page, "pageSize": size, "rows": [_row(r) for r in rows]}
    if request.args.get("counts") == "true":
        # How many words each status has under the other filters, for the status chips.
        where_all, values_all = _where(with_status=False)
        counted = db.session.execute(sql("SELECT w.WoStatus, count(*) " + BASE + where_all + " GROUP BY w.WoStatus"), values_all)
        body["counts"] = {str(status): n for status, n in counted}
    return jsonify(body)


@bp.route("/term-list/export", methods=["GET"])
def export_terms():
    "All terms matching the filters, as a CSV file."
    where, values = _where()
    rows = [_row(r) for r in db.session.execute(sql(SELECT + BASE + where + _order()), values)]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["term", "parent", "translation", "language", "tags", "added", "status"])
    for r in rows:
        writer.writerow(
            [r["text"], "; ".join(r["parents"]), r["translation"], r["language"], "; ".join(r["tags"]), r["created"], r["status"]]
        )
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=terms.csv"},
    )


@bp.route("/tags", methods=["GET"])
def tags():
    "All term tags."
    rows = db.session.execute(sql("SELECT TgText FROM tags ORDER BY TgText"))
    return jsonify([r[0] for r in rows])


@bp.route("/terms/bulk", methods=["POST"])
def bulk():
    """
    Change or delete several terms, all of one language:
    {ids, status?, addTags?, removeTags?, parent?, removeParents?, lowercase?, delete?}
    """
    body = request.get_json(silent=True) or {}
    ids = body.get("ids")
    if not isinstance(ids, list) or not ids or not all(isinstance(i, int) for i in ids):
        return jsonify({"error": "ids must be a list of term ids"}), 400
    if body.get("delete"):
        repo = TermRepository(db.session)
        try:
            for term_id in ids:
                repo.delete(repo.load(term_id))
        except ValueError:
            db.session.rollback()
            return jsonify({"error": "No such term"}), 404
        repo.commit()
        return jsonify({"deleted": len(ids)})
    update = BulkTermUpdateData()
    update.term_ids = ids
    if "status" in body:
        if body["status"] not in STATUSES:
            return jsonify({"error": f"Bad status {body['status']}"}), 400
        update.change_status, update.status_value = True, body["status"]
    update.add_tags = [t.strip() for t in body.get("addTags", []) if t.strip()]
    update.remove_tags = [t.strip() for t in body.get("removeTags", []) if t.strip()]
    update.remove_parents = bool(body.get("removeParents"))
    update.lowercase_terms = bool(body.get("lowercase"))
    parent = (body.get("parent") or "").strip()
    update.parent_text = parent or None
    try:
        TermService(db.session).apply_bulk_updates(update)
    except TermServiceException as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    return jsonify({"updated": len(ids)})
