"""Report screenshots for the website fallback (``make site-shots PDF=...``).

The live report is a Publish to web iframe that stops working if the Power BI licence
lapses, so the site always ships a picture of every page (docs/07 §4). The pictures come
from Power BI Desktop's own export (File > Export > PDF), so they show exactly what the
published report shows, with no browser automation.

Written into the site repository clone (``SITE_REPO_DIR``, see ``website.build``).

* ``--pdf report.pdf``: one WebP per page, ``projects/dubai-property/assets/report/
  p01.webp`` …, in report order, plus ``assets/og.webp`` next to them (the social preview,
  from the Executive page; the home page uses it too and its card shows that page).
* ``--placeholder``: labelled grey pictures in the same places, so the page and its tests
  work before the PDF exists. They say "screenshot pending" and must not be deployed.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from dubai_property.website.build import WEBP_QUALITY, site_paths

log = logging.getLogger(__name__)

# Report page order (powerbi/.../pages/pages.json) and the gallery captions in index.html.
PAGES = (
    "Introduction",
    "Key terms and methods",
    "1. Executive overview",
    "2. Financing",
    "3. Prices",
    "4. Rental yields",
    "5. Valuation model",
    "6. Risk and stress test",
    "KPI guide",
)
POSTER_PAGE = 3  # Executive overview: the poster over the embed and the social preview
SIZE = (1600, 900)  # 16:9, the report canvas (1280 x 720) at 1.25x
OG_SIZE = (1200, 630)  # the usual Open Graph size
NAVY, GREY, TEXT = (27, 42, 74), (232, 235, 240), (95, 102, 115)


def report_dir() -> Path:
    """``projects/dubai-property/assets/report`` in the site clone."""
    return site_paths().project_dir / "assets" / "report"


def og_image() -> Path:
    """The social preview, next to the report pages (the home page uses it too)."""
    return site_paths().project_dir / "assets" / "og.webp"


def page_path(number: int) -> Path:
    """``.../assets/report/p03.webp`` for page 3 (1-based)."""
    return report_dir() / f"p{number:02d}.webp"


def trim(im: Image.Image, tolerance: int = 12) -> Image.Image:
    """Cut the white page margin Desktop's PDF export puts around the report canvas."""
    im = im.convert("RGB")
    diff = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255)))
    box = diff.convert("L").point(lambda v: 255 if v > tolerance else 0).getbbox()
    return im.crop(box) if box else im


def fit(im: Image.Image, size: tuple[int, int] = SIZE) -> Image.Image:
    """Scale to ``size`` on a navy canvas (the report frame colour), keeping the ratio."""
    im = im.convert("RGB")
    scale = min(size[0] / im.width, size[1] / im.height)
    resized = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", size, NAVY)
    canvas.paste(resized, ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2))
    return canvas


def og_crop(im: Image.Image) -> Image.Image:
    """The social preview: the top of the page, cropped to 1200 x 630."""
    scale = OG_SIZE[0] / im.width
    resized = im.resize((OG_SIZE[0], round(im.height * scale)), Image.LANCZOS)
    return resized.crop((0, 0, *OG_SIZE)) if resized.height >= OG_SIZE[1] else fit(im, OG_SIZE)


def save(im: Image.Image, path: Path) -> None:
    """WebP at the site's quality setting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "WEBP", quality=WEBP_QUALITY, method=6)


def from_pdf(pdf: Path) -> list[Image.Image]:
    """Render every PDF page at a width of about 1600 px."""
    import pymupdf  # dev dependency: only needed when a new export arrives

    pages = []
    with pymupdf.open(pdf) as doc:
        for page in doc:
            zoom = 1.25 * SIZE[0] / page.rect.width  # margin room: trim() cuts it
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            pages.append(trim(Image.frombytes("RGB", (pix.width, pix.height), pix.samples)))
    return pages


def placeholder(title: str) -> Image.Image:
    """A grey card that says which page belongs here."""
    im = Image.new("RGB", SIZE, GREY)
    draw = ImageDraw.Draw(im)
    try:
        big, small = ImageFont.load_default(64), ImageFont.load_default(36)
    except TypeError:  # Pillow < 10.1 has no sized default font
        big = small = ImageFont.load_default()
    draw.rectangle((0, 0, SIZE[0], 24), fill=NAVY)
    draw.text((80, 360), title, fill=NAVY, font=big)
    draw.text((80, 460), "Screenshot pending: make site-shots PDF=<export>.pdf", fill=TEXT,
              font=small)  # fmt: skip
    return im


def write(images: Sequence[Image.Image]) -> None:
    """Pages, then the social preview."""
    if len(images) != len(PAGES):
        raise SystemExit(f"expected {len(PAGES)} pages ({', '.join(PAGES)}), got {len(images)}")
    for number, im in enumerate(images, start=1):
        save(fit(im), page_path(number))
    save(og_crop(images[POSTER_PAGE - 1].convert("RGB")), og_image())


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pdf", type=Path, help="PDF exported from Power BI Desktop")
    group.add_argument("--placeholder", action="store_true", help="labelled placeholders")
    args = parser.parse_args(argv)
    if args.pdf:
        if not args.pdf.exists():
            raise SystemExit(f"{args.pdf} not found")
        write(from_pdf(args.pdf))
    else:
        write([placeholder(title) for title in PAGES])
    log.info("wrote %d pages to %s and %s", len(PAGES), report_dir(), og_image())
    return 0


if __name__ == "__main__":
    sys.exit(main())
