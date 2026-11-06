"""
Updates: finding a newer release, skipping it or being reminded later, the checksum of the download, and nothing happening while offline.
"""

import hashlib

import pytest
import requests

from ocarina import offline, prefs, updater
from ocarina.version import VERSION

URL = "/ocarina/api/update"
DMG = b"not really a disk image"
SHA = hashlib.sha256(DMG).hexdigest()


def release(version="9.9.9", digest=SHA, assets=True):
    out = {
        "tag_name": f"v{version}",
        "body": "What is new",
        "html_url": "https://github.com/x/y/releases/tag/v9.9.9",
        "draft": False,
        "prerelease": False,
        "assets": [],
    }
    if assets:
        out["assets"].append({"name": "Ocarina.dmg", "browser_download_url": "https://example.org/Ocarina.dmg", "size": len(DMG), "digest": f"sha256:{digest}" if digest else None})
    return out


class Reply:
    def __init__(self, data=None, status=200, content=b""):
        self._data, self.status_code, self._content = data, status, content
        self.headers = {"Content-Length": str(len(content))}
        self.text = ""

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(str(self.status_code))

    def iter_content(self, size):
        yield self._content

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture(autouse=True)
def fresh(app):
    updater._installing = False  # pylint: disable=protected-access
    prefs.update(prefs.path_for(app.env_config.datapath), {updater.PREF_SKIP: "", updater.PREF_SNOOZE: 0})  # the file outlives a test run
    updater._cache.update(at=0.0, release=None)  # pylint: disable=protected-access
    updater._download.update(state="idle", done=0, total=0, error="", path="", version="")  # pylint: disable=protected-access
    yield


@pytest.fixture
def github(monkeypatch):
    def serve(data=None, status=200):
        monkeypatch.setattr(requests, "get", lambda url, **kw: Reply(data, status, DMG) if "api.github.com" in url else Reply(None, 200, DMG))

    return serve


def test_versions_compare_as_numbers():
    assert updater.is_newer("0.10.0", "0.9.0") and updater.is_newer("v1.0.0", "0.9.9")
    assert not updater.is_newer("0.1.0", "0.1.0") and not updater.is_newer("banana", "0.1.0")


def test_a_newer_release_is_offered(client, github):
    github(release())
    body = client.get(URL).json
    assert body["current"] == VERSION and body["show"] is True and body["latest"]["version"] == "9.9.9" and body["latest"]["notes"] == "What is new"


def test_the_same_or_an_older_release_is_not(client, github):
    github(release(VERSION))
    assert client.get(URL).json["show"] is False


def test_a_release_without_a_checksum_or_disk_image_is_ignored(client, github):
    github(release(digest=None))
    assert client.get(URL).json["latest"] is None
    updater._cache.update(at=0.0)  # pylint: disable=protected-access
    github(release(assets=False))
    assert client.get(URL).json["latest"] is None


def test_no_release_yet_is_not_an_error(client, github):
    github(None, 404)
    body = client.get(URL).json
    assert body["latest"] is None and "error" not in body


def test_skipping_a_version_and_being_reminded_later(client, github):
    github(release())
    assert client.post(URL + "/skip", json={"version": "9.9.9"}).status_code == 200
    assert client.get(URL).json["show"] is False
    client.post(URL + "/unskip")
    assert client.get(URL).json["show"] is True
    client.post(URL + "/later")
    assert client.get(URL).json["show"] is False
    client.post(URL + "/unskip")


def test_checking_can_be_switched_off_but_check_now_still_works(client, github):
    github(release())
    assert client.put(URL + "/settings", json={"check": False}).json == {"check": False}
    assert client.get(URL).json["latest"] is None
    assert client.get(URL + "?force=1").json["latest"]["version"] == "9.9.9"
    client.put(URL + "/settings", json={"check": True})
    assert client.put(URL + "/settings", json={"check": "yes"}).status_code == 400


def test_nothing_is_asked_of_github_while_offline(client, monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail("no request while offline"))
    client.put("/ocarina/api/offline", json={"offline": True})
    try:
        body = client.get(URL + "?force=1").json
        assert body["offline"] is True and body["latest"] is None
        assert client.post(URL + "/download").status_code == 409
    finally:
        client.put("/ocarina/api/offline", json={"offline": False})
    assert offline.is_on() is False


def test_the_download_is_checked_against_its_checksum(app, client, github, tmp_path):
    github(release())
    rel = updater.latest()
    with app.app_context():
        datapath = app.env_config.datapath
    assert updater.start_download(rel, datapath)
    for _ in range(100):
        if updater.state()["state"] != "running":
            break
        __import__("time").sleep(0.05)
    assert updater.state()["state"] == "done" and open(updater.state()["path"], "rb").read() == DMG

    github(release(digest="0" * 64))
    updater._cache.update(at=0.0)  # pylint: disable=protected-access
    bad = updater.latest()
    updater._download.update(state="idle")  # pylint: disable=protected-access
    updater.start_download(bad, datapath)
    for _ in range(100):
        if updater.state()["state"] != "running":
            break
        __import__("time").sleep(0.05)
    assert updater.state()["state"] == "error" and "checksum" in updater.state()["error"]


def test_it_will_not_replace_a_developers_copy(client):
    r = client.post(URL + "/install")
    assert r.status_code == 409 and "installed Ocarina app" in r.json["error"]


def test_a_second_install_while_one_unpacks_is_refused(client, monkeypatch, tmp_path):
    "Clicking Restart again must not start another unpack into the same folder."
    import threading

    app_dir = tmp_path / "Ocarina.app"
    (app_dir / "Contents" / "Resources").mkdir(parents=True)
    dmg = tmp_path / "x.dmg"
    dmg.write_bytes(b"x")
    monkeypatch.setenv("RESOURCEPATH", str(app_dir / "Contents" / "Resources"))
    monkeypatch.setitem(updater._download, "state", "done")  # pylint: disable=protected-access
    monkeypatch.setitem(updater._download, "path", str(dmg))  # pylint: disable=protected-access
    started, release = threading.Event(), threading.Event()

    def slow_stage(_dmg, _target):
        started.set()
        release.wait(5)
        raise OSError("stop here")

    monkeypatch.setattr(updater, "_stage", slow_stage)
    first = {}
    t = threading.Thread(target=lambda: first.update(r=client.post(URL + "/install")))
    t.start()
    assert started.wait(5)
    second = client.post(URL + "/install")
    release.set()
    t.join()
    assert second.status_code == 409 and "already being unpacked" in second.json["error"]
    assert "could not be unpacked" in first["r"].json["error"]
    assert client.post(URL + "/install").json["error"].startswith("The update could not")  # the flag is released after a failure
