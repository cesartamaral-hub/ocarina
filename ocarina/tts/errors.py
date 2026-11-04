"""
Model failures in plain words.

The worker reports Python errors ("ModuleNotFoundError: No module named 'torch'"). explain() turns the ones people
can act on into a sentence; the original text is kept as the technical detail.
"""

import re

RULES = [
    (
        r"No module named '([\w.]+)'",
        lambda m: f"This model needs the Python package “{m.group(1).split('.')[0]}”, which Ocarina does not include. "
        "Models converted for MLX (the “mlx-community” ones on Hugging Face) usually work.",
    ),
    (
        r"No weight files|safetensors.*(not found|missing)|Missing key|size mismatch",
        lambda m: "The model's files are incomplete or do not match. Delete the model in Settings and download it again.",
    ),
    (
        r"No conditionals available|ref_audio",
        lambda m: "This model needs a reference voice clip, and none was usable. Pick another voice.",
    ),
    (
        r"out of memory|OutOfMemory|Insufficient Memory|kIOGPUCommandBufferCallbackErrorOutOfMemory|Cannot allocate memory",
        lambda m: "The model needs more memory than is free. Close other apps, or use a smaller model.",
    ),
    (
        r"TTS worker died|worker died or timed out",
        lambda m: "The model's process stopped, most likely because it ran out of memory or took too long.",
    ),
    (
        r"Model type .* not supported|model_type|KeyError: '(\w+)'.*(MODEL|model)",
        lambda m: "Ocarina's speech engine does not recognise this kind of model.",
    ),
    (
        r"ffmpeg",
        lambda m: "This kind of audio file needs ffmpeg, which is not available here. Use an mp3, wav or flac file, or install ffmpeg.",
    ),
    (
        r"data type 'bfloat16' not understood",
        lambda m: "This model stores its weights in a format Ocarina cannot read here.",
    ),
]


def explain(technical):
    "A plain-language sentence for a known failure, or None when the original message is all there is."
    for pattern, say in RULES:
        found = re.search(pattern, technical or "", re.IGNORECASE)
        if found:
            return say(found)
    return None
