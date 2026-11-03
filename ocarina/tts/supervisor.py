"""
Owns the TTS worker process: starts it, loads a model, synthesizes,
and restarts it if it dies. Unloading kills the worker so all of its
memory goes back to the OS.
"""

import json
import os
import subprocess
import sys
import threading


class TtsError(Exception):
    "The worker reported an error or could not be used."


class Supervisor:
    "One worker, one loaded engine, one request at a time."

    def __init__(self, engine, timeout=600):
        self.engine = engine
        self.timeout = timeout
        self._proc = None
        self._next_id = 0
        self._lock = threading.Lock()

    def _start(self):
        self._proc = subprocess.Popen(  # pylint: disable=consider-using-with
            [sys.executable, "-m", "ocarina.tts.worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTORCH_ENABLE_MPS_FALLBACK": "1"},
        )
        self._request({"op": "load", "engine": self.engine})

    def _alive(self):
        return self._proc is not None and self._proc.poll() is None

    def _request(self, req):
        self._next_id += 1
        req = {**req, "id": self._next_id}
        timer = threading.Timer(self.timeout, self._proc.kill)
        timer.start()
        try:
            self._proc.stdin.write(json.dumps(req) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
        except (BrokenPipeError, OSError) as e:
            raise TtsError("TTS worker died") from e
        finally:
            timer.cancel()
        if not line:
            raise TtsError("TTS worker died or timed out")
        resp = json.loads(line)
        if not resp["ok"]:
            raise TtsError(resp["error"])
        return resp

    def synth(self, text, lang, voice, out):
        "Synthesize one sentence to the wav at out; returns its duration in seconds."
        with self._lock:
            for attempt in (1, 2):
                try:
                    if not self._alive():
                        self._start()
                    req = {
                        "op": "synth",
                        "text": text,
                        "lang": lang,
                        "voice": voice,
                        "out": out,
                    }
                    return self._request(req)["seconds"]
                except TtsError as e:
                    # A dead worker is restarted once; a real model error is final.
                    if attempt == 2 or self._alive():
                        raise
                    self._kill()
                    print(f"TTS worker restarted: {e}", file=sys.stderr)
        raise TtsError("unreachable")

    def _kill(self):
        if self._proc is not None:
            self._proc.kill()
            self._proc.wait()
            self._proc = None

    def unload(self):
        "Stop the worker and free the model's memory."
        with self._lock:
            self._kill()
