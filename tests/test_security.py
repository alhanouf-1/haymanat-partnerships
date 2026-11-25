"""Automated security regression tests (executed with pytest; no network or live server needed)."""
import json
import re
from pathlib import Path

import pytest

from backend.app import create_app
from backend.security import CSP, HEADERS

ROOT = Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".py", ".html", ".css", ".js", ".json", ".md", ".txt", ".toml", ".cfg"}


@pytest.fixture()
def client():
    return create_app().test_client()


def project_text_files():
    skip = {"__pycache__", ".pytest_cache", ".git", ".venv", "node_modules"}
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in TEXT_SUFFIXES and not (set(p.parts) & skip):
            yield p


# ---------- headers ----------
@pytest.mark.parametrize("path", ["/", "/api/partners", "/api/translations/ar", "/static/css/base.css", "/nope"])
def test_security_headers_on_all_responses(client, path):
    r = client.get(path)
    for name, value in HEADERS.items():
        assert r.headers.get(name) == value, (path, name)


def test_csp_is_strict():
    assert "'unsafe-inline'" not in CSP and "'unsafe-eval'" not in CSP
    for d in ("default-src 'self'", "script-src 'self'", "object-src 'none'", "base-uri 'none'", "frame-ancestors 'none'"):
        assert d in CSP


def test_hsts_only_on_https(client):
    assert "Strict-Transport-Security" not in client.get("/").headers
    r = client.get("/", headers={"X-Forwarded-Proto": "https"})
    assert "max-age=" in r.headers["Strict-Transport-Security"]


def test_vercel_headers_mirror_flask_headers():
    cfg = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    rule = next(h for h in cfg["headers"] if h["source"] == "/(.*)")
    got = {h["key"]: h["value"] for h in rule["headers"]}
    for k, v in HEADERS.items():
        assert got[k] == v, k
    assert "Strict-Transport-Security" in got


# ---------- CSP compatibility of the frontend ----------
def test_no_inline_script_or_handlers_in_templates():
    for tpl in (ROOT / "frontend" / "templates").glob("*.html"):
        html = tpl.read_text(encoding="utf-8")
        assert not re.search(r"<script(?![^>]*\bsrc=)", html), tpl.name
        assert not re.search(r"\son[a-z]+\s*=", html, re.I), tpl.name
        assert not re.search(r'\sstyle\s*=', html, re.I), tpl.name
        assert "javascript:" not in html.lower()
        assert "|safe" not in html and "Markup(" not in html


def test_no_inline_handlers_or_styles_in_js_templates():
    for js in (ROOT / "public" / "static" / "js").glob("*.js"):
        src = js.read_text(encoding="utf-8")
        assert not re.search(r"\son(error|click|load)\s*=", src), js.name
        assert not re.search(r'style="', src), js.name
        for bad in ("eval(", "new Function(", "document.write(", "insertAdjacentHTML", "outerHTML"):
            assert bad not in src, (js.name, bad)


def test_js_does_not_interpolate_unescaped_values_in_innerhtml():
    """Every ${...} inside innerHTML templates must be escaped, numeric/const, or a template helper."""
    safe = re.compile(r"escapeHtml\(|^(k|key|i)$|counts\[|p\.category|p\.period|\.join\(|cardHtml|state\.category === k|"
                      r"k === |key === |counts\.|Math\.min|renderOptions")
    for name in ("main.js", "modals.js"):
        src = (ROOT / "public" / "static" / "js" / name).read_text(encoding="utf-8")
        for expr in re.findall(r"\$\{([^}]*)\}", src):
            e = expr.strip()
            if not e:
                continue
            assert safe.search(e) or re.fullmatch(r"[\w.]+", e), f"{name}: review interpolation ${{{e}}}"


# ---------- XSS / injection ----------
def test_query_string_is_not_reflected(client):
    probe = "<script>window.__probe=1</script>"
    for path in ("/", "/nope"):
        r = client.get(path, query_string={"q": probe}, follow_redirects=True)
        assert probe not in r.get_data(as_text=True)


def test_error_pages_do_not_reflect_path(client):
    r = client.get("/static/%3Cscript%3Ealert(1)%3C/script%3E.css")
    assert r.status_code == 404 and "<script>" not in r.get_data(as_text=True)


def test_no_debugger_or_traceback(client):
    app = create_app()
    assert app.debug is False and app.config["DEBUG"] is False
    for p in ("/__debugger__", "/console"):
        r = client.get(p)
        assert r.status_code == 404
        body = r.get_data(as_text=True).lower()
        assert "traceback" not in body and "werkzeug" not in body


def test_no_debug_true_in_source():
    for p in project_text_files():
        if p.suffix == ".py" and p.parent.name != "tests":
            assert "debug=True" not in p.read_text(encoding="utf-8"), p


# ---------- path traversal / sensitive files ----------
SENSITIVE = [
    "/.env", "/.git/config", "/.gitignore", "/requirements.txt", "/requirements-dev.txt", "/vercel.json",
    "/app.py", "/run.py", "/backend/app.py", "/backend/security.py", "/data/partners.json",
    "/translations/ar.json", "/tests/test_security.py", "/instance/partnerships.db", "/README.md",
    "/.python-version", "/frontend/templates/index.html", "/public/static/css/base.css",
]


@pytest.mark.parametrize("path", SENSITIVE)
def test_sensitive_files_not_public(client, path):
    r = client.get(path)
    assert r.status_code == 404, path


@pytest.mark.parametrize("path", [
    "/static/../app.py", "/static/..%2fapp.py", "/static/%2e%2e/app.py", "/static/%2e%2e%2fdata/partners.json",
    "/static/..%5c..%5capp.py", "/static/css/../../../app.py", "/static//etc/passwd",
    "/api/translations/..%2fdata%2fpartners", "/api/translations/../../app", "/api/translations/ar.json",
    "/api/translations/%2e%2e", "/api/translations/ar%00", "/api/translations/AR",
])
def test_path_traversal_blocked(client, path):
    r = client.get(path)
    body = r.get_data(as_text=True)
    assert r.status_code in (301, 308, 400, 404), (path, r.status_code)
    assert "create_app" not in body and "root:" not in body and "name_ar" not in body


def test_no_directory_listing(client):
    for p in ("/static/", "/static", "/static/css/", "/static/js/", "/static/fonts/", "/static/images/"):
        r = client.get(p, follow_redirects=True)
        assert "Index of" not in r.get_data(as_text=True)
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert "<title>" in r.get_data(as_text=True)  # homepage, not a listing


def test_dotfile_and_extension_paths_are_real_404(client):
    for p in ("/.env", "/wp-login.php", "/admin", "/login", "/admin/login", "/register", "/account"):
        assert client.get(p).status_code == 404, p


# ---------- HTTP methods ----------
@pytest.mark.parametrize("path", ["/", "/api/partners", "/api/translations/ar", "/static/css/base.css", "/admin", "/nope"])
@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_write_methods_rejected(client, path, method):
    r = getattr(client, method)(path, data={"x": "1"})
    assert r.status_code in (404, 405), (method, path, r.status_code)


def test_options_does_not_advertise_write_methods(client):
    for path in ("/", "/api/partners", "/api/translations/en"):
        allow = {m.strip() for m in client.options(path).headers.get("Allow", "").split(",")}
        assert not (allow & {"POST", "PUT", "PATCH", "DELETE"}), path


def test_all_routes_are_get_only():
    app = create_app()
    for rule in app.url_map.iter_rules():
        assert rule.methods <= {"GET", "HEAD", "OPTIONS"}, rule


def test_request_body_size_limited(client):
    r = client.post("/", data=b"x" * 50_000)
    assert r.status_code in (405, 413)


# ---------- secrets / config ----------
SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}", r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", r"ghp_[A-Za-z0-9]{30,}",
    r"sk-[A-Za-z0-9]{20,}", r"xox[baprs]-[A-Za-z0-9-]{10,}", r"AIza[0-9A-Za-z_-]{35}",
    r"(?i)(api[_-]?key|secret[_-]?key|password|passwd|token)\s*[:=]\s*['\"][^'\"\s]{6,}['\"]",
]


def test_no_secrets_in_repository_files():
    this = Path(__file__).resolve()
    for p in project_text_files():
        if p == this:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for pat in SECRET_PATTERNS:
            assert not re.search(pat, text), (p, pat)


def test_no_local_machine_paths_in_repository_files():
    this = Path(__file__).resolve()
    for p in project_text_files():
        if p == this:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        assert not re.search(r"[A-Za-z]:\\\\?Users\\|/Users/[A-Za-z]|/home/[a-z]+/|OneDrive", text), p


def test_no_sensitive_files_present():
    names = {".env", "id_rsa", "credentials.json", "secrets.json"}
    for p in ROOT.rglob("*"):
        if ".venv" in p.parts or ".git" in p.parts:
            continue
        assert p.name not in names and p.suffix not in {".db", ".sqlite", ".sqlite3", ".pem", ".key"}, p


def test_gitignore_protects_secrets_but_keeps_assets():
    lines = {l.strip() for l in (ROOT / ".gitignore").read_text().splitlines()}
    for needed in (".env", ".env.*", ".venv/", "__pycache__/", "*.db", "*.sqlite", "*.pem", "*.key", ".vercel/"):
        assert needed in lines, needed
    for must_track in ("data/", "partners.json", "translations", "public", "*.png", "*.json", "static/"):
        assert must_track not in lines, must_track


def test_requirements_minimal_no_auth_or_db():
    prod = (ROOT / "requirements.txt").read_text().lower()
    for bad in ("login", "sqlalchemy", "sqlite", "psycopg", "pymongo", "mysql", "jwt", "bcrypt", "cors", "firebase", "supabase"):
        assert bad not in prod
    assert [l for l in prod.split() if l] == ["flask>=3.0,<4.0"]


def test_run_py_binds_localhost_by_default():
    src = (ROOT / "run.py").read_text(encoding="utf-8")
    assert '"HOST", "127.0.0.1"' in src and "debug=False" in src


# ---------- data hygiene ----------
def test_partner_data_has_no_html_or_unsafe_urls():
    data = json.loads((ROOT / "data" / "partners.json").read_text(encoding="utf-8"))
    for p in data:
        for k, v in p.items():
            if isinstance(v, str) and k in ("name_ar", "name_en", "description_ar", "description_en"):
                assert "<" not in v and ">" not in v, (p["id"], k)
        if p["website"]:
            assert p["website"].startswith("https://"), p["id"]
        if p["logo"]:
            assert p["logo"].startswith(("/static/", "https://")) and ".." not in p["logo"], p["id"]


def test_translations_have_no_html():
    for lang in ("ar", "en"):
        d = json.loads((ROOT / "translations" / f"{lang}.json").read_text(encoding="utf-8"))
        assert not [k for k, v in d.items() if "<" in v or ">" in v]


def test_api_responses_are_json_and_safe(client):
    r = client.get("/api/partners")
    assert r.mimetype == "application/json" and len(r.get_json()) == 65
    assert r.headers.get("Cache-Control") == "no-cache"
    for p in r.get_json():
        if p["logo"]:
            assert p["logo"].startswith("/static/images/partners/") and "?v=" in p["logo"]
    r = client.get("/api/translations/ar")
    assert r.mimetype == "application/json"


# ---------- injection (SQLi / SSTI), open redirect, cookies, CORS ----------
@pytest.mark.parametrize("payload", [
    "' OR '1'='1",
    "1; DROP TABLE partners;--",
    "' UNION SELECT 1,2,3--",
    "{{77777*77777}}",
    "${77777*77777}",
    "<%= 77777*77777 %>",
])
def test_sqli_and_ssti_payloads_harmless(client, payload):
    for path in ("/", "/api/partners"):
        r = client.get(path, query_string={"q": payload, "id": payload})
        body = r.get_data(as_text=True)
        assert r.status_code == 200
        assert payload not in body and "6049261729" not in body
    r_tr = client.get(f"/api/translations/{payload}")
    assert r_tr.status_code == 404
    assert "6049261729" not in r_tr.get_data(as_text=True)
    r_path = client.get(f"/{payload}")
    assert r_path.status_code in (302, 404)
    if r_path.status_code == 302:
        assert r_path.headers["Location"] == "/"


@pytest.mark.parametrize("path", ["/foo//bar", "/%2fevil.com", "/https://evil.com", "/redirect?next=https://evil.com"])
def test_no_open_redirect_or_host_injection(client, path):
    r = client.get(path, headers={"Host": "evil.example"})
    assert r.status_code in (302, 404)
    if r.status_code == 302:
        loc = r.headers["Location"]
        assert loc == "/" and "evil" not in loc


def test_no_session_cookies_or_secret_key(client):
    app = create_app()
    assert app.secret_key is None
    for path in ("/", "/api/partners", "/api/translations/en", "/static/css/base.css"):
        r = client.get(path)
        assert "Set-Cookie" not in r.headers, path


def test_no_cors_wildcard_headers(client):
    for path in ("/", "/api/partners", "/api/translations/ar"):
        r = client.get(path, headers={"Origin": "https://evil.example"})
        assert "Access-Control-Allow-Origin" not in r.headers, path


def test_reserved_backup_and_env_prefixes_return_404(client):
    for path in ("/assets_backup", "/assets_backup/partners.before-logos.json", "/venv", "/env", "/__pycache__", "/tests"):
        assert client.get(path).status_code == 404, path


def test_app_py_disables_debug():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "debug=False" in src


def test_modals_js_rejects_backslashes_and_escapes_category():
    src = (ROOT / "public" / "static" / "js" / "modals.js").read_text(encoding="utf-8")
    assert '!url.includes("\\\\")' in src
    assert "escapeHtml(p.category)" in src
