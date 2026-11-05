import os
import sys

from setuptools import setup

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ocarina.version import VERSION  # noqa: E402

setup(
    app=["ocarina_app.py"],
    name="Ocarina",
    options={
        "py2app": {
            "packages": [
                "lute",
                "ocarina",
                "webview",
                "waitress",
                "sqlalchemy",
                "flask_sqlalchemy",
                "mlx_audio",
                "mlx_lm",
                "soundfile",
                "_soundfile_data",
                "huggingface_hub",
                "transformers",
                "tokenizers",
                "safetensors",
                "numpy",
                "trafilatura",
                "courlan",
                "htmldate",
                "justext",
                "lxml",
                "yt_dlp",
                "youtube_transcript_api",
            ],
            "includes": ["sqlite3", "yaml"],
            "excludes": ["mlx", "tkinter", "_tkinter"],  # copied by hand in build.sh, see there
            "resources": ["../LICENSE.txt", "../NOTICE.md"],
            "iconfile": "../assets/Ocarina.icns",
            "plist": {
                "CFBundleName": "Ocarina",
                "CFBundleShortVersionString": VERSION,
                "CFBundleVersion": VERSION,
                "CFBundleIdentifier": "app.ocarina.Ocarina",
                "NSHighResolutionCapable": True,
                "LSMinimumSystemVersion": "14.0",
            },
        }
    },
    setup_requires=["py2app"],
)
