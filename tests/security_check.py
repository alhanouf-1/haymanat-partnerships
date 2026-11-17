
import sys
import requests
from urllib.parse import urljoin

BASE = (
    sys.argv[1].rstrip("/")
    if len(sys.argv) > 1
    else "http://127.0.0.1:5000"
)

session = requests.Session()
session.headers.update({"User-Agent": "Haymanat-Security-Audit/1.0"})
results = []


def result(status, name, detail=""):
    results.append((status, name))
    print(f"[{status}] {name}")
    if detail:
        print(f"    {detail}")


def request(method, path, **kwargs):
    url = urljoin(BASE + "/", path.lstrip("/"))
    return session.request(
        method,
        url,
        timeout=8,
        allow_redirects=False,
        **kwargs
    )


print(f"\nSecurity audit: {BASE}\n")

# 1. Homepage
try:
    response = request("GET", "/")
    if response.status_code == 200:
        result("PASS", "Homepage is accessible")
    else:
        result("FAIL", "Homepage", f"HTTP {response.status_code}")
except requests.RequestException as exc:
    print(f"Cannot connect: {exc}")
    sys.exit(1)


# 2. Security headers
headers = response.headers

required = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": None,
    "Referrer-Policy": None,
    "Content-Security-Policy": None,
}

for name, expected in required.items():
    value = headers.get(name)

    if name == "X-Frame-Options":
        csp = headers.get("Content-Security-Policy", "")
        protected = (
            value in ("DENY", "SAMEORIGIN")
            or "frame-ancestors" in csp
        )
    else:
        protected = bool(value) and (
            expected is None or value.lower() == expected
        )

    result(
        "PASS" if protected else "WARN",
        f"Security header: {name}",
        value or "Missing or not configured"
    )

if BASE.startswith("https://"):
    hsts = headers.get("Strict-Transport-Security")
    result(
        "PASS" if hsts else "WARN",
        "HSTS on HTTPS",
        hsts or "Missing"
    )


# 3. Sensitive files
sensitive_paths = [
    "/.env",
    "/.git/config",
    "/requirements.txt",
    "/backend/app.py",
    "/data/partners.json",
    "/instance/partnerships.db",
    "/__debugger__",
]

for path in sensitive_paths:
    try:
        r = request("GET", path)

        # 200 may mean real file exposure or an SPA fallback.
        if r.status_code == 200:
            status = "WARN" if path == "/data/partners.json" else "FAIL"
        elif r.status_code in (401, 403, 404, 410):
            status = "PASS"
        else:
            status = "WARN"

        result(status, f"File exposure: {path}", f"HTTP {r.status_code}")

    except requests.RequestException as exc:
        result("WARN", f"File exposure: {path}", str(exc))


# 4. Removed admin routes
admin_paths = ["/admin", "/login", "/admin/login"]

for path in admin_paths:
    try:
        r = request("GET", path)
        status = (
            "PASS"
            if r.status_code in (404, 410)
            else "WARN"
        )
        result(status, f"Removed route: {path}", f"HTTP {r.status_code}")
    except requests.RequestException as exc:
        result("WARN", f"Removed route: {path}", str(exc))


# 5. Detect methods without modifying data
for path in ["/", "/api/partners", "/partners"]:
    try:
        r = request("OPTIONS", path)
        allowed = r.headers.get("Allow", "")

        risky = {
            item.strip().upper()
            for item in allowed.split(",")
        } & {"POST", "PUT", "PATCH", "DELETE"}

        if risky:
            result(
                "WARN",
                f"Write methods advertised: {path}",
                ", ".join(sorted(risky))
            )
        else:
            result(
                "PASS",
                f"No write methods advertised: {path}",
                allowed or f"HTTP {r.status_code}"
            )
    except requests.RequestException as exc:
        result("WARN", f"HTTP methods: {path}", str(exc))


# 6. Server error disclosure
try:
    r = request("GET", "/this-route-should-not-exist-84729")

    indicators = [
        "traceback (most recent call last)",
        "werkzeug debugger",
        "debugger pin",
    ]

    exposed = any(x in r.text.lower() for x in indicators)

    result(
        "FAIL" if exposed else "PASS",
        "Error information disclosure",
        f"HTTP {r.status_code}"
    )
except requests.RequestException as exc:
    result("WARN", "Error information disclosure", str(exc))


# 7. Basic XSS reflection probe
payload = "<script>window.__security_probe=1</script>"

try:
    r = request("GET", "/", params={"q": payload})

    reflected = payload in r.text

    result(
        "WARN" if reflected else "PASS",
        "Raw HTML reflection check",
        "Unescaped probe reflected"
        if reflected else "No raw probe reflected"
    )
except requests.RequestException as exc:
    result("WARN", "Raw HTML reflection check", str(exc))


# 8. Final summary
print("\n" + "=" * 48)
print("SECURITY AUDIT SUMMARY")
print("=" * 48)

for status in ("PASS", "WARN", "FAIL"):
    count = sum(1 for s, _ in results if s == status)
    print(f"{status}: {count}")

print("\nNotes:")
print("- WARN results require manual review.")
print("- OPTIONS does not prove write methods are blocked.")
print("- The XSS check does not test DOM-based XSS.")
print("- Public partner JSON may be intentionally accessible.")
print("- These checks are not a full penetration test.")
