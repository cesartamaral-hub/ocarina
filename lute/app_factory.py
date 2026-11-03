"""
Factory.

Methods: create_app.
"""

import os
import json
import platform
import traceback
import mimetypes
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    flash,
    current_app,
    make_response,
    send_from_directory,
    jsonify,
)
from sqlalchemy.event import listens_for
from sqlalchemy.pool import Pool

from lute.config.app_config import AppConfig
from lute.db import db
from lute.db.setup.main import setup_db
from lute.db.management import add_default_user_settings
from lute.db.data_cleanup import clean_data
from lute.backup.service import Service as BackupService
from lute.db.demo import Service as DemoService
import lute.utils.formutils

from lute.parse.registry import init_parser_plugins, supported_parsers

from lute.models.book import Book
from lute.models.language import Language
from lute.settings.current import (
    refresh_global_settings,
    current_settings,
    current_hotkeys,
)
from lute.models.repositories import UserSettingRepository
from lute.book.stats import Service as StatsService
from lute.stats.service import get_reading_streak

from lute.userimage.routes import bp as userimage_bp
from lute.useraudio.routes import bp as useraudio_bp
from lute.dev_api.routes import bp as dev_api_bp
from lute.cli.commands import bp as cli_bp
from ocarina.api import register as register_ocarina


def _setup_app_dir(dirname, readme_content):
    "Create one app directory."
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    readme = os.path.join(dirname, "README.md")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8") as f:
            f.write(readme_content)


def _setup_app_dirs(app_config):
    """
    App needs the data dir, backups, and other directories.
    """
    dp = app_config.datapath
    required_dirs = [
        [dp, "Lute data folder."],
        [
            app_config.default_user_backup_path,
            "Default path for user backups, can be overridden in settings.",
        ],
        [
            app_config.system_backup_path,
            "Database backups created by Lute at app start, just in case.",
        ],
        [
            app_config.userimagespath,
            "User images.  Each subfolder is a language's ID.",
        ],
        [
            app_config.userthemespath,
            "User themes.  <theme_name>.css files for your personal themes.",
        ],
        [
            app_config.useraudiopath,
            "User audio.  Each file is a book's audio.",
        ],
        [
            app_config.temppath,
            "Temp directory for export file writes, to avoid permissions issues.",
        ],
    ]
    for rec in required_dirs:
        _setup_app_dir(rec[0], rec[1])


def _add_base_routes(app, app_config):  # pylint: disable=unused-argument
    """
    Add some basic routes. The screens themselves are the React app (see ocarina/web and ocarina/api).
    """

    @app.route("/")
    def index():
        return redirect("/ocarina/app/", 302)

    @app.route("/info")
    def show_info():
        """
        Json return of some data.

        Used in lute.verify module for tests.
        """
        ret = {
            "version": lute.__version__,
            "datapath": current_app.config["DATAPATH"],
            "database": current_app.config["DATABASE"],
        }
        return jsonify(ret)

    @app.errorhandler(500)
    def _internal_server_error(e):  # pylint: disable=unused-argument
        "A server error: JSON for the app's own calls (the message is shown by the app), plain text elsewhere."
        detail = traceback.format_exc()
        if request.path.startswith("/ocarina/api/"):
            return jsonify({"error": "Something went wrong on the server", "detail": detail}), 500
        return f"Something went wrong.\n\n{detail}", 500, {"Content-Type": "text/plain; charset=utf-8"}

    @app.errorhandler(404)
    def _page_not_found(e):  # pylint: disable=unused-argument
        "Not found: JSON for the app's own calls, plain text elsewhere."
        if request.path.startswith("/ocarina/api/"):
            return jsonify({"error": "Not found"}), 404
        return "Not found", 404, {"Content-Type": "text/plain; charset=utf-8"}


def _create_app(app_config, extra_config):
    """
    Create the app using the given configuration,
    and init the SqlAlchemy db.
    """

    app = Flask(__name__, instance_path=app_config.datapath)

    config = {
        "SECRET_KEY": "some_secret",
        "DATABASE": app_config.dbfilename,
        "ENV": app_config.env,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{app_config.dbfilename}",
        "DATAPATH": app_config.datapath,
        # ref https://flask-sqlalchemy.palletsprojects.com/en/2.x/config/
        # Don't track mods.
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        # Disable CSRF -- this is a local app, and it's highly
        # unlikely that a malicious site will try to hack anyone's Lute data.
        # ref https://stackoverflow.com/questions/5207160/
        #   what-is-a-csrf-token-what-is-its-importance-and-how-does-it-work
        "WTF_CSRF_ENABLED": False,
    }

    final_config = {**config, **extra_config}
    app.config.from_mapping(final_config)

    # Attach the app_config to app so it's available at runtime.
    app.env_config = app_config

    db.init_app(app)

    @listens_for(Pool, "connect")
    def _pragmas_on_connect(dbapi_con, con_record):  # pylint: disable=unused-argument
        dbapi_con.execute("pragma recursive_triggers = on;")
        dbapi_con.execute("pragma foreign_keys = on;")

    with app.app_context():
        db.create_all()
        add_default_user_settings(db.session, app_config.default_user_backup_path)
        refresh_global_settings(db.session)
    app.db = db

    _add_base_routes(app, app_config)
    app.register_blueprint(userimage_bp)
    app.register_blueprint(useraudio_bp)
    app.register_blueprint(cli_bp)
    register_ocarina(app)
    if app_config.is_test_db:
        app.register_blueprint(dev_api_bp)

    return app


def _init_parser_plugins(plugin_data_path, outfunc):
    "Load and init plugins."
    outfunc("Initializing parsers from plugins ...")
    init_parser_plugins()

    parsers = supported_parsers()
    parsers_with_extra_data = [
        (typename, klass) for typename, klass in parsers if klass.uses_data_directory()
    ]
    if len(parsers_with_extra_data) > 0:
        # outfunc("Creating data folders for plugins ...")
        _setup_app_dir(plugin_data_path, "Data files for plugins.")
    for pair in parsers_with_extra_data:
        typename, klass = pair
        dirname = os.path.join(plugin_data_path, typename)
        klass.data_directory = dirname

        readme_content = f"Extra data for {klass.name()} plugin."
        _setup_app_dir(dirname, readme_content)
        klass.init_data_directory()
        # outfunc(f"  * {klass.name()}: {dirname}")

    outfunc("Enabled parsers:")
    for _, v in supported_parsers():
        outfunc(f"  * {v.name()}")


mimetypes.add_type("text/css", ".css")


def create_app(
    app_config_path=None,
    extra_config=None,
    output_func=None,
):
    """
    App factory.  Calls dbsetup, and returns Flask app.

    Args:
    - app_config_path: path to yml file.  If None, use root config or default.
    - extra_config: dict, e.g. pass { 'TESTING': True } during unit tests.
    """

    def null_print(s):  # pylint: disable=unused-argument
        pass

    outfunc = output_func or null_print

    if app_config_path is None:
        if os.path.exists("config.yml"):
            app_config_path = "config.yml"
        else:
            app_config_path = AppConfig.default_config_filename()

    app_config = AppConfig(app_config_path)
    _setup_app_dirs(app_config)
    setup_db(app_config, output_func)

    if extra_config is None:
        extra_config = {}
    outfunc("Initializing app.")
    app = _create_app(app_config, extra_config)

    # Plugins are loaded after the app, as they may use settings etc.
    _init_parser_plugins(app_config.plugin_datapath, outfunc)

    return app


def data_initialization(session, output_func=None):
    """
    Any extra data setup.

    TODO: rework data initialization.  The DB setup can be handled
    outside of the application context, as IMO it's clearer to manage
    the data separately from the thing that uses the data.  This
    requires moving from flask-sqlalchemy to plain sqlalchemy.
    """

    def _null_print(s):  # pylint: disable=unused-argument
        pass

    outfunc = output_func or _null_print

    demosvc = DemoService(session)
    if demosvc.should_load_demo_data():
        outfunc("Loading demo data.")
        demosvc.load_demo_data()

    # TODO valid parsers: do parser check, mark valid as active, invalid as inactive.

    clean_data(session, outfunc)
