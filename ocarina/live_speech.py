"""
Reading aloud live: the Mac speaks a sentence straight from `say` (no file), and the call returns when the sentence is finished.
One sentence is spoken at a time; asking for another, or `stop()`, ends the one being spoken. The reader asks for the next sentence
when one is done, so it always knows which sentence is being read.
"""

import subprocess
import threading

from ocarina import tools

_lock = threading.Lock()
_process = None
_generation = 0  # bumped by every stop(), so a call that was cut short can tell it was


def stop():
    "End the sentence being spoken, if any."
    global _generation  # pylint: disable=global-statement
    with _lock:
        _generation += 1
        proc = _process
    if proc and proc.poll() is None:
        proc.terminate()


def speak(text, voice, words_per_minute=None):
    "Speak `text` with the Mac voice `voice` and wait. True when it was said to the end, False when stop() or another sentence cut it short."
    global _process  # pylint: disable=global-statement
    stop()  # one at a time
    command = [tools.find("say"), "-v", voice]
    if words_per_minute:
        command += ["-r", str(int(words_per_minute))]
    with _lock:
        mine = _generation
        proc = subprocess.Popen(command + ["--", text], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # pylint: disable=consider-using-with
        _process = proc
    code = proc.wait()
    with _lock:
        if _process is proc:
            _process = None
        cut = _generation != mine
    return code == 0 and not cut
