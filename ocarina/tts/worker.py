"""
TTS worker process.

Runs the model in its own process so a crash or out-of-memory kill
only takes down this worker. Speaks line-delimited JSON on the
original stdout; anything the model libraries print goes to stderr.

Requests:  {"id": 1, "op": "load", "engine": "mlx-chatterbox", "repo": "owner/name" or null}
           {"id": 4, "op": "complete", "system": ..., "user": ..., "max_tokens": 300}   (text engines)
           {"id": 2, "op": "synth", "text": ..., "lang": ..., "voice": path, "out": path}
           {"id": 5, "op": "align", "audio": path, "offset": 0.0, "length": 240.0, "text": ...}   (aligner engine)
           {"id": 6, "op": "duration", "audio": path}
           {"id": 7, "op": "onsets", "audio": path, "intervals": [[start, end], ...]}
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
MLX_AUDIO8_REPO = "nativ-community/Audio8-TTS-Realistic-0.6b-bf16"
MLX_LM_REPO = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
TAIL_SECONDS, TAIL_PAUSE, TAIL_LOOKBACK = 0.8, 0.3, 10  # a sound this short (and 100 ms of sound before it), then a pause this long, is the end of the sentence before
MLX_ALIGNER_REPO = "mlx-community/Qwen3-ForcedAligner-0.6B-8bit"


def _next_sound(loud_frames, first, last, at_least=1):
    "Index of the first 10 ms frame in first..last that starts at least `at_least` loud frames in a row, or None."
    run = 0
    for i in range(first, min(last, len(loud_frames))):
        run = run + 1 if loud_frames[i] else 0
        if run >= at_least:
            return i - run + 1
    return None


def _end_of_run(loud_frames, at, last, gap=6):
    "Index just after the sound that starts at `at` (pauses shorter than `gap` frames stay inside it)."
    i, quiet = at, 0
    while i < min(last, len(loud_frames)) and quiet <= gap:
        quiet = 0 if loud_frames[i] else quiet + 1
        i += 1
    return i - quiet


def first_speech(loud_frames, first, last):
    """
    Index of the 10 ms frame where speech starts in first..last, or None. When there is sound right at `first` and
    also just before it, `first` lies at the end of the sentence before (the aligner can pile words onto it): a short
    stretch like that, followed by a pause, is skipped, and speech starts after the pause. A start that lies in silence
    simply moves to the first sound.
    """
    at = _next_sound(loud_frames, first, last)
    if at is not None and at == first and loud_frames[max(first - TAIL_LOOKBACK, 0) : first].any():
        run_end = _end_of_run(loud_frames, at, last)
        after = _next_sound(loud_frames, run_end, last, at_least=5)  # a click in the pause is not the next sentence
        if (run_end - at) * 0.01 <= TAIL_SECONDS and after is not None and (after - run_end) * 0.01 >= TAIL_PAUSE:
            return after
    return at


class FakeEngine:
    "Writes a short tone; used by tests so they need no model."

    sample_rate = 24000

    def __init__(self, repo=None):
        self.repo = repo

    def complete(self, system, user, max_tokens=300, style=None, source=None, target=None, text=None):  # pylint: disable=unused-argument,too-many-arguments,too-many-positional-arguments
        "A predictable stand-in for a language model: echoes the sentence, so tests can see what was sent."
        if style == "translategemma":
            return f"[fake {style} {source}>{target}] {text}"
        return "[fake translation] " + user.split("\n", 1)[-1]

    def synth(self, text, lang, voice, out, ref_text=None):  # pylint: disable=unused-argument
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


class FakeAlignerEngine:
    "Stands in for the aligner in tests: every word takes 0.3 s, and the audio is 60 s long."

    sample_rate = None

    def __init__(self, repo=None):
        self.repo = repo

    def duration(self, audio):  # pylint: disable=unused-argument
        "Seconds of audio in the file."
        return 60.0

    def align(self, audio, offset, length, text):  # pylint: disable=unused-argument
        "Words with start and end times (seconds from the start of the file)."
        return [[w, round(offset + i * 0.3, 3), round(offset + i * 0.3 + 0.25, 3)] for i, w in enumerate(text.split())]

    def onsets(self, audio, intervals):  # pylint: disable=unused-argument
        "Where sound begins in each interval: here, where it begins."
        return [interval[0] for interval in intervals]


class MlxAlignerEngine:
    "Qwen3 forced aligner via mlx-audio: given a recording and what is said in it, finds when each word is spoken."

    sample_rate = None

    def __init__(self, repo=None):
        # pylint: disable=import-outside-toplevel
        from mlx_audio.stt import load

        self.model = load(repo or MLX_ALIGNER_REPO)
        self._path, self._audio = None, None
        self._env_path, self._env = None, None

    def _load(self, path):
        "The whole file as mono 16 kHz samples (kept for the next window of the same file)."
        # pylint: disable=import-outside-toplevel
        import numpy as np
        from mlx_audio.stt.utils import load_audio

        if path != self._path:
            self._audio, self._path = np.array(load_audio(path, sr=self.model.sample_rate)), path
        return self._audio

    def duration(self, audio):
        "Seconds of audio in the file."
        return len(self._load(audio)) / self.model.sample_rate

    def _envelope(self, path):
        "Loudness of the file in 10 ms steps, and the level above which something is being said (kept for the file)."
        # pylint: disable=import-outside-toplevel
        import numpy as np

        if self._env_path != path:
            samples = self._load(path)
            hop = int(0.01 * self.model.sample_rate)
            n = len(samples) // hop
            loud = np.sqrt((samples[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
            loud = np.convolve(loud, np.ones(2) / 2, mode="same")
            # Well above the room's own noise, and well below the narrator's normal level.
            self._env, self._env_path = (loud, max(0.02 * float(loud.max()), 4 * float(np.percentile(loud, 10)))), path
        return self._env

    def onsets(self, audio, intervals):
        """
        Where speech really begins in each (start, end) interval: the first moment that is loud enough. The aligner puts
        a word's start where the one before it ended, and after a long pause it can pile words onto the end of the last
        sentence or onto silence, so a sentence would start while the narrator is quiet or still on the one before. A
        short burst of sound followed by a long pause is that sentence's tail: skip it, to the sound after the pause.
        """
        # pylint: disable=import-outside-toplevel
        loud, level = self._envelope(audio)
        loud_frames = loud >= level
        found = []
        for start, end in intervals:
            first = max(int(start / 0.01), 0)
            last = max(int(end / 0.01), first + 1)
            at = first_speech(loud_frames, first, last)
            found.append(round(at * 0.01, 3) if at is not None else start)
        return found

    def align(self, audio, offset, length, text):
        "Align text to the part of the file that starts at offset and lasts length seconds; times are absolute."
        rate = self.model.sample_rate
        samples = self._load(audio)[int(offset * rate) : int((offset + length) * rate)]
        # The model ignores the language it is told for languages it does not list, and does fine on them.
        result = self.model.generate(audio=samples, text=text, language="English")
        return [[i.text, round(offset + i.start_time, 3), round(offset + i.end_time, 3)] for i in result]


class FakeTranscriberEngine:
    "Stands in for Whisper in tests."

    sample_rate = None

    def __init__(self, repo=None):
        self.repo = repo

    def transcribe(self, audio, language):  # pylint: disable=unused-argument
        "What was said."
        return f"Gehoord ({language}).", [[0.0, f"Gehoord ({language})."]]


class MlxWhisperEngine:
    "Whisper via mlx-audio: the text of a recording."

    sample_rate = None

    def __init__(self, repo=None):
        from mlx_audio.stt import load  # pylint: disable=import-outside-toplevel

        self.model = load(repo)

    def transcribe(self, audio, language):
        "(text, [[start seconds, text], ...]) of the file, in the language when it is known (else Whisper finds it)."
        result = self.model.generate(audio, language=language, return_timestamps=True, verbose=None)
        segments = [[round(float(s["start"]), 2), s["text"].strip()] for s in (result.segments or []) if s["text"].strip()]
        return result.text.strip(), segments


class MlxChatterboxEngine:
    "Chatterbox Multilingual v3 via mlx-audio."

    def __init__(self, repo=None):
        # pylint: disable=import-outside-toplevel
        from mlx_audio.tts.utils import load_model

        self.model = load_model(repo or MLX_CHATTERBOX_REPO)
        self.sample_rate = self.model.sample_rate

    def synth(self, text, lang, voice, out, ref_text=None):  # pylint: disable=unused-argument
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


class MlxLmEngine:
    "A small language model via mlx-lm, used to translate sentences on this Mac (no speech)."

    sample_rate = None

    def __init__(self, repo=None):
        # pylint: disable=import-outside-toplevel
        from mlx_lm import load

        self.model, self.tokenizer = load(repo or MLX_LM_REPO)

    def complete(self, system, user, max_tokens=300, style=None, source=None, target=None, text=None):  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """
        The model's answer (greedy, so the same sentence gives the same answer). Most models get a system and a user
        message; a model whose chat template has no system role (Gemma) gets the instruction in the user message;
        TranslateGemma wants the text with the two language codes instead of any instruction.
        """
        # pylint: disable=import-outside-toplevel
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        if style == "translategemma":
            messages = [{"role": "user", "content": [{"type": "text", "source_lang_code": source, "target_lang_code": target, "text": text}]}]
        else:
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        try:
            prompt = self._prompt(messages)
        except Exception:  # pylint: disable=broad-exception-caught
            if style == "translategemma":
                raise
            prompt = self._prompt([{"role": "user", "content": f"{system}\n\n{user}"}])
        return generate(self.model, self.tokenizer, prompt=prompt, max_tokens=max_tokens, sampler=make_sampler(temp=0.0)).strip()

    def _prompt(self, messages):
        return self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False, enable_thinking=False)


class MlxAudio8Engine:
    """
    Audio8 TTS via mlx-audio. It imitates a voice only when given the words spoken in the clip
    (ref_text); without that it speaks in its own voice.
    """

    def __init__(self, repo=None):
        # pylint: disable=import-outside-toplevel
        from mlx_audio.tts.utils import load_model

        self.model = load_model(repo or MLX_AUDIO8_REPO)
        self.sample_rate = self.model.sample_rate

    def synth(self, text, lang, voice, out, ref_text=None):  # pylint: disable=unused-argument
        "Generate speech for one sentence and write it to out as wav; the language follows the text."
        # pylint: disable=import-outside-toplevel
        import numpy as np
        import soundfile as sf

        clone = {"ref_audio": voice, "ref_text": ref_text} if voice and ref_text else {}
        chunks = [np.array(r.audio) for r in self.model.generate(text=text, **clone)]
        wav = np.concatenate(chunks)
        sf.write(out, wav, self.sample_rate)
        return len(wav) / self.sample_rate


ENGINES = {"fake": FakeEngine, "fake-transcriber": FakeTranscriberEngine, "mlx-whisper": MlxWhisperEngine, "fake-aligner": FakeAlignerEngine, "mlx-aligner": MlxAlignerEngine, "mlx-chatterbox": MlxChatterboxEngine, "mlx-audio8": MlxAudio8Engine, "mlx-lm": MlxLmEngine}


def _handle(engine, req):
    "Run one request; returns (response fields, engine)."
    op = req["op"]
    if op == "load":
        engine = ENGINES[req["engine"]](req.get("repo"))
        return {"sample_rate": engine.sample_rate}, engine
    if op == "complete":
        if engine is None:
            raise RuntimeError("No model loaded")
        extra = {k: req.get(k) for k in ("style", "source", "target", "text")}
        return {"text": engine.complete(req["system"], req["user"], req.get("max_tokens", 300), **extra)}, engine
    if op == "transcribe":
        text, segments = engine.transcribe(req["audio"], req.get("language"))
        return {"text": text, "segments": segments}, engine
    if op == "duration":
        return {"seconds": engine.duration(req["audio"])}, engine
    if op == "onsets":
        return {"starts": engine.onsets(req["audio"], req["intervals"])}, engine
    if op == "align":
        return {"words": engine.align(req["audio"], req["offset"], req["length"], req["text"])}, engine
    if op == "synth":
        if engine is None:
            raise RuntimeError("No model loaded")
        os.makedirs(os.path.dirname(req["out"]), exist_ok=True)
        root, ext = os.path.splitext(req["out"])
        tmp = f"{root}.part{ext}"  # keep the extension: soundfile picks the format from it
        seconds = engine.synth(req["text"], req["lang"], req["voice"], tmp, req.get("ref_text"))
        os.replace(tmp, req["out"])
        return {"seconds": seconds}, engine
    raise ValueError(f"Unknown op {op}")


def main():
    "Serve requests until quit or stdin closes."
    from ocarina.tts import mlx_compat  # pylint: disable=import-outside-toplevel

    mlx_compat.install()  # before any model library imports safe_open: bfloat16 weights then load without PyTorch
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
