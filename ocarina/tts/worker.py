"""
TTS worker process.

Runs the model in its own process so a crash or out-of-memory kill
only takes down this worker. Speaks line-delimited JSON on the
original stdout; anything the model libraries print goes to stderr.

Requests:  {"id": 1, "op": "load", "engine": "mlx-chatterbox", "repo": "owner/name" or null}
           {"id": 2, "op": "synth", "text": ..., "lang": ..., "voice": path, "out": path}
           {"id": 3, "op": "quit"}
Responses: {"id": 1, "ok": true, ...} or {"id": 1, "ok": false, "error": "..."}
"""

import json
import math
import os
import struct
import sys
import traceback
import wave

MLX_CHATTERBOX_REPO = "mlx-community/chatterbox-multilingual-v3"


class FakeEngine:
    "Writes a short tone; used by tests so they need no model."

    sample_rate = 24000

    def __init__(self, repo=None):
        self.repo = repo

    def synth(self, text, lang, voice, out):  # pylint: disable=unused-argument
        "Write a tone whose length depends on the text length."
        n = int(self.sample_rate * 0.02 * max(len(text), 1))
        with wave.open(out, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.sample_rate)
            w.writeframes(
                b"".join(
                    struct.pack("<h", int(8000 * math.sin(i / 20))) for i in range(n)
                )
            )
        return n / self.sample_rate


class MlxChatterboxEngine:
    "Chatterbox Multilingual v3 via mlx-audio."

    def __init__(self, repo=None):
        # pylint: disable=import-outside-toplevel
        from mlx_audio.tts.utils import load_model

        self.model = load_model(repo or MLX_CHATTERBOX_REPO)
        self.sample_rate = self.model.sample_rate

    def synth(self, text, lang, voice, out):
        "Generate speech for one sentence and write it to out as wav."
        # pylint: disable=import-outside-toplevel
        import numpy as np
        import soundfile as sf

        chunks = [
            np.array(r.audio)
            for r in self.model.generate(text=text, lang_code=lang, ref_audio=voice)
        ]
        wav = np.concatenate(chunks)
        sf.write(out, wav, self.sample_rate)
        return len(wav) / self.sample_rate


ENGINES = {"fake": FakeEngine, "mlx-chatterbox": MlxChatterboxEngine}


def _handle(engine, req):
    "Run one request; returns (response fields, engine)."
    op = req["op"]
    if op == "load":
        engine = ENGINES[req["engine"]](req.get("repo"))
        return {"sample_rate": engine.sample_rate}, engine
    if op == "synth":
        if engine is None:
            raise RuntimeError("No model loaded")
        os.makedirs(os.path.dirname(req["out"]), exist_ok=True)
        root, ext = os.path.splitext(req["out"])
        tmp = f"{root}.part{ext}"  # keep the extension: soundfile picks the format from it
        seconds = engine.synth(req["text"], req["lang"], req["voice"], tmp)
        os.replace(tmp, req["out"])
        return {"seconds": seconds}, engine
    raise ValueError(f"Unknown op {op}")


def main():
    "Serve requests until quit or stdin closes."
    proto_out = os.fdopen(os.dup(1), "w", encoding="utf-8")
    os.dup2(2, 1)  # stray prints from libraries must not corrupt the protocol
    engine = None
    for line in sys.stdin:
        req = json.loads(line)
        if req["op"] == "quit":
            break
        try:
            fields, engine = _handle(engine, req)
            resp = {"id": req["id"], "ok": True, **fields}
        except Exception as e:  # pylint: disable=broad-exception-caught
            traceback.print_exc()  # stderr: the parent only gets the one-line message
            resp = {"id": req["id"], "ok": False, "error": f"{type(e).__name__}: {e}"}
        proto_out.write(json.dumps(resp) + "\n")
        proto_out.flush()


if __name__ == "__main__":
    main()
