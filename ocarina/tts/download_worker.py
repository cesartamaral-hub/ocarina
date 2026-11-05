"""
Downloads the files of one model in a process of its own (see models.download), so that cancelling stops it at once.

Reads one line of JSON, the catalog entry of the model, from standard input; writes lines of JSON to the process that started it:
{"done": bytes, "total": bytes} as the files come, then {"ok": true} or {"error": message}. Files already downloaded are kept, and a
file that was being fetched is continued the next time.
"""

import json
import os
import sys
import time

from ocarina.tts import models


def main():
    "Download the model named on standard input."
    model = json.loads(sys.stdin.readline())
    out = os.fdopen(os.dup(1), "w", encoding="utf-8")
    os.dup2(2, 1)  # stray prints from libraries must not corrupt the protocol
    last = {"at": 0.0}

    def say(message):
        out.write(json.dumps(message) + "\n")
        out.flush()

    def progress(done, total):
        now = time.time()
        if now - last["at"] >= 0.2 or done >= total:  # not every chunk
            last["at"] = now
            say({"done": done, "total": total})

    try:
        models.download_here(model, progress)
        say({"ok": True})
    except Exception as e:  # pylint: disable=broad-exception-caught
        say({"error": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    main()
