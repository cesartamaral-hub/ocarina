"""
The translation quality scores: chrF, the grade bands, the test set and the shipped measurements.
"""

import json
import os

from ocarina import quality  # noqa: F401  pylint: disable=unused-import
from ocarina.quality import chrf as chrf_module
from ocarina.quality.grades import BANDS, grade
from ocarina.tts import models as model_files

FOLDER = os.path.join(os.path.dirname(chrf_module.__file__))


def _load(name):
    with open(os.path.join(FOLDER, name), encoding="utf-8") as f:
        return json.load(f)


def test_chrf_is_100_for_a_perfect_translation_and_low_for_an_unrelated_one():
    assert chrf_module.chrf(["Yesterday I went to the market."], ["Yesterday I went to the market."]) == 100.0
    assert chrf_module.chrf(["The cat sat."], ["Yesterday I went to the market."]) < 15
    assert chrf_module.chrf([""], ["x y z"]) == 0.0
    near = chrf_module.chrf(["I went to the market yesterday."], ["Yesterday I went to the market."])
    assert 40 < near < 100  # the same words in another order score high, but not full marks


def test_grades_follow_the_bands():
    assert [grade(x) for x in (80, 62, 61.9, 55, 54.9, 48, 47.9, 38, 37.9, 0)] == ["A", "A", "B", "B", "C", "C", "D", "D", "X", "X"]
    assert grade(70, errors=5, sentences=10) is None and grade(70, errors=4, sentences=10) == "A"  # a model that refused the language has no grade
    assert [floor for floor, _ in BANDS] == sorted((floor for floor, _ in BANDS), reverse=True)


def test_the_test_set_is_parallel_credited_and_the_same_size_for_every_language():
    data = _load("quality_set.json")
    assert "CC BY-SA 4.0" in data["credit"] and len(data["reference"]) == 10 and len(data["lines"]) == 10
    assert len(data["languages"]) >= 50
    assert all(len(v["sentences"]) == 10 and v["code"] and v["flores"] for v in data["languages"].values())


def test_the_shipped_scores_match_the_catalog_and_the_bands():
    data = _load("quality.json")
    catalog = {m["id"] for m in model_files.text_models()}
    assert set(data["models"]) <= catalog and len(data["models"]) >= 2
    for model_id, languages in data["models"].items():
        assert len(languages) >= 50, model_id
        for name, row in languages.items():
            assert 0 <= row["chrf"] <= 100 and row["grade"] == grade(row["chrf"], row["errors"]), (model_id, name)
    qwen = data["models"]["qwen3-4b-instruct-mlx"]
    assert qwen["Afrikaans"]["grade"] == "A" and qwen["Tibetan"]["grade"] == "X"  # the best and the worst of the first run


def test_text_models_cover_the_languages_they_were_measured_in(monkeypatch):
    models = {m["id"]: set(m["languages"]) for m in model_files.text_models()}
    gemma, qwen = models["translategemma-4b-mlx"], models["qwen3-4b-instruct-mlx"]
    assert {"pt", "ar", "it", "es", "hi"} <= gemma and {"pt", "ar", "it", "es", "hi"} <= qwen
    assert "bo" not in gemma and "bo" not in qwen  # Tibetan graded X: not offered
    assert "ceb" in qwen and "ceb" not in gemma  # TranslateGemma refused Cebuano


def test_the_best_model_for_a_language_is_the_one_with_the_higher_score(tmp_path):
    from ocarina import quality as q  # pylint: disable=import-outside-toplevel

    both = ["qwen3-4b-instruct-mlx", "translategemma-4b-mlx"]
    assert q.best_model("pt", both) == "qwen3-4b-instruct-mlx" and q.best_model("ar", both) == "translategemma-4b-mlx"
    assert q.best_model("ar", both[:1]) is None  # nothing to compare
    assert q.best_model("bo", both) is None  # both are poor in Tibetan
    (tmp_path / "quality_local.json").write_text(json.dumps({"qwen3-4b-instruct-mlx": {"ar": {"chrf": 90.0, "grade": "A", "errors": 0}}}), encoding="utf-8")
    assert q.scores_for("qwen3-4b-instruct-mlx", str(tmp_path))["ar"]["source"] == "checked"
    assert q.best_model("ar", both, str(tmp_path)) == "qwen3-4b-instruct-mlx"  # what was measured here wins over what shipped


def test_without_a_choice_each_language_gets_the_best_installed_model(monkeypatch):
    from ocarina import translate  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(model_files, "is_installed", lambda m: True)
    auto = {"provider": "local", "localModel": "qwen3-4b-instruct-mlx", "localAuto": True}
    assert translate.settings_for(auto, "ar")["localModel"] == "translategemma-4b-mlx"
    assert translate.settings_for(auto, "pt")["localModel"] == "qwen3-4b-instruct-mlx"
    assert translate.settings_for({**auto, "localAuto": False}, "ar")["localModel"] == "qwen3-4b-instruct-mlx"  # you chose one: it stays
    assert translate.settings_for({**auto, "localModelByLanguage": {"ar": "qwen3-4b-instruct-mlx"}}, "ar")["localModel"] == "qwen3-4b-instruct-mlx"
    monkeypatch.setattr(model_files, "is_installed", lambda m: m["id"] == "qwen3-4b-instruct-mlx")
    assert translate.settings_for(auto, "ar")["localModel"] == "qwen3-4b-instruct-mlx"  # only one is here
