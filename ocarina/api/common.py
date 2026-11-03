"""
Small helpers shared by the API modules.
"""

ZWS = "\u200B"  # zero-width space: Lute puts it between tokens

# Audio formats a book can have as its own recording.
ALLOWED_AUDIO_EXTENSIONS = ["mp3", "m4a", "m4b", "wav", "ogg", "opus", "aac", "flac", "webm"]


def clean(text):
    "Text for display: no zero-width spaces, no surrounding blanks."
    return (text or "").replace(ZWS, "").strip()
