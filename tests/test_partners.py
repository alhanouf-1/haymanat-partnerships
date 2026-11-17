import json
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "partners.json"
partners = json.loads(DATA.read_text(encoding="utf-8"))

CATEGORIES = {"organizations", "clubs", "volunteer_teams", "initiatives", "hackathons"}
PERIODS = {"2025", "2026_H1", "2026_H2"}


def test_total_count():
    assert len(partners) == 65


def test_category_counts():
    c = Counter(p["category"] for p in partners)
    assert c == {"organizations": 14, "clubs": 19, "volunteer_teams": 4, "initiatives": 21, "hackathons": 7}


def test_period_counts_per_category():
    c = Counter((p["category"], p["period"]) for p in partners)
    expected = {
        ("organizations", "2025"): 2, ("organizations", "2026_H1"): 4, ("organizations", "2026_H2"): 8,
        ("clubs", "2025"): 5, ("clubs", "2026_H1"): 3, ("clubs", "2026_H2"): 11,
        ("volunteer_teams", "2026_H1"): 2, ("volunteer_teams", "2026_H2"): 2,
        ("initiatives", "2025"): 8, ("initiatives", "2026_H1"): 5, ("initiatives", "2026_H2"): 8,
        ("hackathons", "2025"): 2, ("hackathons", "2026_H1"): 4, ("hackathons", "2026_H2"): 1,
    }
    assert c == expected


def test_valid_values_and_unique_ids():
    ids = [p["id"] for p in partners]
    assert len(ids) == len(set(ids))
    for p in partners:
        assert p["category"] in CATEGORIES
        assert p["period"] in PERIODS
        assert p["name_ar"] and p["name_ar"].strip()


def test_duplicate_bareeq_preserved():
    dups = [p for p in partners if p["name_ar"] == "مبادرة بريق"]
    assert len(dups) == 2
    assert {p["period"] for p in dups} == {"2025", "2026_H2"}
    assert dups[0]["id"] != dups[1]["id"]


def test_no_unintended_duplicate_names():
    names = Counter(p["name_ar"] for p in partners)
    assert [n for n, k in names.items() if k > 1] == ["مبادرة بريق"]


def test_no_invented_fields():
    for p in partners:
        assert p["description_ar"] is None and p["description_en"] is None
        assert p["logo"] is None and p["website"] is None
