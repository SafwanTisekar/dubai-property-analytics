"""Area centroids for the Power BI bubble map → ``dbt/seeds/seed_area.csv`` (docs/06 §4).

DLD publishes no coordinates, so each area's centroid comes from OpenStreetMap Nominatim
(owner decision, 2026-10-01). Only the public DLD area name is sent, as
``"<name>, Dubai, United Arab Emirates"``, with the descriptive User-Agent and the
1-request-per-second limit the Nominatim usage policy asks for. Every raw response is
cached under ``data/raw/osm/nominatim/`` (gitignored), so a re-run makes no network calls.

How a centroid is chosen, and recorded in ``centroid_source``:

* ``osm_nominatim``: the DLD name, or a spelling of it (ordinal words as digits or "1st",
  "Al-" as "Al "), found inside Dubai: the result must be an area feature (OSM category
  place / boundary / landuse, not a hotel or road of the same name), its OSM address in
  emirate ``AE-DU`` *and* inside ``config.DUBAI_BBOX`` (Sharjah and Ajman are next door).
* ``osm_nominatim_alias``: found under a better-known name for the same place (``ALIASES``,
  e.g. DLD's "Marsa Dubai" is Dubai Marina). Listed in the report for review.
* ``osm_nominatim_approx``: only the parent community was found (the name without its
  "First" / "2" / ... suffix). Close, but several sub-areas then share one point; listed
  for review.
* ``manual``: typed in by the owner. Never overwritten.
* blank: not found. The bubble map leaves the area out; there is **no** silent fallback
  to a zone centroid, which would put a bubble somewhere the area isn't.

Writes the seed in place (only latitude / longitude / centroid_source change) and
``reports/area_centroids.md``, which lists every miss, alias and approximation as the
owner's review list. Then ``make dbt`` loads the seed into ``dim_area`` / ``rpt.dim_area``.

Usage::

    uv run python -m dubai_property.ingest.geocode_areas [--refresh]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dubai_property import config
from dubai_property.quality.dq_report import md_table

log = logging.getLogger(__name__)

SEED_PATH = config.DBT_DIR / "seeds" / "seed_area.csv"
REPORT_NAME = "area_centroids.md"
TIMEOUT_SECONDS = 30
SEED_COLUMNS = ["area_id", "area_name_en", "zone", "latitude", "longitude", "centroid_source"]

# Bump when the request parameters change, so cached responses of the old request are ignored.
CACHE_VERSION = "v2-namedetails"

SOURCE_EXACT = "osm_nominatim"
SOURCE_ALIAS = "osm_nominatim_alias"
SOURCE_APPROX = "osm_nominatim_approx"
SOURCE_MANUAL = "manual"

ORDINALS = {
    "first": ("1", "1st"),
    "second": ("2", "2nd"),
    "third": ("3", "3rd"),
    "fourth": ("4", "4th"),
    "fifth": ("5", "5th"),
    "sixth": ("6", "6th"),
    "seventh": ("7", "7th"),
}
# DLD spellings -> common OSM spellings (word level, applied before the ordinal variants).
SPELLINGS = {
    "um": "umm",
    "jabal": "jebel",
    "barshaa": "barsha",
    "thanayah": "thanyah",
    "muhaisanah": "muhaisnah",
    "suqaim": "suqeim",
    "goze": "quoz",
    "safouh": "sufouh",
    "center": "centre",
    "shiba": "sheba",
    "yelayiss": "yalayis",
    "zaabeel": "za'abeel",
}
# DLD names whose place is known in OSM under another name. Kept short and reviewed: each
# hit is labelled osm_nominatim_alias in the seed and listed in the report.
ALIASES: dict[str, tuple[str, ...]] = {
    "Marsa Dubai": ("Dubai Marina",),
    "Madinat Dubai Almelaheyah": ("Mina Rashid", "Port Rashid"),
    "Hadaeq Sheikh Mohammed Bin Rashid": ("Mohammed Bin Rashid City",),
    "Burj Khalifa": ("Downtown Dubai",),
    "Al Merkadh": ("Al Merkad",),
    "Palm Jabal Ali": ("Palm Jebel Ali",),
    "Mena Jabal Ali": ("Mina Jebel Ali",),
    "Al Khairan First": ("Dubai Creek Harbour",),
    # Seed clarification of DLD's "Island 2" (its master project is Jumeira Bay).
    "Island 2 (Jumeira Bay)": ("Island 2", "Jumeira Bay"),
}
_SUFFIX = re.compile(
    r"\s+(?:" + "|".join(ORDINALS) + r"|\d+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Candidate:
    """One query to try, and the centroid_source a hit on it earns."""

    query_name: str
    source: str


@dataclass(frozen=True)
class Hit:
    """A centroid found for an area."""

    latitude: float
    longitude: float
    source: str
    query_name: str
    osm_name: str


def clean_name(name: str) -> str:
    """Collapse whitespace and write ``Al-X`` as ``Al X`` (DLD mixes both).

    Brackets stay: in DLD names they qualify the place ("Al-Souq Al Kabeer (Deira)" is not
    the Bur Dubai souk), so they are never stripped; see ``ALIASES`` for renamed areas.
    """
    name = re.sub(r"\s+", " ", name.strip())
    name = re.sub(r"\b(al)-", r"\1 ", name, flags=re.IGNORECASE)
    return re.sub(r"([^\d\s])(\d+)$", r"\1 \2", name)  # "Al Layan1" -> "Al Layan 1"


def _respell(name: str) -> str:
    words = name.split(" ")
    return " ".join(
        SPELLINGS[w.lower()].capitalize() if w.lower() in SPELLINGS else w for w in words
    )


def _ordinal_forms(name: str) -> list[str]:
    """The name with a trailing ordinal word written as a digit and as "1st"."""
    words = name.split(" ")
    last = words[-1].lower()
    if last in ORDINALS:
        return [" ".join([*words[:-1], form]) for form in ORDINALS[last]]
    return []


def candidates(area_name: str) -> list[Candidate]:
    """Queries to try in order: exact spellings, then an alias, then the parent community."""
    base = clean_name(area_name)
    exact: list[str] = []
    for name in (base, _respell(base)):
        forms = _ordinal_forms(name)  # [digit, nth]: OSM in Dubai mostly writes "Al Barsha 1"
        for form in (*forms[:1], name, *forms[1:]):
            if form.lower() not in {e.lower() for e in exact}:
                exact.append(form)
    out = [Candidate(n, SOURCE_EXACT) for n in exact]
    for alias in ALIASES.get(area_name.strip()) or ALIASES.get(base) or ():
        out.append(Candidate(alias, SOURCE_ALIAS))
    parent = _SUFFIX.sub("", base)
    # A one-word parent ("Island 2" -> "Island") would match anything: not tried.
    if parent != base and len(parent.split(" ")) >= 2:
        for name in dict.fromkeys([parent, _respell(parent)]):
            out.append(Candidate(name, SOURCE_APPROX))
    return out


def query_string(name: str) -> str:
    """The free-text query sent to Nominatim (the area name only, plus the city)."""
    return f"{name}, Dubai, United Arab Emirates"


def in_dubai(result: dict[str, Any]) -> bool:
    """True if a Nominatim result lies in the emirate of Dubai (code AE-DU) and the box."""
    address = result.get("address") or {}
    if address.get("ISO3166-2-lvl4") != "AE-DU":
        return False
    lon_min, lat_min, lon_max, lat_max = config.DUBAI_BBOX
    try:
        lat, lon = float(result["lat"]), float(result["lon"])
    except (KeyError, TypeError, ValueError):
        return False
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


# Areas are places (suburb, neighbourhood, quarter), admin boundaries or land-use polygons.
# Anything else (a hotel called "Marsa Dubai", a road called "Al Barsha") is not the area.
AREA_CATEGORIES = {"place", "boundary", "landuse"}


def is_area_feature(result: dict[str, Any]) -> bool:
    """True if the result is a place / boundary / land-use feature, not a POI or road."""
    return result.get("category") in AREA_CATEGORIES


_STOP_TOKENS = {"al", "el"}
_ORDINAL_TOKENS = {
    **{word: digit for word, (digit, _) in ORDINALS.items()},
    **{nth: digit for digit, nth in ORDINALS.values()},
}


def name_tokens(name: str) -> set[str]:
    """Lowercase word tokens with "al" dropped and ordinals as digits ("First" = "1st" = "1")."""
    words = re.findall(r"[a-z0-9]+", clean_name(name).lower().replace("'", ""))
    return {_ORDINAL_TOKENS.get(w, w) for w in words if w not in _STOP_TOKENS}


def names_match(query_name: str, result: dict[str, Any]) -> bool:
    """True if every word of the query is in one of the result's names (any language tag).

    Nominatim matches loosely ("Marsa Dubai" finds "Marsa Al Arab Villas"); this keeps only
    results that are actually called what was asked for.
    """
    wanted = name_tokens(query_name)
    names = list((result.get("namedetails") or {}).values()) + [result.get("name") or ""]
    return bool(wanted) and any(wanted <= name_tokens(n) for n in names if n)


def pick(results: Sequence[dict[str, Any]], query_name: str) -> dict[str, Any] | None:
    """The first area feature inside Dubai with the asked-for name (ranked by Nominatim)."""
    return next(
        (r for r in results if is_area_feature(r) and in_dubai(r) and names_match(query_name, r)),
        None,
    )


class Nominatim:
    """Cached, rate-limited Nominatim search. ``fetcher`` is injectable for tests."""

    def __init__(
        self,
        cache_dir: Path = config.DATA_RAW_OSM,
        *,
        refresh: bool = False,
        fetcher: Callable[[str], bytes] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Set the cache folder; ``refresh`` re-fetches cached queries."""
        self.cache_dir = cache_dir
        self.refresh = refresh
        self.fetcher = fetcher or self._http_get
        self.sleep = sleep
        self.network_calls = 0
        self._last_call = 0.0

    @staticmethod
    def request(query: str) -> urllib.request.Request:
        """The HTTP request for one query (descriptive User-Agent, Dubai-bounded)."""
        lon_min, lat_min, lon_max, lat_max = config.DUBAI_BBOX
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "namedetails": 1,
            "limit": 5,
            "countrycodes": "ae",
            "viewbox": f"{lon_min},{lat_max},{lon_max},{lat_min}",
            "bounded": 1,
        }
        url = f"{config.NOMINATIM_URL}?{urllib.parse.urlencode(params)}"
        return urllib.request.Request(url, headers={"User-Agent": config.NOMINATIM_USER_AGENT})

    def _http_get(self, query: str) -> bytes:
        with urllib.request.urlopen(self.request(query), timeout=TIMEOUT_SECONDS) as response:
            return response.read()

    def _cache_path(self, query: str) -> Path:
        key = f"{query}|{CACHE_VERSION}"
        return self.cache_dir / f"{hashlib.sha1(key.encode()).hexdigest()[:16]}.json"

    def search(self, query: str) -> list[dict[str, Any]]:
        """Results for ``query``, from the cache when present."""
        path = self._cache_path(query)
        if path.exists() and not self.refresh:
            return json.loads(path.read_text())["results"]
        wait = config.NOMINATIM_MIN_INTERVAL_SECONDS - (time.monotonic() - self._last_call)
        if wait > 0:
            self.sleep(wait)
        body = self.fetcher(query)
        self._last_call = time.monotonic()
        self.network_calls += 1
        results = json.loads(body)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"query": query, "results": results}, ensure_ascii=False))
        return results


def locate(area_name: str, client: Nominatim) -> tuple[Hit | None, list[str]]:
    """Try each candidate in order; return the first hit and the names tried."""
    tried: list[str] = []
    for cand in candidates(area_name):
        tried.append(cand.query_name)
        result = pick(client.search(query_string(cand.query_name)), cand.query_name)
        if result is not None:
            return (
                Hit(
                    latitude=round(float(result["lat"]), 6),
                    longitude=round(float(result["lon"]), 6),
                    source=cand.source,
                    query_name=cand.query_name,
                    osm_name=(result.get("namedetails") or {}).get("name:en")
                    or str(result.get("display_name", "")).split(",")[0],
                ),
                tried,
            )
    return None, tried


def read_seed(path: Path = SEED_PATH) -> list[dict[str, str]]:
    """Seed rows as dicts, with an empty centroid_source column added if missing."""
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row.setdefault("centroid_source", "")
        row["centroid_source"] = row["centroid_source"] or ""
    return rows


def write_seed(rows: list[dict[str, str]], path: Path = SEED_PATH) -> None:
    """Write the seed back in its column order (minimal quoting, LF line endings)."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SEED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({k: row.get(k, "") for k in SEED_COLUMNS} for row in rows)


def geocode(rows: list[dict[str, str]], client: Nominatim) -> list[dict[str, Any]]:
    """Fill latitude / longitude / centroid_source in place; return one log entry per area.

    Manual rows are kept as they are. Every other row is re-derived from the (cached)
    responses, so a changed rule applies to all rows and a re-run is reproducible.
    """
    log_rows: list[dict[str, Any]] = []
    for row in rows:
        name = row["area_name_en"]
        if row["centroid_source"] == SOURCE_MANUAL:
            log_rows.append({**row, "outcome": SOURCE_MANUAL, "query": "", "osm_name": ""})
            continue
        hit, tried = locate(name, client)
        if hit is None:
            row.update(latitude="", longitude="", centroid_source="")
            log_rows.append({**row, "outcome": "not found", "query": "; ".join(tried)})
            continue
        row.update(
            latitude=f"{hit.latitude:.6f}",
            longitude=f"{hit.longitude:.6f}",
            centroid_source=hit.source,
        )
        log_rows.append(
            {**row, "outcome": hit.source, "query": hit.query_name, "osm_name": hit.osm_name}
        )
    return log_rows


def render(log_rows: list[dict[str, Any]], network_calls: int) -> str:
    """``reports/area_centroids.md``: counts by outcome and the owner's review lists."""
    counts: dict[str, int] = {}
    for r in log_rows:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    n = len(log_rows)
    located = n - counts.get("not found", 0)

    def section(outcome: str, title: str, note: str, cols: list[str]) -> list[str]:
        rows = [r for r in log_rows if r["outcome"] == outcome]
        if not rows:
            return []
        body = [[str(r.get(c, "")) for c in cols] for r in rows]
        return [f"## {title} ({len(rows)})", "", note, "", *md_table(cols, body), ""]

    lines = [
        "# Area centroids",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `ingest/geocode_areas.py` "
        f"(`make centroids`), {network_calls} new Nominatim requests (the rest from the cache "
        "in `data/raw/osm/`). Centroids feed the Power BI bubble map (docs/06 §4). "
        f"**{config.OSM_ATTRIBUTION}.**",
        "",
        f"**{located} of {n} areas located.** Only results whose OSM address is in the "
        "emirate of Dubai (AE-DU) and inside the Dubai box are accepted. Not-found areas have "
        "no bubble; there is no fallback to a zone centroid. To fix one, type its coordinates "
        "into `dbt/seeds/seed_area.csv` with `centroid_source = manual` (never overwritten), "
        "then `make dbt`.",
        "",
        *md_table(
            ["Outcome", "Areas"],
            [[k, f"{v:,}"] for k, v in sorted(counts.items(), key=lambda kv: -kv[1])],
        ),
        "",
        *section(
            "not found",
            "Not found: fill in by hand",
            "Names tried, in order.",
            ["area_id", "area_name_en", "zone", "query"],
        ),
        *section(
            SOURCE_APPROX,
            "Approximate: parent community only, please review",
            "Found only without the sub-area suffix, so sub-areas share one point.",
            ["area_id", "area_name_en", "zone", "query", "osm_name", "latitude", "longitude"],
        ),
        *section(
            SOURCE_ALIAS,
            "Found under an alias, please review",
            "Located under the better-known name in `ALIASES`.",
            ["area_id", "area_name_en", "zone", "query", "osm_name", "latitude", "longitude"],
        ),
    ]
    return "\n".join(lines)


def run(*, refresh: bool = False, seed: Path = SEED_PATH, report: Path | None = None) -> dict:
    """Geocode every non-manual area, rewrite the seed and the report. Returns counts."""
    rows = read_seed(seed)
    client = Nominatim(refresh=refresh)
    log_rows = geocode(rows, client)
    write_seed(rows, seed)
    report = report or config.REPORTS / REPORT_NAME
    report.write_text(render(log_rows, client.network_calls))
    counts: dict[str, int] = {}
    for r in log_rows:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    log.info("areas: %d, outcomes: %s, network calls: %d", len(rows), counts, client.network_calls)
    return counts


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="ignore the response cache")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(refresh=args.refresh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
