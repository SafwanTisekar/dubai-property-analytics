"""Website build (``make site``): headline numbers from the database, project cards, figures.

The site is plain static HTML in its own repository (the GitHub Pages user site
``SafwanTisekar.github.io``), whose local clone is ``SITE_REPO_DIR`` in ``.env``: a personal
home page (``index.html``) with a card per project, and a page per project
(``projects/<slug>/index.html``). This module writes into that clone; it keeps no copy here.
Every number on either page sits in a ``<span data-kpi="key">`` whose text this module
writes, so nothing is typed by hand (docs/07 §4) and the pages read correctly without
JavaScript or a fetch. The
same values go to ``data/site.json`` with a label and a source, for review and for
the CI test that checks the pages and the JSON agree.

The project cards are rendered from ``data/projects.json`` (the one place to add a
project) into the home page between the ``projects:start`` / ``projects:end`` markers.

The numbers reuse the code that already backs the reports and the Power BI cards:

* market sales of the latest full year: the canonical silver query of the KPI
  reconciliation (``quality.kpi_reconciliation``), the figure ``reports/findings.md`` quotes;
* AVM, stress test, forecast and index: the card queries of ``quality.pbi_cards`` over the
  rpt views, so the site shows what the report shows (``kpi_reconciliation.md`` §7);
* mix shift and the comparison with DLD's index: ``models.report_4a`` (``price_index.md``);
* the villa drawdown: ``models.hedonic_index.find_episodes`` on the published index.

Only small aggregates leave Postgres. It runs against the main database only: a scratch or
fixture database would put meaningless numbers on a public page.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from PIL import Image

from dubai_property import config, db
from dubai_property.models import hedonic_index as h
from dubai_property.models import report_4a
from dubai_property.quality import kpi_reconciliation as kr
from dubai_property.quality import pbi_cards as cards

log = logging.getLogger(__name__)

SITE_ENV = "SITE_REPO_DIR"  # .env: the local clone of the site repository
PROJECT_SLUG = "dubai-property"


@dataclass(frozen=True)
class SitePaths:
    """Where each site file lives inside the site repository clone."""

    root: Path

    @property
    def home(self) -> Path:
        """The personal home page."""
        return self.root / "index.html"

    @property
    def project_dir(self) -> Path:
        """This project's folder on the site."""
        return self.root / "projects" / PROJECT_SLUG

    @property
    def project(self) -> Path:
        """This project's page."""
        return self.project_dir / "index.html"

    @property
    def pages(self) -> tuple[Path, Path]:
        """Every page with data-kpi spans."""
        return (self.home, self.project)

    @property
    def site_json(self) -> Path:
        """The numbers, with label and source."""
        return self.root / "data" / "site.json"

    @property
    def projects_json(self) -> Path:
        """The project cards."""
        return self.root / "data" / "projects.json"

    @property
    def figure_dir(self) -> Path:
        """Where the story charts go."""
        return self.project_dir / "assets" / "figures"

    def local(self, url: str) -> Path:
        """A root-relative site URL (``/projects/...``) -> its file in the clone."""
        return self.root / url.lstrip("/")


def site_dir(required: bool = True) -> Path | None:
    """``SITE_REPO_DIR`` from the environment or ``.env``; it must hold the site's index.html."""
    from dotenv import load_dotenv

    load_dotenv(config.PROJECT_ROOT / ".env", override=False)
    raw = os.environ.get(SITE_ENV, "").strip()
    path = Path(raw).expanduser() if raw else None
    if path is None or not (path / "index.html").is_file():
        if not required:
            return None
        raise SystemExit(
            f"{SITE_ENV} must point at the local clone of the site repository "
            f"(SafwanTisekar.github.io), as an absolute path in .env; got {raw or 'nothing'}"
        )
    return path


def site_paths() -> SitePaths:
    """The site repository paths (fails clearly when SITE_REPO_DIR is unset)."""
    return SitePaths(site_dir())


# reports/figures -> website/assets/figures/<name>.webp, one per finding (docs/07 §3).
FIGURES = (
    "price_index_mix_shift",
    "price_index_validation",
    "price_index_levels",
    "avm_accuracy_by_segment",
    "stress_heatmap",
)
FIGURE_MAX_WIDTH = 1400  # px; the content column is 1100 px, so this stays sharp on 2x screens
WEBP_QUALITY = 82

STRESS_LTV = cards.DEFAULT_LTV  # 80%: the observed norm since 2020 (findings F2.4)
APARTMENTS, VILLAS, DUBAI = "Apartments", "Villas / Townhouses", "Dubai (all residential)"

CARDS_RE = re.compile(r"(<!-- projects:start[^>]*-->\n).*?(<!-- projects:end -->)", re.DOTALL)
PLACEHOLDER_RE = re.compile(r"\{([a-z0-9_]+)\}")
SPAN_RE = re.compile(r'(<span\b[^>]*\bdata-kpi="([a-z0-9_]+)"[^>]*>)(.*?)(</span>)', re.DOTALL)


@dataclass(frozen=True)
class Kpi:
    """One number on the page."""

    key: str
    value: str  # as displayed
    label: str  # what it is, for site.json readers
    source: str  # where it comes from


# --- Formatting -------------------------------------------------------------------------

MINUS = "−"  # a real minus sign: easier to read than a hyphen, and not a dash


def millions(n: Any) -> str:
    """1_769_938 -> '1.77M'; 10_514_602 -> '10.5M' (three significant figures)."""
    m = float(n) / 1e6
    return f"{m:.2f}M" if m < 10 else f"{m:.1f}M"


def signed(x: Any, digits: int = 0) -> str:
    """0.166 -> '+17%'; -0.05 -> '−5%' (half away from zero, as the cards round)."""
    v = cards._half_up(Decimal(str(x)) * 100, digits)
    if v == 0:
        return f"{abs(v)}%"
    return f"+{v}%" if v > 0 else f"{MINUS}{abs(v)}%"


def unsigned(x: Any, digits: int = 0) -> str:
    """-0.111 -> '11%': the size of a fall, when the sentence already says 'below'."""
    return cards.pct(abs(Decimal(str(x))), digits)


# --- Queries ----------------------------------------------------------------------------

COUNTS_SQL = """
select (select count(*) from gold.fct_transaction where is_in_report_scope),
       (select count(*) from gold.fct_rent_contract where is_in_report_scope)
"""


def latest_full_year(snapshot: date) -> int:
    """The latest complete calendar year (the report's default Year)."""
    return snapshot.year if (snapshot.month, snapshot.day) == (12, 31) else snapshot.year - 1


def villa_drawdown(index: Any) -> h.Episode:
    """The villa index's latest peak-to-trough episode of 10% or more."""
    villa = report_4a.series(index, "villa")
    episodes = h.find_episodes(villa["period_start"].to_list(), villa["index_value"].to_list())
    if not episodes:
        raise SystemExit("no villa drawdown episode in ml.fct_price_index: check make train")
    return episodes[-1]


def collect(conn: psycopg.Connection) -> list[Kpi]:
    """Every number the page shows."""
    (snapshot,) = conn.execute('select "Data As Of" from rpt.report_info').fetchone()
    year = latest_full_year(snapshot)
    out = [
        Kpi("data_as_of", f"{snapshot.day} {snapshot:%b %Y}", "Data snapshot", "rpt.report_info"),
        Kpi("year", str(year), "Latest full year", "rpt.report_info"),
    ]

    txn, rent = conn.execute(COUNTS_SQL).fetchone()
    out += [
        Kpi("txn_lines", millions(txn), "DLD transaction lines in scope (2004 on)",
            "gold.fct_transaction"),
        Kpi("rent_lines", millions(rent), "Ejari rent contract lines in scope",
            "gold.fct_rent_contract"),
    ]  # fmt: skip

    src = "silver market sales (kpi_reconciliation, = rpt)"
    sales = kr.fetch(conn, kr.SILVER_SALES_SQL, date(year, 1, 1), date(year, 12, 31))[str(year)]
    out += [
        Kpi("sales_count", cards.num(sales["market_sales"]), f"Market sales {year}", src),
        Kpi("sales_value", cards.aed_bn(sales["market_value"]), f"Market sales value {year}", src),
    ]

    src = "rpt.avm_performance, Test / Overall (avm_model_card.md)"
    for model, prefix in (("lightgbm", "avm"), ("comps", "comps")):
        mdape, h10, _ = cards._one(conn, cards.AVM_PERF_SQL, {"model": model})
        out += [
            Kpi(f"{prefix}_mdape", cards.pct(mdape), f"{model} median absolute % error", src),
            Kpi(f"{prefix}_hit10", cards.pct(h10, 0), f"{model} share within ±10%", src),
        ]
    (n_test, _, _) = cards._one(conn, cards.AVM_SCORE_SQL)
    out.append(Kpi("avm_test_sales", cards.num(n_test), "AVM test sales (2025 on)",
                   "rpt.avm_score"))  # fmt: skip

    src = f"rpt.stress_grid, Ready, assumed LTV {STRESS_LTV}% (stress_test.md)"
    for segment, seg_key in ((APARTMENTS, "apt"), (VILLAS, "villa")):
        for shock in (-20, -30):
            share, _ = cards._one(
                conn,
                cards.STRESS_SQL,
                {"scenario": "Price shock", "basis": "Assumed LTV", "segment": segment,
                 "shock": shock, "ltv": STRESS_LTV},
            )  # fmt: skip
            out.append(
                Kpi(f"stress_{seg_key}_{-shock}", cards.pct(share, 0),
                    f"{segment}: share in negative equity after a {-shock}% fall", src)
            )  # fmt: skip
    out.append(Kpi("stress_ltv", f"{STRESS_LTV}%", "Assumed loan-to-value", src))

    central, lo, hi = cards._one(
        conn, cards.FORECAST_SQL, {"segment": DUBAI, "scenario": cards.DEFAULT_SCENARIO}
    )
    src = "rpt.forecast, Dubai, rates flat (forecast.md)"
    out += [
        Kpi("fc_central", signed(central, 1), "12-month outlook, central", src),
        Kpi("fc_lo", signed(lo), "12-month outlook, 80% band low", src),
        Kpi("fc_hi", signed(hi), "12-month outlook, 80% band high", src),
    ]

    src = "rpt.price_index, latest complete month"
    for segment, key in ((APARTMENTS, "apt_yoy"), (DUBAI, "dubai_yoy")):
        period, _, yoy, _ = cards._one(conn, cards.INDEX_SQL, {"segment": segment,
                                                               "until": "9999-12-31"})  # fmt: skip
        out.append(Kpi(key, signed(yoy, 1), f"{segment} index, year on year "
                       f"({period:%b %Y})", src))  # fmt: skip
    conn.rollback()

    # Index-based numbers, read with the same loaders as price_index.md.
    index = report_4a.load_index()
    ep = villa_drawdown(index)
    src = "ml.fct_price_index, villas (price_index.md episodes)"
    out += [
        Kpi("villa_peak", f"{ep.peak_period:%B %Y}", "Villa index peak", src),
        Kpi("villa_trough", f"{ep.trough_period:%B %Y}", "Villa index trough so far", src),
        Kpi("villa_drawdown", unsigned(ep.depth), "Villa fall, peak to trough", src),
    ]

    raw_year = report_4a.query(report_4a.RAW_YEARLY_SQL)
    changes = [c for c in report_4a.mix_shift_changes(index, raw_year, snapshot.year)
               if c[1] is not None and c[2] is not None]  # fmt: skip
    # The year the raw median understates growth most (the price_index.md mix-table note).
    mix_year, raw, hedonic = max(changes, key=lambda c: c[2] - c[1])
    src = "price_index.md mix table (raw yearly median vs hedonic annual average)"
    out += [
        Kpi("mix_year", str(mix_year), "Year the raw median understated growth most", src),
        Kpi("mix_raw", signed(raw), f"Apartment raw median change {mix_year}", src),
        Kpi("mix_hedonic", signed(hedonic), f"Apartment like-for-like change {mix_year}", src),
    ]

    val = report_4a.load_diagnostics()["validation"]
    corr = [v["metrics"]["yoy_corr_aligned"] for v in val.values()]
    src = "artifacts/hedonic_index/diagnostics.json validation (price_index.md)"
    out += [
        Kpi("val_corr_min", f"{min(corr):.2f}", "Aligned YoY correlation with DLD, lowest", src),
        Kpi("val_corr_max", f"{max(corr):.2f}", "Aligned YoY correlation with DLD, highest", src),
        Kpi("val_lead", str(val["dubai"]["metrics"]["best_lead_months"]),
            "Months by which our monthly index turns before DLD's", src),
    ]  # fmt: skip
    return out


# --- Writing ----------------------------------------------------------------------------


def fill_html(text: str, values: dict[str, str]) -> tuple[str, set[str]]:
    """Write each value into its ``data-kpi`` span; return the page and the keys used.

    Raises ``KeyError`` for a span whose key has no value, so a typo can't ship a stale or
    empty number.
    """
    used: set[str] = set()

    def sub(m: re.Match) -> str:
        key = m.group(2)
        if key not in values:
            raise KeyError(f'index.html has data-kpi="{key}" but the build has no such value')
        used.add(key)
        return f"{m.group(1)}{html.escape(values[key], quote=False)}{m.group(4)}"

    return SPAN_RE.sub(sub, text), used


def convert_figure(src: Path, dest: Path, max_width: int = FIGURE_MAX_WIDTH) -> None:
    """PNG -> WebP, scaled down to ``max_width`` (never up)."""
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > max_width:
            im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "WEBP", quality=WEBP_QUALITY, method=6)


def _kpi_span(key: str) -> str:
    return f'<span data-kpi="{key}"></span>'


def render_card(project: dict[str, Any], site: SitePaths) -> str:
    """One project card. Numbers are empty data-kpi spans, filled like any other span."""
    e = html.escape
    numbers = "\n".join(
        f"          <li><strong>{_kpi_span(n['kpi'])}</strong> "
        f"{PLACEHOLDER_RE.sub(lambda m: _kpi_span(m.group(1)), e(n['text'], quote=False))}</li>"
        for n in project["numbers"]
    )
    summary = " ".join(e(s, quote=False) for s in project["summary"])
    tags = "".join(f"<li>{e(t, quote=False)}</li>" for t in project["tags"])
    with Image.open(site.local(project["thumbnail"])) as im:
        w, h = im.size
    url, title = e(project["url"]), e(project["title"], quote=False)
    img = (
        f'<img src="{e(project["thumbnail"])}" alt="{e(project["thumbnail_alt"])}" '
        f'loading="lazy" width="{w}" height="{h}">'
    )
    cta = (
        f'<a class="btn btn-primary" href="{url}">'
        f'View project<span class="sr-only">: {title}</span></a>'
    )
    return f"""      <article class="card" id="project-{e(project["slug"])}">
        <a href="{url}" tabindex="-1" aria-hidden="true">{img}</a>
        <div class="card-body">
          <h3><a href="{url}">{title}</a></h3>
          <p>{summary}</p>
          <ul class="card-numbers">
{numbers}
          </ul>
          <ul class="pills" aria-label="Tools">{tags}</ul>
          <p class="card-source">{e(project["attribution"], quote=False)}</p>
          {cta}
        </div>
      </article>
"""


def render_cards(page: str, projects: list[dict[str, Any]], site: SitePaths) -> str:
    """Replace the block between the projects markers with one card per project."""
    if not CARDS_RE.search(page):
        raise SystemExit(
            "index.html has no <!-- projects:start --> ... <!-- projects:end --> block"
        )
    cards_html = "".join(render_card(p, site) for p in projects)
    return CARDS_RE.sub(lambda m: m.group(1) + cards_html + m.group(2), page)


def write_site(kpis: list[Kpi], site: SitePaths) -> None:
    """site.json, the project cards, every page's numbers and the figures."""
    values = {k.key: k.value for k in kpis}
    projects = json.loads(site.projects_json.read_text(encoding="utf-8"))["projects"]
    pages: dict[Path, str] = {}
    used: set[str] = set()
    for path in site.pages:
        text = path.read_text(encoding="utf-8")
        if path == site.home:
            text = render_cards(text, projects, site)
        pages[path], keys = fill_html(text, values)
        used |= keys
    unused = set(values) - used
    if unused:
        raise SystemExit(f"values not shown on any page (remove or use them): {sorted(unused)}")
    for path, text in pages.items():
        path.write_text(text, encoding="utf-8")

    site.site_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "about": "Numbers shown on the site pages, written by `make site` from the database. "
        "Do not edit by hand.",
        "data_as_of": values["data_as_of"],
        "attribution": "Dubai Land Department, CC BY 4.0",
        "kpis": {k.key: {f: v for f, v in asdict(k).items() if f != "key"} for k in kpis},
    }
    site.site_json.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", "utf-8")

    for name in FIGURES:
        convert_figure(config.FIGURES / f"{name}.png", site.figure_dir / f"{name}.webp")


def main() -> int:
    """CLI entry point (``make site``)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    site = site_paths()  # fail before the queries if the site clone isn't configured
    if not db.is_main_db():
        raise SystemExit(f"make site reads the main database ({config.MAIN_DB}) only")
    with db.connect() as conn:
        kpis = collect(conn)
    write_site(kpis, site)
    width = max(len(k.key) for k in kpis)
    for k in kpis:
        log.info("%-*s %s", width, k.key, k.value)
    pages = ", ".join(str(p.relative_to(site.root)) for p in site.pages)
    log.info("wrote %s, %s and %d figures in %s", pages, site.site_json.relative_to(site.root),
             len(FIGURES), site.root)  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(main())
