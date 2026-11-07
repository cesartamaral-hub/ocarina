"The version of the app. scripts/release.sh changes it; the update check compares it with the latest GitHub release."
import os
import subprocess

VERSION = "0.2.2"


def _dev_build():
    "The commit of a dev build, '' for a release. desktop/build.sh stamps it into ocarina/_dev_build.py (unless scripts/release.sh builds); a run from the source folder asks git."
    try:
        from ocarina._dev_build import COMMIT  # pylint: disable=import-outside-toplevel
        return COMMIT
    except ImportError:
        pass
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(os.path.join(root, ".git")):
        return ""
    try:
        return subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=3, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


DEV_BUILD = _dev_build()
