"""
Loading bfloat16 weights without PyTorch (ocarina/tts/mlx_compat.py). Run in a child process: the patch changes a
library function, which must not leak into the other tests.
"""

import subprocess
import sys
import textwrap


def _run(code):
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], capture_output=True, text=True, check=False, timeout=120)


def test_bfloat16_is_read_without_torch_once_installed():
    "The stock MLX reader fails on bfloat16 (numpy has none); after install() it reads it, header and keys included."
    code = """
        import os, tempfile
        import mlx.core as mx
        import safetensors
        from safetensors import safe_open as early   # a library that imported the function before the patch
        path = os.path.join(tempfile.mkdtemp(), "t.safetensors")
        mx.save_safetensors(path, {"codec.w": mx.ones((4, 4), dtype=mx.bfloat16), "other": mx.zeros((2,), dtype=mx.float32)}, {"format": "mlx"})
        try:
            with early(path, framework="mlx") as f:
                f.get_tensor("codec.w")
            print("STOCK-WORKS")
        except TypeError as e:
            print("STOCK-FAILS", "bfloat16" in str(e))
        from ocarina.tts import mlx_compat
        mlx_compat.install()
        mlx_compat.install()  # twice is fine
        with safetensors.safe_open(path, framework="mlx") as f:
            print("KEYS", sorted(f.keys()))
            print("DTYPE", f.get_tensor("codec.w").dtype)
            print("META", f.metadata())
        try:
            import torch
            print("TORCH-PRESENT")
        except ModuleNotFoundError:
            print("NO-TORCH")
    """
    out = _run(code)
    assert out.returncode == 0, out.stderr
    assert "STOCK-FAILS True" in out.stdout  # the problem is real: the stock reader fails on bfloat16
    assert "KEYS ['codec.w', 'other']" in out.stdout and "DTYPE mlx.core.bfloat16" in out.stdout and "META {'format': 'mlx'}" in out.stdout


def test_other_frameworks_are_left_alone():
    "Only framework 'mlx' is replaced: numpy reads still go to the real safe_open."
    code = """
        import os, tempfile
        import mlx.core as mx
        import numpy as np
        from safetensors import safe_open
        from ocarina.tts import mlx_compat
        path = os.path.join(tempfile.mkdtemp(), "t.safetensors")
        mx.save_safetensors(path, {"w": mx.ones((2,), dtype=mx.float32)})
        mlx_compat.install()
        with safe_open(path, framework="numpy") as f:
            t = f.get_tensor("w")
            print("NUMPY", type(t).__name__, t.tolist())
    """
    out = _run(code)
    assert out.returncode == 0, out.stderr
    assert "NUMPY ndarray [1.0, 1.0]" in out.stdout


def test_modules_that_imported_the_function_early_are_updated_too():
    "A module holding the old safe_open (imported before install) gets the replacement."
    code = """
        import os, sys, tempfile, types
        import mlx.core as mx
        from safetensors import safe_open
        holder = types.ModuleType("holder")
        holder.safe_open = safe_open
        sys.modules["holder"] = holder
        path = os.path.join(tempfile.mkdtemp(), "t.safetensors")
        mx.save_safetensors(path, {"w": mx.ones((2,), dtype=mx.bfloat16)})
        from ocarina.tts import mlx_compat
        mlx_compat.install()
        with holder.safe_open(path, framework="mlx") as f:
            print("DTYPE", f.get_tensor("w").dtype)
    """
    out = _run(code)
    assert out.returncode == 0, out.stderr
    assert "DTYPE mlx.core.bfloat16" in out.stdout
