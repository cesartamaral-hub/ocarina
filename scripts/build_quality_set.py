"""
Builds the small test set the translation quality scores use: ten sentences per language from FLORES-200 (devtest), with their English
translations as the reference. FLORES-200 is CC BY-SA 4.0 (NLLB Team, Meta AI), so the file this makes is CC BY-SA 4.0 too, credited in NOTICE.md.

    python scripts/build_quality_set.py <folder with flores200_dataset> [out.json]

The same ten sentence numbers are used for every language (the sets are parallel), picked with a fixed seed among English sentences of
moderate length, so the set can be rebuilt exactly.
"""

import json
import os
import random
import sys

SEED = 20261106
PER_LANGUAGE = 10
# Ocarina's language name -> (code Ocarina and the models use, FLORES-200 code). Portuguese is FLORES's single Portuguese (Brazilian).
LANGUAGES = {
    "Afrikaans": ("af", "afr_Latn"), "Albanian": ("sq", "als_Latn"), "Amharic": ("am", "amh_Ethi"), "Arabic": ("ar", "arb_Arab"),
    "Armenian": ("hy", "hye_Armn"), "Azerbaijani": ("az", "azj_Latn"), "Basque": ("eu", "eus_Latn"), "Belarusian": ("be", "bel_Cyrl"),
    "Bengali": ("bn", "ben_Beng"), "Bosnian": ("bs", "bos_Latn"), "Bulgarian": ("bg", "bul_Cyrl"), "Catalan": ("ca", "cat_Latn"),
    "Cebuano": ("ceb", "ceb_Latn"), "Croatian": ("hr", "hrv_Latn"), "Czech": ("cs", "ces_Latn"), "Danish": ("da", "dan_Latn"),
    "Dutch": ("nl", "nld_Latn"), "Esperanto": ("eo", "epo_Latn"), "Estonian": ("et", "est_Latn"), "Farsi": ("fa", "pes_Arab"),
    "Finnish": ("fi", "fin_Latn"), "French": ("fr", "fra_Latn"), "Galician": ("gl", "glg_Latn"), "Georgian": ("ka", "kat_Geor"),
    "German": ("de", "deu_Latn"), "Greek": ("el", "ell_Grek"), "Hebrew": ("he", "heb_Hebr"), "Hindi": ("hi", "hin_Deva"),
    "Hungarian": ("hu", "hun_Latn"), "Icelandic": ("is", "isl_Latn"), "Indonesian": ("id", "ind_Latn"), "Italian": ("it", "ita_Latn"),
    "Japanese": ("ja", "jpn_Jpan"), "Kazakh": ("kk", "kaz_Cyrl"), "Khmer": ("km", "khm_Khmr"), "Latvian": ("lv", "lvs_Latn"),
    "Lithuanian": ("lt", "lit_Latn"), "Macedonian": ("mk", "mkd_Cyrl"), "Mandarin Chinese": ("zh", "zho_Hans"), "Norwegian": ("no", "nob_Latn"),
    "Polish": ("pl", "pol_Latn"), "Brazilian Portuguese": ("pt", "por_Latn"), "Punjabi": ("pa", "pan_Guru"), "Romanian": ("ro", "ron_Latn"),
    "Russian": ("ru", "rus_Cyrl"), "Serbian": ("sr", "srp_Cyrl"), "Slovak": ("sk", "slk_Latn"), "Slovene": ("sl", "slv_Latn"),
    "Spanish": ("es", "spa_Latn"), "Swahili": ("sw", "swh_Latn"), "Swedish": ("sv", "swe_Latn"), "Thai": ("th", "tha_Thai"),
    "Tibetan": ("bo", "bod_Tibt"), "Turkish": ("tr", "tur_Latn"), "Ukrainian": ("uk", "ukr_Cyrl"), "Vietnamese": ("vi", "vie_Latn"),
}


def read(folder, flores):
    with open(os.path.join(folder, "devtest", f"{flores}.devtest"), encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def build(folder):
    english = read(folder, "eng_Latn")
    eligible = [i for i, s in enumerate(english) if 70 <= len(s) <= 140]
    chosen = sorted(random.Random(SEED).sample(eligible, PER_LANGUAGE))
    languages = {}
    for name, (code, flores) in LANGUAGES.items():
        lines = read(folder, flores)
        languages[name] = {"code": code, "flores": flores, "sentences": [lines[i] for i in chosen]}
    return {
        "credit": "FLORES-200 devtest (NLLB Team, Meta AI), CC BY-SA 4.0: https://github.com/facebookresearch/flores",
        "seed": SEED,
        "lines": chosen,
        "reference": [english[i] for i in chosen],
        "languages": languages,
    }


if __name__ == "__main__":
    root = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "ocarina", "quality", "quality_set.json")
    data = build(root)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"{len(data['languages'])} languages, {PER_LANGUAGE} sentences each -> {out}")
