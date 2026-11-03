from setuptools import setup

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
                "soundfile",
                "_soundfile_data",
                "huggingface_hub",
                "transformers",
                "tokenizers",
                "safetensors",
                "numpy",
            ],
            "includes": ["sqlite3", "yaml"],
            "excludes": ["mlx"],  # copied by hand in build.sh, see there
            "iconfile": "../assets/Ocarina.icns",
            "plist": {
                "CFBundleName": "Ocarina",
                "CFBundleIdentifier": "app.ocarina.Ocarina",
                "NSHighResolutionCapable": True,
            },
        }
    },
    setup_requires=["py2app"],
)
