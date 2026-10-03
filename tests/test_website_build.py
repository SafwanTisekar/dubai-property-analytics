"""The website build (``make site``) and its link to the site repository (docs/07).

The site lives in its own repository (``SafwanTisekar.github.io``), which has its own tests
for the pages themselves. Here:

* the build helpers, with no database and no site clone (always run, CI included);
* checks that tie the site to this project, run only when ``SITE_REPO_DIR`` points at a
  local clone of the site (skipped in CI): every page the build writes exists, the embed
  URL equals the docs/08 Publishing record, and the report gallery matches the Power BI
  pages.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from dubai_property import config
from dubai_property.website import build, report_pages

# --- Build helpers ----------------------------------------------------------------------


def test_formatting() -> None:
    assert build.millions(1_769_938) == "1.77M"
    assert build.millions(10_514_602) == "10.5M"
    assert build.signed(0.166) == "+17%"
    assert build.signed(-0.0504) == "−5%"
    assert build.signed(0.0123, 1) == "+1.2%"
    assert build.signed(0.0) == "0%"
    assert build.unsigned(-0.111) == "11%"


def test_latest_full_year() -> None:
    assert build.latest_full_year(date(2026, 9, 25)) == 2025
    assert build.latest_full_year(date(2026, 12, 31)) == 2026


def test_fill_html_writes_values_and_rejects_unknown_keys() -> None:
    page = '<p><span data-kpi="a">old</span> and <span class="x" data-kpi="b">1</span></p>'
    out, used = build.fill_html(page, {"a": "AED 1 & 2", "b": "+3%"})
    assert out == (
        '<p><span data-kpi="a">AED 1 &amp; 2</span> and <span class="x" data-kpi="b">+3%</span></p>'
    )
    assert used == {"a", "b"}
    with pytest.raises(KeyError):
        build.fill_html('<span data-kpi="c">x</span>', {"a": "1"})


@pytest.fixture
def fake_site(tmp_path: Path) -> build.SitePaths:
    """A minimal site clone: one thumbnail, enough for render_cards."""
    thumb = tmp_path / "projects" / "demo" / "thumb.webp"
    thumb.parent.mkdir(parents=True)
    Image.new("RGB", (160, 90), (40, 40, 40)).save(thumb, "WEBP")
    return build.SitePaths(tmp_path)


PROJECT = {
    "slug": "demo",
    "title": "Demo & Co",
    "url": "/projects/demo/",
    "thumbnail": "/projects/demo/thumb.webp",
    "thumbnail_alt": "Demo thumbnail",
    "summary": ["One.", "Two."],
    "numbers": [{"kpi": "a", "text": "of something in {year}"}],
    "tags": ["SQL"],
    "attribution": "Data: somebody",
}


def test_render_cards_replaces_only_the_block(fake_site: build.SitePaths) -> None:
    page = "<div>\n<!-- projects:start (x) -->\nOLD\n<!-- projects:end -->\n</div>"
    out = build.render_cards(page, [PROJECT], fake_site)
    assert "OLD" not in out and out.startswith("<div>") and out.endswith("</div>")
    assert out.count('<article class="card"') == 1
    assert 'width="160" height="90"' in out  # true thumbnail size, read from the clone
    assert '<span data-kpi="a"></span>' in out and '<span data-kpi="year"></span>' in out
    assert "Demo &amp; Co" in out
    assert build.render_cards(out, [PROJECT], fake_site) == out  # idempotent
    with pytest.raises(SystemExit):
        build.render_cards("<div></div>", [PROJECT], fake_site)


def test_site_paths_resolve_root_relative_urls(tmp_path: Path) -> None:
    site = build.SitePaths(tmp_path)
    assert site.local("/projects/demo/x.webp") == tmp_path / "projects/demo/x.webp"
    assert site.pages == (tmp_path / "index.html", site.project_dir / "index.html")


def test_site_dir_requires_a_clone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(build.SITE_ENV, str(tmp_path))  # no index.html there
    assert build.site_dir(required=False) is None
    with pytest.raises(SystemExit, match="SITE_REPO_DIR"):
        build.site_dir()
    (tmp_path / "index.html").write_text("<!doctype html>")
    assert build.site_dir() == tmp_path


# --- The site clone, when configured ----------------------------------------------------


@pytest.fixture(scope="module")
def site() -> build.SitePaths:
    root = build.site_dir(required=False)
    if root is None:
        pytest.skip("SITE_REPO_DIR is not set to a local clone of the site repository")
    return build.SitePaths(root)


def test_site_has_every_page_the_build_writes(site: build.SitePaths) -> None:
    for path in (*site.pages, site.site_json, site.projects_json):
        assert path.is_file(), path


def test_embed_url_matches_publishing_record(site: build.SitePaths) -> None:
    roadmap = (config.PROJECT_ROOT / "docs" / "08-roadmap.md").read_text(encoding="utf-8")
    (url,) = re.findall(r"\| Publish-to-web URL \| (\S+) \|", roadmap)
    assert f'"{url}"' in (site.root / "config.js").read_text(encoding="utf-8")


def test_gallery_matches_report_pages(site: build.SitePaths) -> None:
    pages_json = config.PROJECT_ROOT / "powerbi/DubaiProperty.Report/definition/pages/pages.json"
    order = json.loads(pages_json.read_text(encoding="utf-8"))["pageOrder"]
    assert len(report_pages.PAGES) == len(order)
    html = site.project.read_text(encoding="utf-8")
    assert re.findall(r"<figcaption>([^<]+)</figcaption>", html) == list(report_pages.PAGES)
    for n in range(1, len(order) + 1):
        assert (site.project_dir / "assets" / "report" / f"p{n:02d}.webp").is_file()


def test_site_numbers_are_current(site: build.SitePaths) -> None:
    """Every span on the site carries the value site.json records (make site wrote both)."""
    kpis = json.loads(site.site_json.read_text(encoding="utf-8"))["kpis"]
    for path in site.pages:
        for _, key, text, _ in build.SPAN_RE.findall(path.read_text(encoding="utf-8")):
            assert text == kpis[key]["value"].replace("&", "&amp;"), f"{path.name} {key}"
