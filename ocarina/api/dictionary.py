"""
JSON API for word definitions (Wiktionary, cached; see ocarina/dictionary.py).

    GET /ocarina/api/dictionary/define?languageId=<id>&text=<word>[&cacheOnly=true]

Answers {found, word, entries: [{partOfSpeech, definitions: [{text, examples, lemma?}]}], lemmas: [{word, entries}],
url, cached, stale}. lemmas holds the base forms that inflected-form definitions point to, with their meanings.
With cacheOnly and nothing cached, {found: false, cacheMiss: true}. 502 with {error, code: "offline"} when
Wiktionary can't be reached and the word was never looked up before.
"""

from flask import Blueprint, current_app, jsonify, request

from lute.db import db
from lute.models.language import Language
from ocarina import dictionary

bp = Blueprint("ocarina_dictionary", __name__, url_prefix="/ocarina/api")


@bp.route("/dictionary/define", methods=["GET"])
def define():
    "Definitions of a word in a language."
    try:
        language = db.session.get(Language, int(request.args.get("languageId", "")))
    except ValueError:
        language = None
    if language is None:
        return jsonify({"error": "Unknown language"}), 404
    try:
        result = dictionary.define(
            current_app.env_config.datapath,
            language.name,
            request.args.get("text", ""),
            cache_only=request.args.get("cacheOnly") == "true",
        )
    except dictionary.DictionaryError as e:
        return jsonify({"error": str(e), "code": "offline" if e.offline else "bad_input"}), 502 if e.offline else 400
    if result is None:
        return jsonify({"found": False, "cacheMiss": True})
    result.pop("fetched", None)
    return jsonify(result)
