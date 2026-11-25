# Security Audit Report — Haymanat Alnajah Partnerships Showcase

**Audit Date:** 2026-11-25
**Scope:** Local source code, static assets, configuration, and Flask test-client verification (`haymanat-partnerships`)
**Application Type:** Read-only bilingual (Arabic/English) Python Flask showcase backed by local JSON files (no database, no user accounts, no admin interface, no file upload).

---

## 1. Executive Summary

The application has a small attack surface by design: it exposes only three `GET` routes (`/`, `/api/partners`, `/api/translations/<lang>`), uses no database, stores no user credentials, sets no cookies or sessions, and runs with `DEBUG=False` and strict HTTP security headers (`Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, COOP, CORP, and conditional/Vercel HSTS).

During this audit:
- **No Critical or High vulnerabilities** were found.
- **4 Low-severity / hygiene issues** were identified and fixed safely without altering UI, layout, text, or partnership data.
- **2 Repository-hygiene warnings** (untracked stray terminal dump file and untracked `assets_backup/` directory) were left untouched per the non-deletion policy and are documented for user action before pushing to GitHub.
- **1 Automated check (`pip-audit`)** could not complete in this offline environment because it queries PyPI/OSV over the network; exact installed package versions are listed in Section 8 for online/CI verification.

---

## 2. Security Checks Performed

1. **Project Structure & Configuration Inspection:** Reviewed `app.py`, `run.py`, `backend/app.py`, `backend/assets.py`, `backend/security.py`, `backend/routes/public_routes.py`, `vercel.json`, `requirements.txt`, `requirements-dev.txt`, `.python-version`, `.gitignore`, and `git status`.
2. **Template & Client-Side Code Review:** Inspected `frontend/templates/base.html`, `frontend/templates/index.html`, and all JavaScript files under `public/static/js/` (`boot.js`, `i18n.js`, `search.js`, `filters.js`, `modals.js`, `main.js`).
3. **Static Analysis:** Ran `bandit -r app.py run.py backend`.
4. **Automated Security & Regression Test Suite:** Executed `pytest` against Flask's `test_client()` (`tests/test_security.py`, `tests/test_routes.py`, `tests/test_partners.py`, `tests/test_translations.py`) plus `node --check` on all JavaScript modules.
5. **Vulnerability Categories Assessed:**
   - **Injection:** SQLi, command injection, Jinja2 SSTI, `eval`/`Function`, unsafe deserialization (`pickle`/`yaml`).
   - **Web Security:** Reflected/DOM XSS, CSRF, path traversal, open redirects / Host header injection, HTTP method restrictions, cookies/sessions, CSP and security headers.
   - **Flask Configuration:** Secret keys, `DEBUG`/`TESTING` flags, error handlers (`404`, `405`, `413`, `500`), `MAX_CONTENT_LENGTH`, CORS headers.
   - **API & Data Security:** Read-only enforcement, JSON content types, `partners.json` / translation content hygiene, exposure of `.env`, `.git`, source files, or backups.

---

## 3. Vulnerabilities & Findings Discovered

| ID | Severity | Status | File / Location | Description & Potential Impact |
|---|---|---|---|---|
| **F-01** | **Low** | **Fixed** | `app.py` (line 7) | `app.run()` was called without `debug=False`. While Flask defaults to `debug=False`, setting `FLASK_DEBUG=1` in the environment could enable the interactive Werkzeug debugger if `app.py` were launched directly. |
| **F-02** | **Low** | **Fixed** | `backend/app.py` (`RESERVED_PREFIXES`, lines 14–19) | Paths without a dot such as `/assets_backup`, `/venv`, `/env`, `/node_modules`, and `/__pycache__` fell into the 404 catch-all redirect (`302 -> /`) instead of returning `404 Not found`. No file contents were exposed, but scanners interpret `302` on sensitive prefixes ambiguously. |
| **F-03** | **Low** | **Fixed** | `public/static/js/modals.js` (lines 17, 38) | `safeLogoUrl()` checked `!url.includes("..")` for `/static/` paths without rejecting backslashes (`\\`), and the modal SVG fallback `<use href="#i-${p.category}"/>` did not wrap `p.category` in `escapeHtml()` (mitigated by `loadPartners()` validation in `main.js`, hardened for defense-in-depth). |
| **F-04** | **Low** | **Fixed** | `tests/test_partners.py` (`test_no_invented_fields`, lines 54–57) | Outdated test asserted `p["logo"] is None` for every partner, causing `pytest` to fail after 53 partner logos were integrated into `data/partners.json`. |
| **W-01** | **Low (Repo Hygiene)** | **Open — User Action** | Workspace root: stray untracked file (`ite*`) and `assets_backup/` | `git status` shows an untracked 16 KB accidental `less` help dump file (`ite` + private-use character) and the untracked `assets_backup/` directory (51 original logos + pre-logo JSON backup). Neither is excluded by `.gitignore`. `git add .` would commit them to GitHub (Vercel excludes them because neither is in `public/` or `vercel.json` `includeFiles`). |
| **W-02** | **Info** | **Accepted / Advisory** | `requirements.txt` (line 1) | `Flask>=3.0,<4.0` uses a major-version range rather than exact pinned versions (`==`), allowing minor/patch drift between local builds and Vercel deployments. |
| **W-03** | **Info** | **Accepted / Advisory** | `backend/security.py` (line 7) | CSP `img-src 'self' data: https:` allows external `https:` image origins and `data:` URIs (`data:image/svg+xml` is used in `public/static/css/components.css` for `.period-select`). Safe for a read-only site, though `'self' data:` would be slightly tighter if external HTTPS partner logos are never used. |
| **W-04** | **Info** | **Accepted** | `backend/assets.py` (line 10) | Uses `hashlib.sha1(..., usedforsecurity=False)` solely to compute `?v=<hash>` cache-busting tokens for static assets. Non-cryptographic use; acceptable and flagged as clean by Bandit. |

---

## 4. Controls Verified as Secure (PASS)

- **No Auth / Admin / Database Attack Surface:** Zero login, registration, admin, SQL, ORM, or file-upload code exists. All Flask routes accept `GET`/`HEAD`/`OPTIONS` only; `POST`/`PUT`/`PATCH`/`DELETE` return `405` or `404`.
- **No Secrets or Local Machine Paths:** Regex scans across all repository text files found no API keys, private keys, tokens, `.env` files, `.db`/`.sqlite` files, or local filesystem paths.
- **No XSS / Injection / SSTI:**
  - Jinja2 autoescaping is active; zero `|safe`, `Markup()`, or `render_template_string()` calls exist.
  - Zero inline `<script>`, inline `style=`, or inline `on*` handlers exist in HTML or JS templates (`boot.js` is externalized; broken images use a capture listener).
  - All user-visible strings and `data/partners.json` fields rendered via `innerHTML` pass through `escapeHtml()`, `safeLogoUrl()`, or `safeUrl()`, and `loadPartners()` filters records by strict ID (`/^[\\w-]+$/`), category, and period allowlists.
- **Path Traversal & Sensitive File Protection:**
  - `/api/translations/<lang>` strictly allowlists `("ar", "en")`.
  - `backend/assets.py` resolves `static_folder` and verifies `base in target.parents`.
  - Requests to `/.env`, `/.git/config`, `/requirements.txt`, `/backend/app.py`, `/data/partners.json`, `/translations/ar.json`, `/vercel.json`, `/app.py`, `/run.py`, `/__debugger__`, `/admin`, `/login`, and encoded traversal attempts return `404`.
  - Directory listing is disabled across `/static/` and subdirectories.
- **Flask Production Settings & Headers:**
  - `create_app()` forces `DEBUG=False`, `TESTING=False`, `MAX_CONTENT_LENGTH=16384`, sets no `secret_key`, emits no cookies, and emits no wildcard CORS headers.
  - Generic error handlers (`404`, `405`, `413`, `500`) disclose no stack traces or Werkzeug debugger output.
  - `backend/security.py` and `vercel.json` both enforce strict CSP (no `'unsafe-inline'` or `'unsafe-eval'`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, COOP, CORP, and HSTS (`Strict-Transport-Security` on HTTPS / Vercel).
- **External Link Safety:** The Google Forms link in `frontend/templates/index.html` uses `target="_blank" rel="noopener noreferrer"`.

---

## 5. Fixes Implemented

1. **`app.py` (line 7):** Changed `app.run()` to `app.run(debug=False)`.
2. **`backend/app.py` (line 17):** Added `"assets_backup"`, `"venv"`, `"env"`, `"node_modules"`, `"__pycache__"` to `RESERVED_PREFIXES` so requests to those prefixes return `404` instead of redirecting.
3. **`public/static/js/modals.js` (lines 17, 38):** Added `!url.includes("\\\\")` to `safeLogoUrl()` and wrapped `p.category` in `escapeHtml(p.category)` inside the SVG `<use>` fallback.
4. **`tests/test_partners.py` (lines 54–59):** Updated `test_no_invented_fields()` to validate that populated `logo` paths start with `/static/images/partners/`, contain no `..`, and exist on disk under `public/`.
5. **`tests/test_security.py` (lines 259–327):** Added regression tests for SQLi/SSTI payloads, open-redirect/Host-header injection, absence of `Set-Cookie`/`secret_key`/CORS headers, reserved backup/env prefixes returning `404`, `app.py` `debug=False`, `modals.js` hardening, and `/api/partners` cache-busting headers.

---

## 6. Tests Executed & Results

| Tool / Suite | Scope | Result |
|---|---|---|
| `pytest -q` | Full suite (`tests/test_partners.py`, `test_routes.py`, `test_security.py`, `test_translations.py`) | **135 passed** |
| `bandit -r app.py run.py backend` | All Python backend & entrypoint code | **0 issues** (Low/Medium/High: 0) |
| `node --check` | All 6 JS files in `public/static/js/` | **Syntax OK** |

---

## 7. Remaining Risks & Recommendations

1. **Remove stray terminal file before `git add`:** Delete the untracked `ite*` (`less` help output) file in the project root before committing to GitHub.
2. **Decide on `assets_backup/` tracking:** If you do not want the 12+ MB backup archive in GitHub, add `assets_backup/` to `.gitignore`. (Vercel already excludes it from deployment.)
3. **Consider exact dependency pinning (optional):** Pin `Flask==3.1.3` (or generate a lockfile) in `requirements.txt` for deterministic Vercel builds.

---

## 8. Checks That Could Not Be Completed (Require Manual / Online Verification)

1. **`pip-audit` (Known Dependency CVEs):** Could not complete locally because this offline sandbox blocks outbound HTTPS requests to PyPI/OSV (`Failed to upgrade pip` / no network). Run `py -3.13 -m pip_audit -r requirements.txt` and `py -3.13 -m pip_audit -r requirements-dev.txt` from an online terminal or GitHub Actions before/after pushing.
   - Observed local `.venv` versions: `Flask 3.1.3`, `Werkzeug 3.1.9`, `Jinja2 3.1.6`, `MarkupSafe 3.0.4`, `itsdangerous 2.2.0`, `click 8.5.1`, `blinker 1.9.0`.
   - Observed global Python 3.13.4 versions: `Flask 3.1.3`, `Werkzeug 3.1.8`, `Jinja2 3.1.6`, `MarkupSafe 3.0.3`, `itsdangerous 2.2.0`, `click 8.4.2`, `blinker 1.9.0`, `waitress 3.0.2`.
2. **Live Browser Verification under Strict CSP & Logo Rendering:** Interactive browser checks (DevTools Console CSP check, RTL/LTR toggle, search/filters, modal rendering for all 53 logos including Wajeez and Aus Volunteer Team) were not executed in Chrome during this audit. Open the site locally (`py -3.13 run.py`) and verify zero CSP errors in DevTools Console.
3. **Live Vercel Edge Headers:** After deploying to Vercel, run `python tests/security_check.py https://<your-app>.vercel.app` to verify CDN headers, HSTS, and static asset responses in production.
4. **Penetration Testing / Third-Party Hosted Links:** Automated tests cannot guarantee complete security; `forms.gle` is a third-party external form link outside this codebase's control.

---

## 9. Final Deployment Readiness

### Verified Items (Confirmed in Current Source & Automated Tests)

- **Reported Fixes Confirmed in Code:**
  - `app.py` line 7 sets `app.run(debug=False)`.
  - `backend/app.py` lines 14–19 include `assets_backup`, `venv`, `env`, `node_modules`, and `__pycache__` in `RESERVED_PREFIXES`.
  - `public/static/js/modals.js` lines 17 and 38 reject `\\` in `safeLogoUrl()` and apply `escapeHtml(p.category)` in the SVG fallback.
  - `tests/test_partners.py` lines 54–61 enforce `description_ar is None`, `description_en is None`, `website is None`, and valid local `logo` files under `public/static/images/partners/`.
- **Dependencies (`requirements.txt` / `requirements-dev.txt`):**
  - `requirements.txt` contains only `Flask>=3.0,<4.0` (no auth, database, ORM, or CORS packages). `requirements-dev.txt` adds `pytest>=8.0` and `waitress>=3.0` for local testing/WSGI serving only.
  - Risk note: both files use version ranges rather than exact pins (`==`), which permits minor/patch version drift at deploy time.
- **CSP `img-src` Review (`'self' data: https:`):**
  - `'self'` is required for the official logo, favicon, and all 53 partner logos.
  - `data:` is required for existing UI because `public/static/css/components.css` line 78 renders the `.period-select` dropdown arrow via `data:image/svg+xml`.
  - `https:` is unused by current `partners.json` records (all local `/static/`), kept only to support optional future `https://` logos in `safeLogoUrl()`.
- **Production Configuration:**
  - Debug mode is forced off (`DEBUG=False`, `TESTING=False`), no `SECRET_KEY` or `.env` secrets are stored or required, and no cookies or Flask sessions are emitted (`Set-Cookie` absent).
  - `backend/security.py` and `vercel.json` enforce matching strict CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, COOP, CORP, and HSTS (`max-age=31536000; includeSubDomains` when served over HTTPS / `X-Forwarded-Proto: https`).
- **Repository Hygiene Findings (Unmodified — Awaiting User Action):**
  - **Accidental `ite*` file:** Untracked 16,653-byte file (`ite` + Unicode `U+F022`, created 2026-11-17) in the project root containing a `less` command help dump. Not deleted; remove manually with approval before committing so it is not pushed to GitHub or rejected by cross-platform tooling.
  - **`assets_backup/` directory:** Untracked folder (52 files, ~10.71 MB: 51 original unoptimized logos + `partners.before-logos.json`) not currently in `.gitignore`. Recommendation: add `assets_backup/` to `.gitignore` before pushing to GitHub unless you explicitly want those backups stored in the public repository. (Vercel already ignores it.)

### Items Requiring Manual / Online Verification (Incomplete)

1. **Dependency Vulnerability Audit (`pip-audit`):** Re-attempted in this environment for both `requirements.txt` and `requirements-dev.txt`; **failed offline** (`ERROR:pip_audit._cli:Failed to upgrade pip` due to no outbound network access to PyPI/OSV). **The dependency audit remains incomplete** until run online: `py -3.13 -m pip_audit -r requirements.txt` and `py -3.13 -m pip_audit -r requirements-dev.txt`.
2. **Browser & Visual CSP Check:** Verify in a live browser (`py -3.13 run.py` and after Vercel deploy) that DevTools Console reports zero CSP violations and that Arabic/English switching, search, filters, and all 53 partner logos (cards + modals) render properly.
3. **Production Deployment Verification:** After deploying to Vercel, run `python tests/security_check.py https://<your-app>.vercel.app` to confirm HTTPS, HSTS, security headers, and static CDN behavior on the live URL.
4. **Inherent Limits:** Automated checks do not substitute for a manual penetration test and cannot guarantee complete security; the external Google Form (`forms.gle`) is outside this repository's control.
