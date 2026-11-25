"""Read-only public routes: homepage, partner data, translations."""
import json

from flask import Blueprint, abort, current_app, jsonify, render_template

from ..assets import asset_version

public_bp = Blueprint("public", __name__)

SUPPORTED_LANGS = ("ar", "en")


def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@public_bp.get("/")
def index():
    return render_template("index.html")


@public_bp.get("/api/partners")
def partners():
    data = _load_json(current_app.config["DATA_FILE"])
    for record in data:
        # Version local logo URLs by file content so a replaced image is never served from browser cache.
        logo = record.get("logo")
        if isinstance(logo, str) and logo.startswith("/static/") and "?" not in logo:
            version = asset_version(current_app.static_folder, logo[len("/static/"):])
            if version:
                record["logo"] = f"{logo}?v={version}"
    response = jsonify(data)
    response.headers["Cache-Control"] = "no-cache"
    return response


@public_bp.get("/api/translations/<lang>")
def translations(lang):
    if lang not in SUPPORTED_LANGS:
        abort(404)
    response = jsonify(_load_json(current_app.config["TRANSLATIONS_DIR"] / f"{lang}.json"))
    response.headers["Cache-Control"] = "public, max-age=300"
    return response
