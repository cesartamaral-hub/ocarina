"""
Translation quality per model and language: the scores Ocarina measured and shipped (quality.json, see grades.py), and the ones measured on this
Mac (<data folder>/quality_local.json, which win). A language counts as covered by a text model when its grade is A to D.

    shipped()                  the shipped file as a dict ({"models": {model id: {language name: {code, chrf, errors, grade}}}})
    scores_for(model_id, datapath)   {code: {chrf, grade, errors, source}} with the local measurements over the shipped ones
    usable_codes(model_id)     the language codes the shipped scores grade A to D
    best_model(code, ids, datapath)  the id with the highest score for the language, when at least two are compared
"""

import json
import os

DIR = os.path.dirname(__file__)
USABLE = ("A", "B", "C", "D")
_shipped = {}


def shipped():
    if not _shipped:
        with open(os.path.join(DIR, "quality.json"), encoding="utf-8") as f:
            _shipped.update(json.load(f))
    return _shipped


def local_path(datapath):
    return os.path.join(datapath, "quality_local.json")


def _local(datapath):
    try:
        with open(local_path(datapath), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return {}


def scores_for(model_id, datapath=None):
    "{code: {chrf, grade, errors, source}} for a model: the shipped scores, with what was measured here over them."
    found = {}
    for row in shipped().get("models", {}).get(model_id, {}).values():
        found[row["code"]] = {"chrf": row["chrf"], "grade": row["grade"], "errors": row["errors"], "source": "shipped"}
    if datapath:
        for code, row in (_local(datapath).get(model_id) or {}).items():
            found[code] = {**row, "source": "checked"}
    return found


def usable_codes(model_id):
    return sorted(code for code, row in scores_for(model_id).items() if row["grade"] in USABLE)


def best_model(code, ids, datapath=None):
    "Of the models, the one with the best score for the language; None with fewer than two scored or when they tie."
    scored = [(scores_for(i, datapath).get(code), i) for i in ids]
    scored = [(row["chrf"], i) for row, i in scored if row and row["grade"] in USABLE]
    if len(scored) < 2:
        return None
    scored.sort(reverse=True)
    return scored[0][1] if scored[0][0] > scored[1][0] else None
