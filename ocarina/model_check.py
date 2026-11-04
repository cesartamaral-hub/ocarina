"""
Trying a model: load it in a worker and use it once, so a model that cannot work here is found out right away
(with a plain reason) and not in the middle of voicing a book.

Results are kept in <data folder>/model_checks.json, per model and revision. A speech model is asked for a short
sentence twice (the first call includes loading, the second shows the real speed); a text model for one translation; an aligner for placing three words.
"""

import json
import os
import time

from ocarina.audio_sync import aligner_engine
from ocarina.localllm import LocalModel
from ocarina.tts import models as model_files
from ocarina.tts import voices
from ocarina.tts.errors import explain
from ocarina.tts.supervisor import Supervisor

FILE = "model_checks.json"


def _path(datapath):
    return os.path.join(datapath, FILE)


def _load(datapath):
    try:
        with open(_path(datapath), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(datapath, data):
    os.makedirs(datapath, exist_ok=True)
    tmp = _path(datapath) + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _path(datapath))


def _revision(model):
    return model["repositories"][0]["revision"]


def result_for(datapath, model):
    "The last check of this model, or None if it was never tried (or a different revision was)."
    found = _load(datapath).get(model["id"])
    return found if found and found.get("revision") == _revision(model) else None


def failing_ids(datapath):
    "Ids of models whose last check failed."
    return {mid for mid, r in _load(datapath).items() if not r.get("ok")}


def forget(datapath, model_id):
    "Drop a model's result (its files were deleted)."
    data = _load(datapath)
    if data.pop(model_id, None) is not None:
        _save(datapath, data)


def _try_speech(datapath, model, engine):
    language = next((c for c in model.get("languages", []) if c in voices.SAMPLE_TEXT), "nl")
    voice_id = voices.default_voice_id(language)
    voice = voices.path_of(datapath, voice_id)
    ref_text = voices.transcript_of(datapath, voice_id)
    out = os.path.join(datapath, "temp", f"check_{model['id']}.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    supervisor = Supervisor(engine or model["engine"], repo=model["repositories"][0]["id"], timeout=1800)
    try:
        started = time.time()
        supervisor.synth(voices.SAMPLE_TEXT[language], language, voice, out, ref_text)
        first = time.time() - started
        started = time.time()
        audio_seconds = supervisor.synth(voices.SAMPLE_TEXT[language], language, voice, out, ref_text)
        second = time.time() - started
    finally:
        supervisor.unload()
        if os.path.exists(out):
            os.remove(out)
    return {"language": language, "loadSeconds": round(max(first - second, 0), 1), "secondsPerSecondOfAudio": round(second / audio_seconds, 2) if audio_seconds else None}


def _try_text(model, engine):
    runner = LocalModel(idle_seconds=1)
    try:
        started = time.time()
        extra = {"style": "translategemma", "source": "nl", "target": "en", "text": "Goedemorgen, hoe gaat het met je?"} if model.get("prompt") == "translategemma" else {}
        answer = runner.complete(model, "Reply with the English translation only.", "Dutch sentence:\nGoedemorgen, hoe gaat het met je?", engine=engine, **extra)
        if not answer.strip():
            raise RuntimeError("The model gave no answer.")
        return {"secondsPerSentence": round(time.time() - started, 1)}
    finally:
        runner.unload()


def _try_aligner(datapath, model, engine):
    "Load the aligner and place three words on a second and a half of tone (it has no use for the sound being speech)."
    import numpy as np  # pylint: disable=import-outside-toplevel
    import soundfile as sf  # pylint: disable=import-outside-toplevel

    path = os.path.join(datapath, "temp", f"check_{model['id']}.wav")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sf.write(path, (0.1 * np.sin(np.arange(24000) / 8)).astype("float32"), 16000)
    supervisor = Supervisor(aligner_engine(engine or model["engine"]), repo=model["repositories"][0]["id"], timeout=1800)
    try:
        started = time.time()
        words = supervisor.align(path, 0.0, 1.5, "een twee drie")
        if len(words) != 3:
            raise RuntimeError("The model did not place the words.")
        return {"seconds": round(time.time() - started, 1)}
    finally:
        supervisor.unload()
        if os.path.exists(path):
            os.remove(path)


def check_model(datapath, model, engine=None):
    "Try the model once; stores and returns {ok, ...numbers} or {ok: False, error, detail}."
    try:
        kind = model_files.kind_of(model)
        if kind == "text":
            numbers = _try_text(model, engine)
        elif kind == "aligner":
            numbers = _try_aligner(datapath, model, engine)
        else:
            numbers = _try_speech(datapath, model, engine)
        result = {"ok": True, **numbers}
    except Exception as e:  # pylint: disable=broad-exception-caught
        technical = f"{type(e).__name__}: {e}"
        result = {"ok": False, "error": explain(technical) or technical, "detail": technical}
    result.update({"revision": _revision(model), "at": int(time.time())})
    data = _load(datapath)
    data[model["id"]] = result
    _save(datapath, data)
    return result
