"""
A small language model that runs on this Mac, used to translate sentences without internet.

It lives in the same kind of worker process as the voices, so a crash or running out of memory cannot take the app
down. It stays loaded for a few minutes after use (so translating a page of sentences is quick) and is then unloaded
to give its memory back.
"""

import threading

from ocarina.tts.supervisor import Supervisor

IDLE_SECONDS = 300


class LocalModel:
    "One text model, loaded on first use and unloaded after a quiet spell."

    def __init__(self, idle_seconds=IDLE_SECONDS):
        self.idle_seconds = idle_seconds
        self._lock = threading.Lock()
        self._supervisor = None
        self._model_id = None
        self._timer = None

    def complete(self, model, system, user, engine=None, max_tokens=300, **extra):
        "The model's answer; model is a catalog entry, engine overrides its engine (tests use 'fake')."
        with self._lock:
            if self._supervisor is None or self._model_id != model["id"]:
                self._stop()
                self._supervisor = Supervisor(engine or model["engine"], repo=model["repositories"][0]["id"])
                self._model_id = model["id"]
            try:
                return self._supervisor.complete(system, user, max_tokens, **extra)
            finally:
                self._arm_timer()

    def unload(self):
        "Stop the worker and give its memory back."
        with self._lock:
            self._stop()

    def _stop(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if self._supervisor:
            self._supervisor.unload()
            self._supervisor, self._model_id = None, None

    def _arm_timer(self):
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self.idle_seconds, self.unload)
        self._timer.daemon = True
        self._timer.start()


local_model = LocalModel()
