# 07. Website

The portfolio site that hosts the embedded report: where it lives, its pages, how its numbers are produced and the design rules. The site itself is in a separate repository, [SafwanTisekar.github.io](https://github.com/SafwanTisekar/SafwanTisekar.github.io).

## 1. Goal

A fast personal site that a recruiter understands in 30 seconds and a hiring manager can explore for 10 minutes: a home page about me with projects as a section, and a page per project. For this project the embedded Power BI report is the centrepiece; the story and build sections show the thinking behind it. Many readers are not specialists, so the wording is plain English.

## 2. Stack and hosting

- **Static HTML, CSS and a little vanilla JS** in its own repository, the GitHub Pages user site, served at https://safwantisekar.github.io/ (this project: https://safwantisekar.github.io/projects/dubai-property/). No framework, no build step to deploy, no custom domain.
- This repository keeps **no copy** of the site. `make site` and `make site-shots` write into a local clone of it (`SITE_REPO_DIR` in `.env`); `make site-preview` serves the clone. Publishing is a commit and push in the site repository.
- The site repository deploys itself: its Pages workflow runs `tests/test_site.py` and publishes on every push to `main`.
- Links are root-relative (`/styles.css`, `/projects/dubai-property/`); `og:image` is an absolute URL, as social previews require.
- Tests: the site repository checks the pages (numbers vs `data/site.json`, links, images, contrast, privacy). Here, `tests/test_website_build.py` checks the build helpers and, when `SITE_REPO_DIR` is set, ties the site to this project (embed URL = docs/08 Publishing record, report gallery = the Power BI pages); in CI those checks skip.

## 3. Pages

```
SafwanTisekar.github.io/
  index.html                     home page
  styles.css  main.js  config.js  shared by every page
  data/site.json                 numbers (make site)
  data/projects.json             the project cards: the one place to add a project
  projects/dubai-property/
    index.html                   this project's page
    assets/figures/  assets/report/  assets/og.webp  assets/architecture.svg
```

**Home.** Hero, What I do, About, Experience, Skills, Projects, Education. The text is my own wording or taken from my CV (the CV itself is not published); nothing is invented, and any gap was a visible `TODO` note that blocked deploys until resolved. Projects render from `data/projects.json`: one project shows as a wide featured card, two or more as a grid.

**Project page (`projects/dubai-property/`).**

| Section | Content |
|---|---|
| Hero | Title, one-line pitch, four headline numbers (transactions and rent lines; latest full year's market sales; AVM error vs comparables; negative equity after a 20% fall); buttons: live report, GitHub repo, 5-minute tour |
| Live report | Publish-to-web iframe (16:9) behind a poster; a gallery of the nine page screenshots as the fallback |
| The story | The business question, then five findings with one chart each: mix shift, the index vs DLD's, the 2026 turn and the outlook, AVM vs comparables, the stress test |
| How it's built | Pipeline steps, tools, data quality and testing, limitations |

Footer: DLD CC BY 4.0, OpenStreetMap ODbL, data-as-of date, "Independent project, not affiliated with DLD. Not investment or lending advice."

**Adding a project:** an entry in `data/projects.json`, a page under `projects/<slug>/`, any new numbers in `build.collect`, then `make site`.

## 4. How the numbers get onto the page

`make site` (`src/dubai_property/website/build.py`) reads the main database, renders the project cards, and writes every number on both pages into its `<span data-kpi="key">`, plus `data/site.json` (value, label, source per key). Nothing is typed by hand, and the page stays plain HTML (readable without JavaScript, indexable). The values reuse reconciled code: the KPI query of `quality/kpi_reconciliation.py`, the card queries of `quality/pbi_cards.py` (so the site matches the Power BI cards), `models/report_4a.mix_shift_changes`, the index validation diagnostics and `hedonic_index.find_episodes`. The build fails on a span without a value or a value no page shows, and refuses a scratch database. It also converts the five story charts to WebP (1400 px wide).

## 5. Power BI embed

- `main.js` creates the iframe when the frame scrolls near or the poster is clicked, so the report never slows the first view.
- The embed URL lives in the site's `config.js`; a test checks it equals the docs/08 Publishing record.
- **Fallback:** the page screenshots and main findings show when JavaScript is off, when the iframe hasn't loaded after 20 s, or after `embedExpires`. The date is the reliable switch, because an expired Publish-to-web link still loads (an error page). Move the date on when the licence is renewed.
- **Screenshots:** File > Export > PDF in Desktop, then `make site-shots PDF=path/to/export.pdf`, which trims the margins and writes `p01.webp` … `p09.webp` in report order plus `og.webp` (the social preview, from the Executive page). Done on 2026-10-03.

## 6. Design

- Dark theme with one green accent, shared by both pages through `styles.css`; report screenshots and charts sit on light cards so they read as designed.
- Contrast tested: green on the background 6.9:1, on cards ≥ 5.9:1; buttons use dark text on green (6.75:1); body text 8.5:1.
- Manrope, self-hosted (variable weight, 25 KB, OFL), with system fonts as fallback.
- Accessibility: semantic landmarks, one `h1` per page, skip link, visible focus ring, alt text everywhere, declared image sizes, no animations.
- Layout: one 1160 px container with 16 px gutters; checked at 1440 px and 375 px with no horizontal scroll.
- Performance: no external requests before the report iframe; images as WebP.
- Wording: plain sentences, no em-dashes.
- Personal details: GitHub links only. Tests fail on email addresses, phone numbers, `mailto:` / `tel:`, LinkedIn, and any document file (a CV).

## 7. Content checklist

- [x] Headline numbers pulled from the database by `make site`
- [x] Five findings, each with one chart and a takeaway
- [x] Architecture: pipeline steps on the page; `architecture.svg` reused in the README
- [x] AVM metrics against the comparable-sales baseline
- [x] Limitations (EIBOR proxy, rate effect, illustrative stress test, provisional latest months, villa area basis, no building age or developer, nominal AED, part year)
- [x] Attribution and disclaimer
- [x] Report screenshots from the Desktop PDF export (2026-10-03)
- [ ] Lighthouse ≥ 90 on Performance, Accessibility and SEO on the deployed site

## 8. Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-02 | **One long page** with anchored sections instead of the five pages first planned (index, case study, methodology, data, about) | Recruiters scan one page; the depth lives in the repo docs and model cards, linked from the page |
| 2026-10-02 | Numbers written into the HTML at build time, not fetched by JavaScript | Static page reads without JS and is indexable; one source (`site.json`) and a test keep page and JSON equal |
| 2026-10-02 | Fallback switches on a configured licence end date as well as a load timeout | An expired Publish to web link still loads an error page, so a timeout alone can't detect it |
| 2026-10-02 | Screenshots from Desktop's PDF export (PyMuPDF dev dependency) | Exactly what the report shows, no browser automation |
| 2026-10-03 | GitHub links only: no email or LinkedIn on the site | Decided at plan review; a test rejects email addresses, `mailto:` and LinkedIn in `website/` |
| 2026-10-03 | Mix shift quoted from the published hedonic index (2023: raw +1% vs like for like +17%, `price_index.md`), not the Phase 3 fixed basket (+14.5%) | The site cites the published model |
| 2026-10-03 | The index finding says it reflects turns about 6 months sooner, likely because DLD's series appears to average 12 months (an inference); it never says the index predicts turns | Wording rule set at plan review |
| 2026-10-03 | The pipeline diagram on the page is an ordered list styled as steps, not an inline SVG | Readable text at phone width and native to screen readers; the SVG is kept for the README |
| 2026-10-03 | **Two-page structure:** a personal home page with projects as a section, and this project on its own page | The site is about me; more projects can be added as cards |
| 2026-10-03 | Home content only from the CV; gaps are visible `TODO` notes, blocked at deploy | Nothing about me is invented |
| 2026-10-03 | Project cards rendered at build time from `data/projects.json` | One place to add a project; the page stays static |
| 2026-10-03 | Experience: "improvement" in payment turnaround confirmed; GST input tax credit loss prevented stated as INR 7.2 crore (18% of INR 40 crore), about AED 2.7 million (26.23 INR per AED, 2 Oct 2026); Unilever is the only role | My answers to the home-page TODOs |
| 2026-10-03 | Restyle: dark theme, green accent, self-hosted Manrope, photo mosaic hero; home sections Hero, What I do, About, Experience, Skills, Projects, Education | My style reference and content brief |
| 2026-10-03 | Hero: new photo with the background removed, no project numbers; Experience adds month-end close support and IT/vendor coordination (confirmed by me, beyond the CV) | Review of the restyle |
| 2026-10-03 | Charts and report screenshots open in a native `<dialog>` viewer (Esc closes, focus returns to the link; without JavaScript the link opens the image) | Charts were too small to read in the two-column findings layout |
| 2026-10-03 | **The site moved to its own repository**, the GitHub Pages user site `SafwanTisekar.github.io` (no custom domain). `make site` writes into its clone (`SITE_REPO_DIR`); this repository's Pages workflow and `website/` folder are removed; links are root-relative | A personal site with several projects shouldn't live inside one project's repository |
