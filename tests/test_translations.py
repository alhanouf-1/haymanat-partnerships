import json
from pathlib import Path

T = Path(__file__).resolve().parent.parent / "translations"
ar = json.loads((T / "ar.json").read_text(encoding="utf-8"))
en = json.loads((T / "en.json").read_text(encoding="utf-8"))


def test_identical_keys():
    assert set(ar) == set(en)


def test_no_empty_values():
    assert all(v.strip() for v in ar.values())
    assert all(v.strip() for v in en.values())


def test_required_translations():
    required = {
        "nav.home": ("الرئيسية", "Home"),
        "nav.partners": ("شركاء النجاح", "Success Partners"),
        "hero.cta": ("استكشف شركاءنا", "Explore Our Partners"),
        "category.all": ("جميع الشراكات", "All Partnerships"),
        "category.organizations": ("الجهات والمؤسسات", "Organizations & Institutions"),
        "category.clubs": ("الأندية والمجموعات", "Clubs & Communities"),
        "category.volunteer_teams": ("الفرق التطوعية", "Volunteer Teams"),
        "category.initiatives": ("المبادرات", "Initiatives"),
        "category.hackathons": ("الهاكاثونات", "Hackathons"),
        "search.placeholder": ("ابحث عن شريك نجاح...", "Search for a Partner..."),
        "period.all": ("جميع الفترات", "All Periods"),
        "period.2026_H1": ("النصف الأول من 2026", "First Half of 2026"),
        "period.2026_H2": ("النصف الثاني من 2026", "Second Half of 2026"),
        "card.view_details": ("عرض التفاصيل", "View Details"),
        "empty.title": ("لا توجد نتائج", "No Results Found"),
        "stats.total": ("إجمالي الشراكات", "Total Partnerships"),
        "about.title": ("من نحن", "About Us"),
        "hero.title": ("شركاء النجاح، أثر يجمعنا", "Success Partners, United by Impact"),
    }
    for key, (a, e) in required.items():
        assert ar[key] == a, key
        assert en[key] == e, key


def test_placeholders_match():
    import re
    for k in ar:
        assert sorted(re.findall(r"\{\w+\}", ar[k])) == sorted(re.findall(r"\{\w+\}", en[k])), k


def test_used_keys_exist():
    """Every data-i18n key in templates and t('...') key in JS exists."""
    import re
    root = Path(__file__).resolve().parent.parent / "frontend"
    PUBLIC = Path(__file__).resolve().parent.parent / "public"
    text = (root / "templates" / "index.html").read_text(encoding="utf-8")
    keys = set(re.findall(r'data-i18n="([\w.]+)"', text))
    for pair in re.findall(r'data-i18n-attr="([^"]+)"', text):
        keys |= {p.split(":")[1] for p in pair.split(";")}
    for js in (PUBLIC / "static" / "js").glob("*.js"):
        keys |= set(re.findall(r'\bt\("([\w.]+)"', js.read_text(encoding="utf-8")))
    # Keys ending in "." are dynamic prefixes (e.g. "category." + id), checked by other tests.
    missing = {k for k in keys if not k.endswith(".") and k not in ar}
    assert not missing, missing
