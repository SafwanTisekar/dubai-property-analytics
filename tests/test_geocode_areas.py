"""Area centroid geocoding (ingest/geocode_areas.py): no network, a fake Nominatim."""

from __future__ import annotations

import json

from dubai_property import config
from dubai_property.ingest import geocode_areas as g


def result(name, lat=25.1, lon=55.2, *, emirate="AE-DU", category="place", name_en=None):
    """A Nominatim jsonv2 result as the search returns it (addressdetails + namedetails)."""
    names = {"name": name}
    if name_en:
        names["name:en"] = name_en
    return {
        "lat": str(lat),
        "lon": str(lon),
        "category": category,
        "name": name,
        "display_name": f"{name}, Dubai, United Arab Emirates",
        "address": {"ISO3166-2-lvl4": emirate},
        "namedetails": names,
    }


class FakeFetcher:
    """Answers from a dict query -> results and records every request."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, query):
        self.calls.append(query)
        return json.dumps(self.answers.get(query, [])).encode()


def client(tmp_path, answers):
    fetcher = FakeFetcher(answers)
    return g.Nominatim(tmp_path, fetcher=fetcher, sleep=lambda s: None), fetcher


def test_request_identifies_the_project_and_bounds_dubai():
    req = g.Nominatim.request("Al Barsha, Dubai, United Arab Emirates")
    assert req.get_header("User-agent") == config.NOMINATIM_USER_AGENT
    assert "dubai-property-analytics" in config.NOMINATIM_USER_AGENT
    assert "github.com" in config.NOMINATIM_USER_AGENT  # descriptive, with a contact URL
    assert "bounded=1" in req.full_url and "countrycodes=ae" in req.full_url
    assert "namedetails=1" in req.full_url and "addressdetails=1" in req.full_url


def test_candidates_spellings_then_alias_then_parent():
    names = [(c.query_name, c.source) for c in g.candidates("Um Suqaim First")]
    assert names[0] == ("Um Suqaim 1", g.SOURCE_EXACT)  # digit form first
    assert ("Umm Suqeim 1", g.SOURCE_EXACT) in names
    assert names[-1] == ("Umm Suqeim", g.SOURCE_APPROX)
    assert [c.source for c in g.candidates("Marsa Dubai")] == [g.SOURCE_EXACT, g.SOURCE_ALIAS]
    # A one-word parent would match anything, so it is never tried.
    assert [c.query_name for c in g.candidates("Island 2")] == ["Island 2"]
    assert g.clean_name("Al-Riqqa  East") == "Al Riqqa East"
    assert g.clean_name("Al Layan1") == "Al Layan 1"


def test_name_must_match_and_lie_in_dubai():
    good = result("Al Barsha South 4")
    assert g.pick([good], "Al Barsha South Fourth") is good  # "Fourth" == "4"
    # Nominatim's loose match: a hotel, or a differently named place, is rejected.
    assert g.pick([result("Marsa Dubai Hotel", category="tourism")], "Marsa Dubai") is None
    assert g.pick([result("Marsa Al Arab Villas")], "Marsa Dubai") is None
    # Sharjah is next door; the emirate code decides.
    assert g.pick([result("Al Nahda 1", emirate="AE-SH")], "Al Nahda 1") is None
    # Inside AE-DU but outside the box (bad coordinates) is rejected too.
    assert g.pick([result("Al Nahda 1", lat=26.5)], "Al Nahda 1") is None
    # The English name tag counts when the main name is Arabic.
    assert g.pick([result("الخليج التجاري", name_en="Business Bay")], "Business Bay")


def test_geocode_keeps_manual_rows_and_never_falls_back(tmp_path):
    rows = [
        {"area_id": "1", "area_name_en": "Business Bay", "zone": "Z", "latitude": "",
         "longitude": "", "centroid_source": ""},
        {"area_id": "2", "area_name_en": "Nowhere Second", "zone": "Z", "latitude": "1",
         "longitude": "2", "centroid_source": g.SOURCE_EXACT},
        {"area_id": "3", "area_name_en": "Hand Placed", "zone": "Z", "latitude": "25.0",
         "longitude": "55.0", "centroid_source": g.SOURCE_MANUAL},
    ]  # fmt: skip
    answers = {g.query_string("Business Bay"): [result("Business Bay", 25.18, 55.27)]}
    nominatim, fetcher = client(tmp_path, answers)
    log = g.geocode(rows, nominatim)
    assert rows[0]["latitude"] == "25.180000" and rows[0]["centroid_source"] == g.SOURCE_EXACT
    # Not found now: the old centroid is cleared, not kept or replaced by a zone point.
    assert rows[1]["latitude"] == "" and rows[1]["centroid_source"] == ""
    assert rows[2]["latitude"] == "25.0" and rows[2]["centroid_source"] == g.SOURCE_MANUAL
    assert not any("Hand Placed" in q for q in fetcher.calls)  # manual rows aren't queried
    assert [r["outcome"] for r in log] == [g.SOURCE_EXACT, "not found", g.SOURCE_MANUAL]


def test_cache_means_no_second_request(tmp_path):
    answers = {g.query_string("Business Bay"): [result("Business Bay")]}
    nominatim, fetcher = client(tmp_path, answers)
    nominatim.search(g.query_string("Business Bay"))
    again, fetcher2 = client(tmp_path, answers)
    again.search(g.query_string("Business Bay"))
    assert len(fetcher.calls) == 1 and fetcher2.calls == [] and again.network_calls == 0


def test_seed_round_trip_adds_the_source_column(tmp_path):
    path = tmp_path / "seed_area.csv"
    path.write_text('area_id,area_name_en,zone,latitude,longitude\n1,A,"Z, Y",,\n')
    rows = g.read_seed(path)
    assert rows[0]["centroid_source"] == ""
    g.write_seed(rows, path)
    assert path.read_text() == (
        'area_id,area_name_en,zone,latitude,longitude,centroid_source\n1,A,"Z, Y",,,\n'
    )


def test_committed_seed_is_consistent():
    rows = g.read_seed()
    lon_min, lat_min, lon_max, lat_max = config.DUBAI_BBOX
    for r in rows:
        located = bool(r["latitude"])
        assert located == bool(r["longitude"]) == bool(r["centroid_source"]), r
        if located:
            assert lat_min <= float(r["latitude"]) <= lat_max, r
            assert lon_min <= float(r["longitude"]) <= lon_max, r
