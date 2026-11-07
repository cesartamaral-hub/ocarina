"""
JSON API for word definitions (Wiktionary, cached; see ocarina/dictionary.py).

    GET /ocarina/api/dictionary/parts?languageId=<id>&text=<several words>
    {parts: [{text, words, source, entries}]}: what the dictionaries on this Mac know inside a selection (runs of two or more words, then single words)
    GET /ocarina/api/dictionary/define?languageId=<id>&text=<word>[&cacheOnly=true][&online=true]

Answers {found, word, entries: [{partOfSpeech, definitions: [{text, examples, lemma?}]}], lemmas: [{word, entries}],
url, cached, stale}. lemmas holds the base forms that inflected-form definitions point to, with their meanings.
`source` says which dictionary answered ({id, name, license, offline}); `others` are the other dictionaries that know the word, each
{source, entries, lemmas}. The dictionaries on this Mac come first; Wiktionary over the internet is asked when none knows the word, or
with online=true (then it comes in `others`). With cacheOnly and nothing cached, {found: false, cacheMiss: true}. 502 with {error, code: "offline"} when
Wiktionary can't be reached and the word was never looked up before.
"""

from flask import Blueprint, current_app, jsonify, request

from lute.db import db
from lute.models.language import Language
from ocarina import dictionary, expressions, translate

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
            online=request.args.get("online") == "true",
        )
    except dictionary.DictionaryError as e:
        return jsonify({"error": str(e), "code": "offline" if e.offline else "bad_input"}), 502 if e.offline else 400
    if result is None:
        return jsonify({"found": False, "cacheMiss": True})
    result.pop("fetched", None)
    return jsonify(result)


@bp.route("/dictionary/parts", methods=["GET"])
def parts():
    "What the dictionaries on this Mac say about the runs of words inside a selection."
    language = db.session.get(Language, int(request.args["languageId"])) if request.args.get("languageId", "").isdigit() else None
    if language is None:
        return jsonify({"error": "Unknown language"}), 404
    code = translate.code_for(language.name)
    found = expressions.parts(current_app.env_config.datapath, code, request.args.get("text", "")) if code else []
    return jsonify({"parts": found})
