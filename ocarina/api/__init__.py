"""
Ocarina's routes, registered on the Lute app.
"""

from ocarina.api import books_routes, tts_routes, web


def register(app):
    "Register all Ocarina blueprints."
    for module in (books_routes, tts_routes, web):
        app.register_blueprint(module.bp)
