"""
JSON API for backups of the database (the images folder is mirrored next to them).

    GET  /ocarina/api/backups                  settings, a warning if due, and the backup files
    PUT  /ocarina/api/backups/settings         enabled, auto, warn, dir, count
    POST /ocarina/api/backups                  make a backup now ({"manual": true} keeps it for good)
    POST /ocarina/api/backups/skip             count today as backed up (stops the daily reminder)
    GET  /ocarina/api/backups/<name>/download  one backup file

Backups are gzip-compressed copies of the database. To restore one, quit the app, gunzip the file
and put it in the data folder as ocarina.db.
"""

import os
import re
import time

from flask import Blueprint, current_app, jsonify, request, send_file
from sqlalchemy import text as sql

from lute.backup.service import BackupException, Service as BackupService
from lute.db import db
from lute.models.repositories import UserSettingRepository

bp = Blueprint("ocarina_backups", __name__, url_prefix="/ocarina/api")

NAME = re.compile(r"^(manual_)?lute_backup_[\w.\-]+$")
MAX_KEPT = 100


def _settings():
    return UserSettingRepository(db.session).get_backup_settings()


def _file_json(f):
    return {
        "name": f.name,
        "manual": f.is_manual,
        "size": f.size,
        "sizeBytes": f.size_bytes,
        "modified": int(f.last_modified.timestamp()),
    }


def _has_data():
    "True once the library holds a book or a term; an empty one is not worth backing up."
    return bool(db.session.execute(sql("select exists(select 1 from books) or exists(select 1 from words)")).scalar())


def _state():
    settings = _settings()
    service = BackupService(db.session)
    files = []
    if settings.backup_dir and os.path.isdir(settings.backup_dir):
        files = sorted(service.list_backups(settings.backup_dir), reverse=True)
    return {
        "settings": {
            "enabled": settings.backup_enabled,
            "auto": settings.backup_auto,
            "warn": settings.backup_warn,
            "dir": settings.backup_dir or "",
            "count": settings.backup_count,
            "lastBackup": settings.last_backup_datetime,
        },
        "warning": service.backup_warning(settings),
        "dueNow": service.should_run_auto_backup(settings) and _has_data(),
        "backups": [_file_json(f) for f in files],
    }


@bp.route("/backups", methods=["GET"])
def backups():
    "Settings, whether a backup is due, a warning if backups are old, and the files."
    return jsonify(_state())


@bp.route("/backups/settings", methods=["PUT"])
def save_settings():
    "Change the backup settings."
    body = request.get_json(silent=True) or {}
    enabled = bool(body.get("enabled"))
    directory = (body.get("dir") or "").strip()
    try:
        count = int(body.get("count"))
    except (TypeError, ValueError):
        return jsonify({"error": "How many backups to keep must be a number"}), 400
    if not 1 <= count <= MAX_KEPT:
        return jsonify({"error": f"Keep between 1 and {MAX_KEPT} backups"}), 400
    if enabled or directory:
        if not os.path.isabs(directory):
            return jsonify({"error": "The backup folder must be a full path, starting with /"}), 400
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError as e:
            return jsonify({"error": f"Can't use that folder: {e.strerror}"}), 400
    repo = UserSettingRepository(db.session)
    repo.set_value("backup_enabled", 1 if enabled else 0)
    repo.set_value("backup_auto", 1 if body.get("auto") else 0)
    repo.set_value("backup_warn", 1 if body.get("warn") else 0)
    repo.set_value("backup_dir", directory)
    repo.set_value("backup_count", count)
    db.session.commit()
    return jsonify(_state())


@bp.route("/backups", methods=["POST"])
def make_backup():
    "Make a backup now."
    manual = bool((request.get_json(silent=True) or {}).get("manual"))
    settings = _settings()
    if not settings.backup_dir:
        return jsonify({"error": "Choose a backup folder first"}), 400
    try:
        made = BackupService(db.session).create_backup(current_app.env_config, settings, is_manual=manual)
    except (BackupException, OSError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"name": os.path.basename(made), **{"backups": _state()["backups"]}}), 201


@bp.route("/backups/skip", methods=["POST"])
def skip():
    "Count today as backed up."
    BackupService(db.session).skip_this_backup()
    return jsonify({"lastBackup": int(time.time())})


@bp.route("/backups/<name>/download", methods=["GET"])
def download(name):
    "One backup file."
    directory = _settings().backup_dir
    path = os.path.join(directory or "", name)
    if not NAME.match(name) or not directory or not os.path.isfile(path):
        return jsonify({"error": "No such backup"}), 404
    return send_file(path, as_attachment=True)
