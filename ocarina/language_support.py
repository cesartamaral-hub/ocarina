"""
What Ocarina can do for a language: meanings, an AI voice, translation on this Mac, audio sync and a Mac voice.

    support(name, datapath)  ->  {"language", "code", "level", "meanings", "aiVoice", "translation", "audioSync", "macVoice"}

Each feature is "ready", "download" (a model that covers the language exists but is not downloaded), "online" (meanings only: the
dictionaries on this Mac do not have it, the internet is asked) or "none". The level is "full" when meanings are on this Mac and there is
a voice model and a translation model for the language, otherwise "basic": reading, word lists and the Mac voice still work.
"""

from ocarina import pronounce, translate
from ocarina.dictionaries import registry
from ocarina.tts import models as model_files


def _models_state(kind_models, code):
    covering = [m for m in kind_models if code in m.get("languages", [])]
    if not covering:
        return "none"
    return "ready" if any(model_files.is_installed(m) for m in covering) else "download"


def support(name, datapath):
    "The features available for a language, by its Lute name."
    code = translate.code_for(name)
    if code is None:
        return {"language": name, "code": None, "level": "basic", "meanings": "online", "aiVoice": "none", "translation": "none", "audioSync": "none", "macVoice": "none"}
    aligners = [m for m in model_files.load_catalog() if model_files.kind_of(m) == "aligner"]
    found = {
        "meanings": "ready" if registry.active(datapath, code) else "online",
        "aiVoice": _models_state(model_files.speech_models(), code),
        "translation": _models_state(model_files.text_models(), code),
        "audioSync": _models_state(aligners, code),
        "macVoice": "ready" if pronounce.mac_voices(code) else "none",
    }
    full = found["meanings"] == "ready" and found["aiVoice"] != "none" and found["translation"] != "none"
    return {"language": name, "code": code, "level": "full" if full else "basic", **found}
