from setuptools import setup

setup(
    app=["ocarina_app.py"],
    name="Ocarina",
    options={
        "py2app": {
            "packages": ["lute", "webview", "waitress", "sqlalchemy", "flask_sqlalchemy"],
            "includes": ["sqlite3", "yaml"],
            "plist": {
                "CFBundleName": "Ocarina",
                "CFBundleIdentifier": "app.ocarina.spike",
                "NSHighResolutionCapable": True,
            },
        }
    },
    setup_requires=["py2app"],
)
