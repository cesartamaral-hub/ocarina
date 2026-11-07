"""
What this Mac is: its chip and memory, and what that means for the models. A base MacBook Air with 8 GB cannot keep two models in memory and
still run a browser; one with 16 GB can keep one comfortably; 32 GB or more does not need to care. The tier decides how careful Ocarina is:
how many model workers may be alive at once and how much memory MLX may keep for reuse.

Set OCARINA_FAKE_RAM_GB to try another Mac's tier (development and tests).
"""

import functools
import os
import subprocess

GB = 1024**3
TIERS = ("small", "medium", "large")  # up to 8 GB, up to 16 GB, more


def _sysctl(name):
    try:
        return subprocess.run(["/usr/sbin/sysctl", "-n", name], capture_output=True, text=True, timeout=5, check=False).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


@functools.lru_cache(maxsize=1)
def info():
    "{chip, ramGb, tier}; ramGb is None and the tier 'large' when the Mac cannot be asked (nothing is held back then)."
    fake = os.environ.get("OCARINA_FAKE_RAM_GB")
    ram = float(fake) if fake else (int(_sysctl("hw.memsize") or 0) / GB or None)
    return {"chip": _sysctl("machdep.cpu.brand_string") or "this Mac", "ramGb": ram, "tier": tier_for(ram)}


def tier_for(ram_gb):
    if not ram_gb:
        return "large"
    return "small" if ram_gb <= 8.5 else "medium" if ram_gb <= 16.5 else "large"


def one_at_a_time():
    "Whether a worker that starts should make the idle ones give their memory back first."
    return info()["tier"] != "large"


def mlx_cache_mb():
    "How much memory MLX may keep for reuse after a call (it keeps all it can by default, which crowds a small Mac); None = no limit."
    return {"small": 256, "medium": 1024}.get(info()["tier"])


def fit(size_bytes, ram_gb=None):
    """
    How a model of this download size sits in this Mac's memory while it works (it needs roughly 1.3 times its files, and macOS and the
    apps need the rest): 'ok', 'tight' (works, other apps will feel it) or 'too big'. 'ok' when the memory is not known.
    """
    ram = ram_gb if ram_gb is not None else info()["ramGb"]
    if not ram or not size_bytes:
        return "ok"
    need = size_bytes * 1.3 / GB
    return "ok" if need <= ram * 0.35 else "tight" if need <= ram * 0.6 else "too big"
