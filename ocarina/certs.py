"""
Certificates for HTTPS inside the packaged app.

py2app's launcher sets SSL_CERT_FILE and SSL_CERT_DIR to a file that does not exist ("openssl.ca/no-such-file"), so any default SSL
context (the model downloader, yt-dlp, urllib) failed with a bare FileNotFoundError. The app and the processes it starts (they inherit
the environment) use the certificates of the bundled `certifi` instead.

    use_bundled()   point SSL_CERT_FILE at certifi's file when the variable is missing or names a file that is not there
"""

import os


def use_bundled():
    "Make default SSL contexts find certificates; leaves a working setting alone."
    current = os.environ.get("SSL_CERT_FILE")
    if current and os.path.isfile(current):
        return
    import certifi  # pylint: disable=import-outside-toplevel

    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ.pop("SSL_CERT_DIR", None)
