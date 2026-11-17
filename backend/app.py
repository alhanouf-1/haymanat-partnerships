"""Flask application factory for the Haymanat Alnajah partnerships showcase."""
from pathlib import Path

from flask import Flask, redirect, request, url_for

from .routes.public_routes import public_bp
from .security import apply_security_headers

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# First path segments that must answer with a real 404 (never the homepage fallback).
RESERVED_PREFIXES = {
    "static", "api", "admin", "login", "logout", "register", "signup", "account", "dashboard",
    "backend", "frontend", "data", "translations", "tests", "instance", "public",
    "__debugger__", "console", "wp-admin", "wp-login.php", "phpmyadmin",
}


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / "frontend" / "templates"),
        static_folder=str(PROJECT_ROOT / "public" / "static"),
        static_url_path="/static",
    )
    app.config["PROJECT_ROOT"] = PROJECT_ROOT
    app.config["DATA_FILE"] = PROJECT_ROOT / "data" / "partners.json"
    app.config["TRANSLATIONS_DIR"] = PROJECT_ROOT / "translations"
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 60 * 60 * 24 * 7  # static asset caching
    app.config["DEBUG"] = False
    app.config["TESTING"] = False
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # public read-only site: reject large bodies

    app.register_blueprint(public_bp)

    @app.errorhandler(404)
    def not_found(_error):
        # Unknown page URLs fall back to the homepage (single-page site). Dotfiles, files with an
        # extension, API/asset paths and sensitive-looking prefixes keep a real 404.
        path = request.path.strip("/")
        first = path.split("/", 1)[0].lower()
        if (request.method in ("GET", "HEAD") and "." not in path
                and first not in RESERVED_PREFIXES):
            return redirect(url_for("public.index"))
        return "Not found", 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return "Method not allowed", 405

    @app.errorhandler(413)
    def too_large(_error):
        return "Request too large", 413

    @app.errorhandler(500)
    def server_error(_error):
        return "Internal server error", 500

    @app.after_request
    def security_headers(response):
        secure = request.is_secure or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
        return apply_security_headers(response, secure)

    return app
