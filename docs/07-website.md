# 07 – Portfolio Website

## 1. Goal

A fast, professional personal site that a recruiter can understand in 30 seconds and a hiring manager can explore for 10 minutes: a home page about the owner, with projects as a section, and a page per project. For this project the embedded Power BI report is the centrepiece, and the story and build sections prove the thinking behind it. Readers are recruiters and hiring managers in banking, real estate and data roles, many of them not specialists, so the wording is plain English.

## 2. Stack and hosting

- **Static HTML + CSS + a little vanilla JS** in its **own repository**, the GitHub Pages user site `SafwanTisekar.github.io`, served at https://safwantisekar.github.io/ (this project: https://safwantisekar.github.io/projects/dubai-property/). No framework and no build step to deploy. No custom domain.
- This repository keeps **no copy** of the site. `make site` and `make site-shots` write into a local clone of the site repository, set as an absolute path in `.env` (`SITE_REPO_DIR`); `make site-preview` serves that clone. Then commit and push in the site repository to publish.
- The site repository deploys itself: its `.github/workflows/pages.yml` runs its `tests/test_site.py` (pytest + Pillow only) and publishes on every push to `main`, leaving out `tests/`, `README.md` and `.github/`. One-time setup there: Settings > Pages > Source: GitHub Actions.
- **Links are root-relative** (`/styles.css`, `/projects/dubai-property/`), as a user site is served at the domain root; `og:image` is an absolute `https://safwantisekar.github.io/...` URL, as social previews require.
- Tests: the site repository checks the pages (numbers vs `data/site.json`, links, images, contrast, privacy). Here, `tests/test_website_build.py` checks the build helpers and, when `SITE_REPO_DIR` is set, ties the site to this project (embed URL = docs/08 Publishing record, report gallery = the Power BI pages, every page the build writes exists); in CI those checks skip.
- Charts are the static PNGs from `reports/figures`, converted to WebP.

## 3. Pages

```
SafwanTisekar.github.io/         (its own repository; SITE_REPO_DIR here)
  index.html                     home page (about the owner)
  styles.css  main.js  config.js  shared by every page
  data/site.json                 numbers (make site)
  data/projects.json             the project cards: the one place to add a project
  assets/favicon.svg
  projects/dubai-property/
    index.html                   this project's page
    assets/figures/  assets/report/  assets/og.webp  assets/architecture.svg
```

**Home (`index.html`).** The owner's own wording for the hero, What I do, About and Skills; the rest from the owner's CV only (the CV itself is never published). Where the CV is thin or ambiguous, the page carries a visible `TODO(owner)` note instead of invented text; the deploy job fails while any remain.

| Section | Content |
|---|---|
| Hero | Name, one-line summary, "Analytics · BI · AI and automation · Dubai, UAE", buttons: View projects, GitHub, CV (hidden until a sanitised `cvUrl` is set); cut-out photo |
| What I do (`#what-i-do`) | Three cards: BI and reporting, AI and automation, owning systems and change (owner's text) |
| About (`#about`) | Three short paragraphs (owner's text) |
| Experience (`#experience`) | Timeline: role, company, dates, achievement bullets with the CV's numbers |
| Skills (`#skills`) | Grouped pills exactly as the owner listed them (BI and reporting, data and SQL, Python and modelling, AI and automation, ERP and delivery) |
| Projects (`#projects`) | Rendered from `data/projects.json`; one project shows as a wide featured card (thumbnail left, text right), two or more as a grid: thumbnail, two-sentence summary, three numbers from `site.json`, tool tags, data attribution, "View project" |
| Education (`#education`) | Degree, certifications, publication |

Footer: name, year, GitHub, Back to top. The project page footer adds Home and the DLD/OSM attribution and disclaimer.

**Project page (`projects/dubai-property/`).** Same header and footer style, with "← All projects" in the nav and the hero.

| Section | Content |
|---|---|
| Hero (`#top`) | Title, one-line pitch, four headline numbers (transactions and rent lines stated separately; latest full year's market sales; AVM error vs comparables; negative equity after a 20% fall), buttons: live report, GitHub repo, 5-minute tour |
| Live report (`#report`) | Publish to web iframe (16:9) behind a poster; screenshot gallery of the nine pages + main findings as the fallback |
| The story (`#story`) | The business question, then five findings, each with one chart and a two or three sentence takeaway: mix shift, the index vs DLD's (turns about 6 months sooner), the 2026 turn with the outlook, AVM vs comparables, the stress test |
| How it's built (`#build`) | Pipeline flow (an ordered list styled as steps), tools, data quality and testing, limitations |

Footer: DLD CC BY 4.0, OpenStreetMap ODbL, data-as-of date, "Independent project, not affiliated with DLD. Not investment or lending advice.", GitHub.

**Adding a project:** add an entry to `data/projects.json` (title, url, thumbnail, summary, numbers as `site.json` keys, tags, attribution), create `projects/<slug>/index.html` from this project's page, add any new numbers to `build.collect` and the page to `build.PAGES`, then `make site`.

## 4. How the numbers get onto the page

`make site` (`src/dubai_property/website/build.py`) reads the main database, renders the project cards from `data/projects.json` into the home page, and writes every number on both pages into its `<span data-kpi="key">`, plus `website/data/site.json` (value, label, source per key). Nothing is typed by hand, and the page stays plain HTML (fast, readable without JavaScript, indexable). The values reuse existing, reconciled code: the silver KPI query of `quality/kpi_reconciliation.py`, the card queries of `quality/pbi_cards.py` (so the site matches the Power BI cards and `kpi_reconciliation.md` §7), `models/report_4a.mix_shift_changes` and the index validation diagnostics (`price_index.md`), and `hedonic_index.find_episodes` for the villa drawdown. The build fails on a span without a value or a value that no page shows. It refuses a scratch database. It also converts the five story charts to WebP (1400 px wide).

Commit the result. The deploy job doesn't need the database.

## 5. Power BI embed

- `main.js` creates the iframe when the frame scrolls near the screen or the poster is clicked, so the report never slows the first view. The poster stays until the iframe fires `load`.
- The embed URL lives in `website/config.js` (one place to update). A test checks it equals the docs/08 Publishing record.
- **Fallback** (`#report-fallback`): the nine page screenshots and the main findings. It shows when JavaScript is off, when the iframe hasn't loaded after `embedTimeoutSeconds` (20 s), or when `embedExpires` has passed. The date is the reliable switch, because an expired Publish to web link still loads (an error page) and fires `load`. Move the date on if the licence is renewed.
- "Open the report full screen" opens the embed URL in a new tab (useful on phones, where a 16:9 frame is small).
- **Screenshots:** in Power BI Desktop, File > Export > PDF (all pages), then `make site-shots PDF=path/to/export.pdf`. It trims the PDF's white page margin and writes `projects/dubai-property/assets/report/p01.webp` … `p09.webp` in report order and `assets/og.webp` next to them (the social preview, from the Executive page; the home page and its project card use it too). Without `PDF=` it writes labelled placeholders. **Don't deploy the placeholders.** Done from the owner's export on 2026-10-03.

## 6. Design

Restyled 2026-10-03 to the owner's style reference (style only): a dark site with one green accent, shared by both pages through `styles.css`.

- **Palette:** near-black background `#0a0d0b` with a soft green glow and faint diagonal light rays (CSS gradients behind the page); cards `#121815` with a 1 px border and a soft green shadow; headings `#f2f5f3`, body text `#a3ada7`; accent green `#3fae5a` for buttons, highlights and big numbers. Dark is the only theme.
- **Contrast (tested):** green on the background 6.9:1 and on cards at least 5.9:1; buttons use dark text on green (6.75:1), because white on green is only 2.8:1; body text 8.5:1. Report screenshots and charts sit on light cards (`#f4f6f4`, text 15:1), so they read as designed.
- **Type:** Manrope, self-hosted (`assets/fonts/manrope-latin-wght.woff2`, variable weight, 25 KB, licence `OFL.txt` alongside), preloaded; system fonts as fallback.
- **Home hero:** headline, summary and two buttons on the left; on the right the owner's photo with its background removed (`assets/photo.webp`, 720 × 900, transparent WebP, 42 KB, alt "Safwan Tisekar"; cut out once with rembg's BiRefNet portrait model, not a project dependency) over a green glow and rings drawn in inline SVG, faded into the page at the bottom and sides. No project numbers in the hero (owner): they live on the project card and page. No stock images, logo strips, testimonials, ratings or "trusted by" claims.
- **Cards:** "What I do" cards with icon badges (inline SVG in green circles), skill groups, project cards, education items.
- Accessibility: semantic landmarks, one `h1` per page, skip link, visible focus ring (green, 3:1 or more), alt text everywhere, declared image sizes, `prefers-reduced-motion` respected (no animations in any case).
- Layout: one container for every section (max width 1160 px, 16 px gutters, same left edge; long paragraphs capped at about 80 characters for reading), sections 64 px apart (44 px on phones); checked at 1440 px and at 375 px (rendered in a 375 px frame: no horizontal scroll on either page).
- Performance: no external requests before the report iframe; figures and photos as WebP.
- Wording: plain sentences, no em-dashes.
- Personal details: GitHub links only. Tests fail on email addresses, phone-number patterns, `mailto:` / `tel:`, LinkedIn, visa or date-of-birth text, and any document file (a CV) in `website/`. The hero line "Dubai, UAE" is the owner's chosen wording (city only, no address).

## 7. Content checklist

- [x] Headline numbers pulled from the database by `make site` (not typed)
- [x] Five findings, each with one chart and a takeaway
- [x] Architecture: the pipeline flow on the page; `assets/architecture.svg` for the README (Phase 7)
- [x] AVM metrics against the comparable-sales baseline (MdAPE, ±10%)
- [x] Limitations section (EIBOR proxy, rate effect, illustrative stress test, provisional latest months, villa area basis, no building age or developer, nominal AED, part year)
- [x] Links: GitHub repo and profile; CV button hidden until a sanitised file is given
- [x] Attribution: "Data: Dubai Land Department, CC BY 4.0", "Area locations © OpenStreetMap contributors (ODbL)"; disclaimer: independent project, not affiliated with DLD; not investment or lending advice
- [x] Report screenshots from the Desktop PDF export (2026-10-03)
- [x] Owner resolved the `TODO(owner)` notes (2026-10-03)
- [ ] Lighthouse ≥ 90 on Performance, Accessibility and SEO (Chrome DevTools; no Node in this environment)

## 8. Decisions (Phase 6)

| Date | Decision | Why |
|---|---|---|
| 2026-10-02 | **One long page** with anchored sections instead of the five pages first planned (index, case study, methodology, data, about) | Recruiters scan one page; the depth lives in the repo docs and model cards, linked from the page (owner) |
| 2026-10-02 | Numbers written into the HTML at build time, not fetched by JavaScript | Static page reads without JS and is indexable; one source (`site.json`) and a test keep page and JSON equal |
| 2026-10-02 | Fallback switches on a configured licence end date as well as a load timeout | An expired Publish to web link still loads an error page, so a timeout alone can't detect it |
| 2026-10-02 | Screenshots from Desktop's PDF export (PyMuPDF dev dependency) | Exactly what the report shows, no browser automation |
| 2026-10-03 | GitHub links only: no email or LinkedIn on the site | Owner decision on plan review; a test rejects email addresses, `mailto:` and LinkedIn in `website/` |
| 2026-10-03 | Mix shift quoted from the published hedonic index (2023: raw +1% vs like for like +17%, `price_index.md`), not the Phase 3 fixed basket (+14.5%) | The site cites the published model |
| 2026-10-03 | The index finding says it reflects turns about 6 months sooner, likely because DLD's series appears to average 12 months (an inference); it never says the index predicts turns | Owner wording rule on plan review |
| 2026-10-03 | The pipeline diagram on the page is an ordered list styled as steps, not an inline SVG | Readable text at phone width and native to screen readers; the SVG is kept for the README |
| 2026-10-03 | **Two-page structure:** a personal home page with projects as a section, and this project on its own page | The site is about the owner; more projects can be added as cards (owner) |
| 2026-10-03 | Home content only from the CV; gaps are visible `TODO(owner)` notes, blocked at deploy | Nothing about the owner is invented (owner) |
| 2026-10-03 | Project cards rendered at build time from `data/projects.json` | One place to add a project; the page stays static |
| 2026-10-03 | Experience: "improvement" in payment turnaround confirmed; GST input tax credit loss prevented stated as INR 7.2 crore (18% of INR 40 crore), about AED 2.7 million (26.23 INR per AED, 2 Oct 2026); Unilever is the only role | Owner answers to the home-page TODOs |
| 2026-10-03 | Restyle: dark theme, green accent, self-hosted Manrope, photo mosaic hero; home sections Hero, What I do, About, Experience, Skills, Projects, Education | Owner's style reference and content brief |
| 2026-10-03 | Hero: new photo with the background removed, no project numbers; Experience adds month-end close support and IT/vendor coordination (owner-confirmed, beyond the CV) | Owner review of the restyle |
| 2026-10-03 | Charts and report screenshots open in a native `<dialog>` viewer (Esc closes, focus returns to the link; without JavaScript the link opens the image) | Charts were too small to read in the two-column findings layout (owner review) |
| 2026-10-03 | **The site moved to its own repository**, the GitHub Pages user site `SafwanTisekar.github.io` (no custom domain). `make site` writes into its clone (`SITE_REPO_DIR`); this repository's Pages workflow and `website/` folder are removed; links are root-relative | A personal site with several projects shouldn't live inside one project's repository (owner) |
