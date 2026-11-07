"""
How long things take, for the "about 3 min" shown before a job starts. A model that was tried here (Settings -> Models) is rated by how long it
took; any other by the catalog's speed bars (1 slowest to 4 fastest). Online translation is taken as steady.

    seconds_per_audio_second(datapath, model)   seconds of work for one second of speech
    seconds_per_sentence(datapath, model)       seconds to translate one sentence with a local model
    ONLINE_SECONDS_PER_SENTENCE                 Google Translate, MyMemory and DeepL
"""

from ocarina import model_check
from ocarina.tts import models as model_files

ONLINE_SECONDS_PER_SENTENCE = 0.6
MAC_VOICE_SECONDS_PER_AUDIO_SECOND = 0.25  # 17 Dutch sentences took 16 s here
_BY_SPEED_AUDIO = {4: 0.2, 3: 0.5, 2: 1.1, 1: 2.0}
_BY_SPEED_SENTENCE = {4: 0.7, 3: 2.0, 2: 5.0, 1: 10.0}


def _level(model):
    return min(4, max(1, int(model.get("speed") or 2)))


def seconds_per_audio_second(datapath, model):
    if model_files.is_builtin(model):
        return MAC_VOICE_SECONDS_PER_AUDIO_SECOND
    check = model_check.result_for(datapath, model)
    if check and check.get("ok") and check.get("secondsPerSecondOfAudio"):
        return check["secondsPerSecondOfAudio"]
    return _BY_SPEED_AUDIO[_level(model)]


def seconds_per_sentence(datapath, model):
    check = model_check.result_for(datapath, model)
    if check and check.get("ok") and check.get("secondsPerSentence"):
        return check["secondsPerSentence"]
    return _BY_SPEED_SENTENCE[_level(model)]
