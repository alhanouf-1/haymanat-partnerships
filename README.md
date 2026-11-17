# Haymanat Alnajah | هيمنة النجاح — Partnerships Showcase

A public, read-only, bilingual (Arabic / English) interactive showcase of Haymanat Alnajah's 65 success partnerships. Flask + Jinja2 backend, vanilla HTML/CSS/JS frontend, local JSON data. No database, no login, no admin, no write endpoints.

## 1. Folder structure

```text
haymanat-partnerships/
├── backend/               Flask app (app.py) + routes/public_routes.py (read-only)
├── frontend/
│   ├── templates/         base.html, index.html (Jinja2)
├── public/static/         css/ js/ images/ (logo) fonts/ (served by Vercel CDN at /static/...)
├── app.py                 Vercel entrypoint (exposes top-level Flask pp)
├── vercel.json            includes templates/data/translations in the function bundle
├── .python-version        3.13
├── translations/          ar.json, en.json (identical keys)
├── data/partners.json     the 65 partnership records (edit this by hand)
├── tests/                 pytest suite
├── run.py                 local entry point
└── requirements.txt
```

## 2. Requirements

Python 3.13 (3.10+ should also work). Production dependency: Flask only (equirements.txt). equirements-dev.txt adds pytest and waitress.

## 3. Install

```powershell
cd haymanat-partnerships
py -3.13 -m venv .venv
.venv\Scripts\activate
py -3.13 -m pip install -r requirements-dev.txt
```

## 4. Run locally

```powershell
py -3.13 run.py        # or: python run.py
```

Open **http://127.0.0.1:5000** (this is the Flask app — not a static server such as Live Server on port 5500). Change the port with `$env:PORT=8000`.

## 5. Tests

```powershell
py -3.13 -m pytest -q
```

Covers the 65 records, category/period counts, the duplicate «مبادرة بريق», translation key parity, routes, assets, and the absence of admin/write routes.

## 6. Editing partners (`data/partners.json`)

Each record:

```json
{
  "id": "org-001",
  "name_ar": "جمعية وطن طموح",
  "name_en": null,
  "category": "organizations",
  "period": "2025",
  "description_ar": null,
  "description_en": null,
  "logo": null,
  "website": null
}
```

- `category`: `organizations`, `clubs`, `volunteer_teams`, `initiatives`, `hackathons`.
- `period`: `2025`, `2026_H1`, `2026_H2`.
- `id` must be unique and stable. Two records are named «مبادرة بريق» (2025 and 2026_H2) — keep both.
- `name_en`: only fill with a verified English name; when `null`, the Arabic name is shown in English mode.
- `description_*`, `website` (http/https only): shown in the modal only when filled.
- `logo`: URL or path such as `/static/images/partners/x.png`; when `null`, a category icon is shown.
- Statistics are computed from this file automatically. Back up the file before big edits; restart the server (or reload) after changes.

## 7. Editing translations

Edit `translations/ar.json` and `translations/en.json`. Keys must stay identical in both (the tests enforce this). Use `{count}`-style placeholders consistently.

## 8. Replacing the logo

Replace `public/static/images/haymanat-logo.png` with the new official file (same filename, ideally 16:9). Do not recolor or crop it.

## 9. Deploy to GitHub + Vercel

Layout follows Vercel's Flask support: root `app.py` exposes `app`; static assets live in `public/` (served by the CDN, so `public/static/css/base.css` is available at `/static/css/base.css`); `vercel.json` bundles `frontend/` (templates), `data/`, `translations/` and `backend/` into the function. `.python-version` pins 3.13.

1. `git init`, commit everything (`data/partners.json`, `translations/` and the logo are tracked; `.venv`, `.env`, caches are ignored), push to a new GitHub repository.
2. In Vercel: **Add New -> Project**, import the repo. Framework preset: Flask/Other; no build command, no environment variables needed.
3. Deploy and share the generated `*.vercel.app` URL (or add a custom domain).

Unknown page URLs redirect to the homepage; missing assets under `/static/` return a real 404.

Other Python hosts: `py -3.13 -m waitress --listen=0.0.0.0:8000 run:app` (or gunicorn `run:app` on Linux). Never use `run.py` (Flask dev server) in production.