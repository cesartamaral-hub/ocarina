"""
Reading safetensors without PyTorch.

Some models (Higgs among them) keep their audio codec in the same bfloat16 checkpoint as the model. mlx-audio reads
those tensors through safetensors' MLX reader, which goes through numpy, and numpy has no bfloat16; mlx-audio then
falls back to PyTorch, which Ocarina does not include. MLX can read bfloat16 safetensors itself (mx.load), so in the
worker process the MLX reader is replaced by one that uses it. Only requests for framework "mlx" are changed.
"""

import sys

import safetensors


class MlxSafeOpen:
    "A safe_open that returns MLX arrays read by MLX itself (bfloat16 included); other safe_open features pass through."

    def __init__(self, original, path, framework="mlx", device="cpu"):  # pylint: disable=unused-argument
        import mlx.core as mx  # pylint: disable=import-outside-toplevel

        self._header = original(path, framework="numpy")  # opening reads only the header: keys and metadata
        self._tensors = mx.load(str(path))  # lazy: nothing is read until a tensor is used

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def keys(self):
        "Names of the tensors in the file."
        return list(self._tensors.keys())

    def metadata(self):
        "The file's metadata."
        return self._header.metadata()

    def get_tensor(self, name):
        "One tensor, as an MLX array."
        return self._tensors[name]


def install():
    "Make safetensors.safe_open(..., framework='mlx') use MLX's own reader. Safe to call twice."
    original = safetensors.safe_open
    if getattr(original, "ocarina_patched", False):
        return

    def safe_open(path, framework="pt", device="cpu"):
        if framework == "mlx":
            return MlxSafeOpen(original, path, framework, device)
        return original(path, framework=framework, device=device)

    safe_open.ocarina_patched = True
    safetensors.safe_open = safe_open
    # Modules that did `from safetensors import safe_open` earlier still hold the old function: swap theirs too.
    for module in list(sys.modules.values()):
        if getattr(module, "safe_open", None) is original:
            module.safe_open = safe_open
