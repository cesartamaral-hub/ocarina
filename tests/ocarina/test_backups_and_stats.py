"""
Backups (settings, making, listing, downloading) and reading stats.
"""

import gzip
import os
import sqlite3

from tests.ocarina.helpers import make_dutch_book

BACKUPS = "/ocarina/api/backups"


def _configure(client, folder, **changes):
    settings = {"enabled": True, "auto": True, "warn": True, "dir": str(folder), "count": 2, **changes}
    return client.put(f"{BACKUPS}/settings", json=settings)


def test_settings_are_validated_and_saved(client, tmp_path):
    "The folder must be a full path (it is created); the count is limited."
    folder = tmp_path / "mijn" / "backups"
    assert _configure(client, folder).status_code == 200 and folder.is_dir()
    saved = client.get(BACKUPS).json["settings"]
    assert {k: saved[k] for k in ("enabled", "auto", "warn", "dir", "count")} == {
        "enabled": True, "auto": True, "warn": True, "dir": str(folder), "count": 2,
    }
    assert _configure(client, "relative/path").status_code == 400
    assert _configure(client, folder, count=0).status_code == 400
    assert _configure(client, folder, count="x").status_code == 400
    assert _configure(client, "/proc/not-allowed/x").status_code == 400


def test_make_backup_lists_and_downloads_it(app, client, tmp_path):
    "A backup is a gzipped copy of the database that opens as SQLite; it can be downloaded."
    _configure(client, tmp_path)
    with app.app_context():
        make_dutch_book("In de backup")
    made = client.post(BACKUPS, json={"manual": True})
    assert made.status_code == 201
    name = made.json["name"]
    assert name.startswith("manual_lute_backup_") and name.endswith(".db.gz")
    state = client.get(BACKUPS).json
    assert [b["name"] for b in state["backups"]] == [name] and state["backups"][0]["manual"] is True
    assert state["settings"]["lastBackup"] is not None and state["dueNow"] is False
    body = client.get(f"{BACKUPS}/{name}/download").data
    restored = tmp_path / "restored.db"
    restored.write_bytes(gzip.decompress(body))
    titles = [r[0] for r in sqlite3.connect(restored).execute("select BkTitle from books")]
    assert "In de backup" in titles


def test_automatic_backups_are_pruned_but_manual_ones_are_kept(app, client, tmp_path):
    "Only the newest N automatic backups stay; manual ones are never removed."
    from lute.backup.service import Service  # pylint: disable=import-outside-toplevel
    from lute.db import db  # pylint: disable=import-outside-toplevel
    from lute.models.repositories import UserSettingRepository  # pylint: disable=import-outside-toplevel

    _configure(client, tmp_path, count=2)
    with app.app_context():
        settings = UserSettingRepository(db.session).get_backup_settings()
        service = Service(db.session)
        service.create_backup(app.env_config, settings, is_manual=True, suffix="a")
        for i in range(4):
            service.create_backup(app.env_config, settings, suffix=f"2026-01-0{i + 1}")
            # Backups are ordered by file time, which a fast test would not tell apart.
            os.utime(tmp_path / f"lute_backup_2026-01-0{i + 1}.db.gz", (1_000_000 + i, 1_000_000 + i))
    names = sorted(b["name"] for b in client.get(BACKUPS).json["backups"])
    assert names == [
        "lute_backup_2026-01-03.db.gz",
        "lute_backup_2026-01-04.db.gz",
        "manual_lute_backup_a.db.gz",
    ]


def test_download_refuses_other_files(client, tmp_path):
    "Only backup files in the backup folder can be downloaded."
    _configure(client, tmp_path)
    (tmp_path / "secret.txt").write_text("x")
    assert client.get(f"{BACKUPS}/secret.txt/download").status_code == 404
    assert client.get(f"{BACKUPS}/..%2Fconfig.yml/download").status_code == 404
    assert client.get(f"{BACKUPS}/lute_backup_missing.db.gz/download").status_code == 404


def test_backup_without_folder_and_skip(client):
    "No folder means no backup; skip marks today as done."
    client.put(f"{BACKUPS}/settings", json={"enabled": False, "auto": False, "warn": True, "dir": "", "count": 5})
    assert client.post(BACKUPS, json={}).status_code == 400
    assert client.post(f"{BACKUPS}/skip").json["lastBackup"] > 0


def test_stats_count_words_of_finished_pages(app, client):
    "Finishing a page adds its words to today's count and starts a streak."
    empty = client.get("/ocarina/api/stats").json
    assert empty["streak"] == 0 and empty["chart"] == {}
    with app.app_context():
        book_id = make_dutch_book("Stats").id
    client.post(f"/ocarina/api/books/{book_id}/pages/1/finish", json={})
    stats = client.get("/ocarina/api/stats").json
    dutch = next(row for row in stats["table"] if row["name"] == "Dutch")
    assert dutch["counts"]["day"] > 0 and dutch["counts"]["total"] == dutch["counts"]["day"]
    assert stats["streak"] == 1
    assert stats["chart"]["Dutch"][-1]["runningTotal"] == dutch["counts"]["total"]


def test_no_automatic_backup_is_due_for_an_empty_library(client, tmp_path, monkeypatch):
    "A new library has nothing to lose: no automatic backup is asked for until it holds a book or a term."
    import ocarina.api.backups as backups  # pylint: disable=import-outside-toplevel

    _configure(client, tmp_path)
    monkeypatch.setattr(backups, "_has_data", lambda: False)
    assert client.get(BACKUPS).json["dueNow"] is False
    monkeypatch.setattr(backups, "_has_data", lambda: True)
    assert client.get(BACKUPS).json["dueNow"] is True
