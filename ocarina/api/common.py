"""
Small helpers shared by the API modules.
"""

ZWS = "\u200B"  # zero-width space: Lute puts it between tokens


def clean(text):
    "Text for display: no zero-width spaces, no surrounding blanks."
    return (text or "").replace(ZWS, "").strip()
