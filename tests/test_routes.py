import pytest

from backend.app import create_app


@pytest.fixture()
def client():
    return create_app().test_client()


def test_homepage(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'lang="ar"' in html and 'dir="rtl"' in html
    assert "haymanat-logo.png" in html


@pytest.mark.parametrize("path", [
    "/static/css/base.css", "/static/css/components.css", "/static/css/responsive.css",
    "/static/js/main.js", "/static/js/i18n.js", "/static/js/search.js",
    "/static/js/filters.js", "/static/js/modals.js", "/static/images/haymanat-logo.png",
    "/static/fonts/tajawal-arabic-400-normal.woff2", "/static/fonts/inter-latin-400-normal.woff2",
])
def test_static_assets(client, path):
    assert client.get(path).status_code == 200


def test_partners_api(client):
    r = client.get("/api/partners")
    assert r.status_code == 200 and len(r.get_json()) == 65


@pytest.mark.parametrize("lang", ["ar", "en"])
def test_translations_api(client, lang):
    assert client.get(f"/api/translations/{lang}").status_code == 200


def test_unknown_language_404(client):
    assert client.get("/api/translations/../data/partners").status_code == 404
    assert client.get("/api/translations/fr").status_code == 404


def test_no_admin_or_write_routes():
    app = create_app()
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        assert rule.methods <= {"GET", "HEAD", "OPTIONS"}, rule
        for bad in ("admin", "login", "register", "account"):
            assert bad not in rule.rule
    c = app.test_client()
    for path in ("/admin", "/login", "/register"):
        assert c.get(path).status_code == 404
    assert c.post("/api/partners").status_code == 405
    assert c.delete("/api/partners").status_code == 405


def test_unknown_page_redirects_home_not_404(client):
    r = client.get("/nope", follow_redirects=True)
    assert r.status_code == 200 and "haymanat-logo.png" in r.get_data(as_text=True)


def test_missing_asset_is_real_404(client):
    assert client.get("/static/css/missing.css").status_code == 404


def test_no_directory_listing(client):
    for p in ("/static/", "/static", "/static/css/", "/data/", "/translations/"):
        r = client.get(p, follow_redirects=True)
        assert "Index of" not in r.get_data(as_text=True)


def test_data_files_not_exposed_directly(client):
    assert client.get("/data/partners.json").status_code in (302, 404)
    assert client.get("/translations/ar.json").status_code in (302, 404)


def test_vercel_entrypoint():
    import app as entry
    from flask import Flask
    assert isinstance(entry.app, Flask)
    r = entry.app.test_client().get("/")
    assert r.status_code == 200
    assert len(entry.app.test_client().get("/api/partners").get_json()) == 65


def test_deployment_files():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    assert (root / ".python-version").read_text().strip() == "3.13"
    assert (root / "requirements.txt").read_text().split() == ["Flask>=3.0,<4.0"]
    assert (root / "public" / "static" / "images" / "haymanat-logo.png").exists()
    assert (root / "data" / "partners.json").exists()
    ignore = (root / ".gitignore").read_text()
    for needed in (".venv", "__pycache__", ".env"):
        assert needed in ignore
    import json
    cfg = json.loads((root / "vercel.json").read_text())
    assert "includeFiles" in cfg["functions"]["app.py"]


def test_404_page(client):
    assert client.get("/nope").status_code == 302
