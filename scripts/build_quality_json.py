"""
Turns a raw measurement (scripts/measure_quality.py) into the shipped scores, ocarina/quality/quality.json: per model and language the chrF
score, the grade and how many sentences failed. The translations themselves are not kept.

    python scripts/build_quality_json.py <measured.json> [out.json]
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ocarina.quality.grades import BANDS, SENTENCES, grade  # noqa: E402  pylint: disable=wrong-import-position


def build(measured, date):
    models = {}
    for model_id, languages in measured.items():
        models[model_id] = {
            name: {"code": r["code"], "chrf": r["chrf"], "errors": r["errors"], "grade": grade(r["chrf"], r["errors"])} for name, r in sorted(languages.items())
        }
    return {
        "version": 1,
        "measured": date,
        "test": f"FLORES-200 devtest, {SENTENCES} sentences per language, into English, chrF (CC BY-SA 4.0, NLLB Team, Meta AI)",
        "bands": [{"from": floor, "grade": letter} for floor, letter in BANDS],
        "note": "Portuguese was measured with FLORES's Portuguese, which is Brazilian; the same score is shown for European Portuguese.",
        "models": models,
    }


if __name__ == "__main__":
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "ocarina", "quality", "quality.json")
    with open(sys.argv[1], encoding="utf-8") as f:
        data = build(json.load(f), "2026-11-06")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print({m: len(v) for m, v in data["models"].items()}, "->", out)
