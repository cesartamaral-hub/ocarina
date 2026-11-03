"""
Text-to-speech for Ocarina.

The model runs in a child process (worker.py) managed by the
supervisor; audio is generated per sentence and cached (cache.py).
"""
