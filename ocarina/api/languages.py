"""
JSON API for languages and their settings (dictionaries, parser, word characters).

    GET    /ocarina/api/languages                  all languages with book and term counts
    GET    /ocarina/api/languages/<id>             one language with all its settings
    POST   /ocarina/api/languages                  create a language
    PUT    /ocarina/api/languages/<id>             change a language
    DELETE /ocarina/api/languages/<id>?force=true  delete it with all its books and terms
    GET    /ocarina/api/languages/template         defaults for a new language, or a predefined one
                                                   (?name=Dutch); predefined names are listed too
    GET    /ocarina/api/languages/support          what Ocarina can do for each language (?names=Italian,Dutch for others)
    GET    /ocarina/api/languages/parsers          parser types that can be chosen
    POST   /ocarina/api/languages/predefined       add predefined languages by name ({"names": [...],
                                                   "books": true to also add their sample stories})
"""

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text as sql
from sqlalchemy.exc import IntegrityError

from lute.db import db
from lute.language.service import Service as LanguageService
from lute.models.language import Language, LanguageDictionary
from lute.parse.registry import supported_parsers
from ocarina import language_support
from ocarina.dictionaries import setup as dictionary_setup

HIDDEN = {"Portuguese"}  # offered as European Portuguese and Brazilian Portuguese; a library that has the plain one keeps it
bp = Blueprint("ocarina_languages", __name__, url_prefix="/ocarina/api")

USE_FOR = ("terms", "sentences")
DICT_TYPES = ("embeddedhtml", "popuphtml")
MAX_NAME, MAX_URL, MAX_RULE = 40, 200, 500


def _language_settings(language):
    "A language with all its settings, as JSON."
    return {
        "id": language.id,
        "name": language.name,
        "parserType": language.parser_type,
        "showRomanization": bool(language.show_romanization),
        "rightToLeft": bool(language.right_to_left),
        "characterSubstitutions": language.character_substitutions or "",
        "regexpSplitSentences": language.regexp_split_sentences or "",
        "exceptionsSplitSentences": language.exceptions_split_sentences or "",
        "wordCharacters": language.word_characters or "",
        "dictionaries": [
            {"useFor": d.usefor, "dictType": d.dicttype, "url": d.dicturi, "active": bool(d.is_active)}
            for d in sorted(language.dictionaries, key=lambda d: d.sort_order)
        ],
    }


def _parser_types():
    return [{"type": key, "name": parser.name()} for key, parser in supported_parsers()]


def _check(body):
    "The first problem with the submitted settings, or None."
    name = (body.get("name") or "").strip()
    if not name or len(name) > MAX_NAME:
        return f"The name is required and at most {MAX_NAME} characters"
    if body.get("parserType") not in [p["type"] for p in _parser_types()]:
        return "Choose how the language is parsed"
    for field in ("characterSubstitutions", "regexpSplitSentences", "exceptionsSplitSentences", "wordCharacters"):
        if len(body.get(field) or "") > MAX_RULE:
            return f"{field} is at most {MAX_RULE} characters"
    dictionaries = body.get("dictionaries") or []
    for d in dictionaries:
        if d.get("useFor") not in USE_FOR or d.get("dictType") not in DICT_TYPES:
            return "A dictionary has an unknown use or type"
        if not (d.get("url") or "").strip() or len(d["url"]) > MAX_URL:
            return f"Every dictionary needs a web address of at most {MAX_URL} characters"
    for use in USE_FOR:
        if not any(d["useFor"] == use and d.get("active") for d in dictionaries):
            return f"Add an active dictionary for {use}"
    return None


def _apply(language, body):
    "Copy submitted settings onto a Language."
    language.name = body["name"].strip()
    language.parser_type = body["parserType"]
    language.show_romanization = bool(body.get("showRomanization"))
    language.right_to_left = bool(body.get("rightToLeft"))
    language.character_substitutions = body.get("characterSubstitutions", "")
    language.regexp_split_sentences = body.get("regexpSplitSentences", "")
    language.exceptions_split_sentences = body.get("exceptionsSplitSentences", "")
    language.word_characters = body.get("wordCharacters", "")
    language.dictionaries = []
    for i, d in enumerate(body["dictionaries"]):
        entry = LanguageDictionary()
        entry.usefor, entry.dicttype, entry.dicturi = d["useFor"], d["dictType"], d["url"].strip()
        entry.is_active, entry.sort_order = bool(d.get("active")), i + 1
        language.dictionaries.append(entry)


def _save(language, body):
    problem = _check(body)
    if problem:
        return jsonify({"error": problem}), 400
    _apply(language, body)
    try:
        db.session.add(language)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": f"A language named {body['name'].strip()} already exists"}), 409
    return jsonify(_language_settings(language)), 200


@bp.route("/languages", methods=["GET"])
def languages():
    "All languages, with how many books and (known or learning) terms each has."
    rows = db.session.execute(
        sql(
            "select LgID, LgName, "
            "(select count(*) from books where BkLgID = LgID), "
            "(select count(*) from words where WoLgID = LgID and WoStatus != 0) "
            "from languages order by LgName"
        )
    )
    return jsonify([{"id": r[0], "name": r[1], "books": r[2], "terms": r[3]} for r in rows])


@bp.route("/languages/support", methods=["GET"])
def support():
    "What Ocarina can do for each language in the library, or for the names given (?names=Italian,Dutch)."
    asked = [n.strip() for n in request.args.get("names", "").split(",") if n.strip()]
    names = asked or [r[0] for r in db.session.execute(sql("select LgName from languages order by LgName"))]
    datapath = current_app.env_config.datapath
    return jsonify([language_support.support(n, datapath) for n in names])


@bp.route("/languages/parsers", methods=["GET"])
def parsers():
    "Parser types that can be chosen."
    return jsonify(_parser_types())


@bp.route("/languages/template", methods=["GET"])
def template():
    "Settings to start a new language from: blank defaults, or a predefined language by name."
    service = LanguageService(db.session)
    predefined = [p for p in service.supported_predefined_languages() if p.name not in HIDDEN]
    taken = {n for (n,) in db.session.execute(sql("select LgName from languages"))}
    available = [p for p in predefined if p.name not in taken]
    name = request.args.get("name")
    chosen = next((p for p in predefined if p.name == name), None) if name else Language()
    if chosen is None:
        return jsonify({"error": "Unknown predefined language"}), 404
    body = _language_settings(chosen)
    body["id"] = None
    names = sorted(p.name for p in available)
    return jsonify({"language": body, "predefined": names, "withStory": [n for n in names if service.get_language_def(n).books]})


@bp.route("/languages/predefined", methods=["POST"])
def add_predefined():
    "Add predefined languages (the first-run screen); names already in use are skipped."
    body = request.get_json(silent=True) or {}
    names = body.get("names")
    if not isinstance(names, list) or not names:
        return jsonify({"error": "Choose at least one language"}), 400
    service = LanguageService(db.session)
    available = {p.name for p in service.supported_predefined_languages() if p.name not in HIDDEN}
    taken = {n for (n,) in db.session.execute(sql("select LgName from languages"))}
    added, skipped = [], []
    for name in names:
        if name not in available or name in taken:
            skipped.append(name)
            continue
        if body.get("books"):
            language_id = service.load_language_def(name)
        else:
            language = service.get_language_def(name).language
            db.session.add(language)
            db.session.commit()
            language_id = language.id
        added.append({"id": language_id, "name": name})
        try:
            dictionary_setup.ensure_default(current_app.env_config.datapath, name)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
    return jsonify({"added": added, "skipped": skipped}), 201 if added else 400


@bp.route("/languages/<int:language_id>", methods=["GET"])
def get_language(language_id):
    "One language with all its settings."
    language = db.session.get(Language, language_id)
    if language is None:
        return jsonify({"error": "No such language"}), 404
    return jsonify(_language_settings(language))


def _small_dictionary(response):
    "A new language gets the small dictionary of its own (a download, in the background; nothing is said if it cannot be had)."
    try:
        name = (response.get_json() or {}).get("name")
        dictionary_setup.ensure_default(current_app.env_config.datapath, name)
    except Exception:  # pylint: disable=broad-exception-caught
        pass


@bp.route("/languages", methods=["POST"])
def create_language():
    "Create a language."
    response, status = _save(Language(), request.get_json(silent=True) or {})
    if status == 200:
        _small_dictionary(response)
    return response, 201 if status == 200 else status


@bp.route("/languages/<int:language_id>", methods=["PUT"])
def update_language(language_id):
    "Change a language's settings."
    language = db.session.get(Language, language_id)
    if language is None:
        return jsonify({"error": "No such language"}), 404
    return _save(language, request.get_json(silent=True) or {})


@bp.route("/languages/<int:language_id>", methods=["DELETE"])
def delete_language(language_id):
    "Delete a language; with books or terms in it, only when force=true (they are deleted too)."
    language = db.session.get(Language, language_id)
    if language is None:
        return jsonify({"error": "No such language"}), 404
    books, terms = db.session.execute(
        sql(
            "select (select count(*) from books where BkLgID = :i), "
            "(select count(*) from words where WoLgID = :i)"
        ),
        {"i": language_id},
    ).one()
    if (books or terms) and request.args.get("force") != "true":
        return jsonify({"error": "The language still has books or terms", "books": books, "terms": terms}), 409
    db.session.delete(language)
    db.session.commit()
    return jsonify({"deleted": language_id, "books": books, "terms": terms})
