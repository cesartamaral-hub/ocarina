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
import weakref

from ocarina import hardware, tools


TOOL_DIRS = ("/opt/homebrew/bin", "/usr/local/bin")  # where Homebrew puts ffmpeg; an app opened from the Dock does not have them on its PATH


def path_with_tools(path=None):
    "PATH with the app's own tools first (ffmpeg) and the folders of Homebrew's tools added at the end."
    parts = [p for p in (path if path is not None else os.environ.get("PATH", "")).split(os.pathsep) if p]
    own = [d for d in (tools.bundled_dir(),) if d and d not in parts]
    return os.pathsep.join(own + parts + [d for d in TOOL_DIRS if d not in parts])


def worker_command_and_env(module="ocarina.tts.worker", offline=True):
    """
    Command and environment that start a worker process.

    Inside a py2app bundle the bare interpreter (sys.executable, in
    UTF-8 mode) is used with the bundle's library folders on its path.
    The app's own launcher is not used: it starts Python in ASCII mode,
    which breaks libraries that read files without an encoding.
    """
    # HF_HUB_OFFLINE: the model worker never downloads; the download manager does that (offline=False, for its own process).
    env = {
        **os.environ,
        "PYTORCH_ENABLE_MPS_FALLBACK": "1",
        "PYTHONUTF8": "1",
        "PATH": path_with_tools(),
    }
    if offline:
        env["HF_HUB_OFFLINE"] = "1"
    cache_mb = hardware.mlx_cache_mb()
    if cache_mb:
        env["OCARINA_MLX_CACHE_MB"] = str(cache_mb)  # see worker.limit_mlx_cache
    if getattr(sys, "frozen", False):
        lib = os.path.join(os.environ["RESOURCEPATH"], "lib")
        env["PYTHONPATH"] = os.pathsep.join(
            [
                os.path.join(lib, "python3.12"),
                os.path.join(lib, "python312.zip"),
                os.path.join(lib, "python3.12", "lib-dynload"),
            ]
        )
    return [sys.executable, "-m", module], env


class TtsError(Exception):
    "The worker reported an error or could not be used."


_started = weakref.WeakSet()  # supervisors that have started a worker (the app has a few: voices, the translation model, transcription)


def release_idle(keep):
    "Stop the workers of the other supervisors that are not in the middle of a request, so their models give memory back. Returns how many."
    stopped = 0
    for other in list(_started):
        if other is keep or not other._alive():  # pylint: disable=protected-access
            continue
        if other._lock.acquire(blocking=False):  # pylint: disable=protected-access
            try:
                other._kill()  # pylint: disable=protected-access
                stopped += 1
            finally:
                other._lock.release()  # pylint: disable=protected-access
    return stopped


class Supervisor:
    "One worker, one loaded engine, one request at a time."

    def __init__(self, engine, timeout=600, repo=None):
        self.engine = engine
        self.repo = repo  # Hugging Face repo of the model to load; None = the engine's default
        self.timeout = timeout
        self._proc = None
        self._next_id = 0
        self._lock = threading.Lock()

    def _start(self):
        if hardware.one_at_a_time():
            release_idle(self)  # a Mac with 8 or 16 GB keeps one model in memory, not two
        _started.add(self)
        command, env = worker_command_and_env()
        self._proc = subprocess.Popen(  # pylint: disable=consider-using-with
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env
        )
        self._request({"op": "load", "engine": self.engine, "repo": self.repo})

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

    def complete(self, system, user, max_tokens=300, **extra):
        "Ask a text model (engine mlx-lm) a question; returns its answer. extra: style, source, target, text (see worker)."
        with self._lock:
            for attempt in (1, 2):
                try:
                    if not self._alive():
                        self._start()
                    return self._request({"op": "complete", "system": system, "user": user, "max_tokens": max_tokens, **extra})["text"]
                except TtsError as e:
                    if attempt == 2 or self._alive():
                        raise
                    self._kill()
                    print(f"Text worker restarted: {e}", file=sys.stderr)
        raise TtsError("unreachable")

    def _ask(self, req):
        "One request with the same restart rule as the others: a dead worker is restarted once, a model error is final."
        with self._lock:
            for attempt in (1, 2):
                try:
                    if not self._alive():
                        self._start()
                    return self._request(req)
                except TtsError as e:
                    if attempt == 2 or self._alive():
                        raise
                    self._kill()
                    print(f"Worker restarted: {e}", file=sys.stderr)
        raise TtsError("unreachable")

    def transcribe(self, audio, language=None):
        "(text, [[start, text], ...]) said in a file (whisper engine)."
        got = self._ask({"op": "transcribe", "audio": audio, "language": language})
        return got["text"], got["segments"]

    def duration(self, audio):
        "Seconds of audio in a file (aligner engine)."
        return self._ask({"op": "duration", "audio": audio})["seconds"]

    def onsets(self, audio, intervals):
        "Where sound begins in each (start, end) interval of a file (aligner engine)."
        return self._ask({"op": "onsets", "audio": audio, "intervals": intervals})["starts"]

    def align(self, audio, offset, length, text):
        "Word times for the text spoken in part of a file (aligner engine): [[word, start, end], ...]."
        return self._ask({"op": "align", "audio": audio, "offset": offset, "length": length, "text": text})["words"]

    def synth(self, text, lang, voice, out, ref_text=None):
        """
        Synthesize one sentence to the wav at out; returns its duration in seconds.
        ref_text: the words spoken in the voice clip (only some engines need it).
        """
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
                        "ref_text": ref_text,
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
