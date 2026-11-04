"""
Speech to text on this Mac (Whisper through the model worker), for videos without captions.

    transcriber(app) -> a function (audio_path, language_code) -> text, or None when the model is not downloaded
"""

from ocarina.tts import models as model_files
from ocarina.tts.supervisor import Supervisor

TIMEOUT = 3600  # seconds for one video


def model():
    "The catalog entry of the transcription model."
    return model_files.transcriber_model()


def is_ready(app_config=None):
    "Whether a transcription model can be used now (tests with a fake engine always can)."
    if app_config is not None and "OCARINA_TTS_ENGINE" in app_config:
        return True
    found = model()
    return bool(found and model_files.is_installed(found))


def transcriber(app_config=None):
    "The function that transcribes a file, or None when there is no model to do it."
    if not is_ready(app_config):
        return None
    found = model()
    fake = app_config is not None and app_config.get("OCARINA_TTS_ENGINE") is not None
    engine = "fake-transcriber" if fake else found["engine"]

    def run(audio, language):
        supervisor = Supervisor(engine, repo=found["repositories"][0]["id"], timeout=TIMEOUT)
        try:
            return supervisor.transcribe(audio, language)
        finally:
            supervisor.unload()

    return run
