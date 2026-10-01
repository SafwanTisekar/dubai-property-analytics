# 07 – Portfolio Website

## 1. Goal

A fast, professional, single-project site that a recruiter can understand in 30 seconds and a hiring manager can explore for 10 minutes. The embedded Power BI report is the centrepiece, and the case study proves the thinking behind it.

## 2. Stack and hosting

- **Static HTML + CSS + a little vanilla JS** in `website/`. No framework and no build step, so it's easy to maintain.
- Hosted on **GitHub Pages** via `.github/workflows/pages.yml` (deploys `website/` on push to `main`).
- Optional custom domain (e.g. `safwantisekar.com`) through a CNAME. HTTPS is automatic.
- Lightweight charts for non-Power BI visuals: static PNG/SVG exported from Python (`reports/figures`).

## 3. Site map

| Page | Purpose | Content |
|---|---|---|
| `index.html`: **Home** | Hook + dashboard | Hero: title, one-line pitch, 3 headline numbers (e.g. "1.6M transactions · AED Xbn traded · AVM ±10% hit rate Y%"). **Embedded Power BI report** (responsive iframe). Buttons: Case Study, GitHub, Download PBIX |
| `case-study.html` | The story | Business problem → questions → approach → 5–7 key findings with supporting charts → recommendations → limitations → "How this maps to UAE banking and real-estate work (collateral AVMs, LTV monitoring, off-plan risk, rate sensitivity)" |
| `methodology.html` | Technical depth | Architecture diagram, medallion layers, star schema, data-quality results (from `reports/dq_report.md`), modelling approach, leakage controls, model card metrics, SHAP images, hedonic index vs DLD index, stress-test assumptions |
| `data.html` | Transparency | Sources and licences, data dictionary (generated), row counts per layer |
| `about.html` | You | Short bio, skills matrix mapped to the project, CV download, LinkedIn, email |

## 4. Power BI embed

```html
<div class="report-frame">
  <iframe
    title="Dubai Property Market & Mortgage Risk Analytics – Power BI report"
    src="<!-- Publish-to-web URL from docs/06 §6 -->"
    loading="lazy"
    allowfullscreen="true"></iframe>
</div>
<noscript><img src="assets/report-fallback.png" alt="Screenshot of the Executive Summary page"></noscript>
```

```css
.report-frame { position: relative; width: 100%; aspect-ratio: 16 / 9; }
.report-frame iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }
@media (max-width: 700px) { .report-frame { aspect-ratio: 9 / 16; } } /* consider linking to full screen on mobile */
```

- The embed URL lives in `website/config.js` (one place to update).
- **Fallback:** if the iframe fails or the licence has lapsed, show a screenshot carousel of all six pages plus a 30–60 s GIF/MP4 walkthrough. Always ship these regardless.
- Add `?pageName=` links to jump straight to specific report pages from the case study.

## 5. Design

- Clean, finance-appropriate look: neutral background, one accent colour matching the Power BI theme, system font stack or one Google Font.
- Light/dark mode via `prefers-color-scheme`.
- Mobile-first, max content width about 1100 px, and no horizontal scroll at 375 px.
- Accessibility: semantic HTML, alt text, colour contrast AA.
- Performance: Lighthouse ≥ 90 on Performance/Accessibility/SEO. Compress images (WebP) and lazy-load the iframe.
- SEO/social: `<title>`, meta description, Open Graph image (a dashboard screenshot).

## 6. Content checklist

- [ ] Headline numbers pulled from the final gold tables (not typed from memory)
- [ ] 5–7 findings, each with one chart and a "so what" sentence
- [ ] Architecture diagram exported as SVG
- [ ] Model card summary table (Gini/KS/AUC for baseline, Model A, Model B)
- [ ] Limitations section (right-censoring, `last_pymnt_d` timing proxy, US data, simplified LGD/EAD)
- [ ] Links: GitHub repo, PBIX download, LinkedIn, CV
- [ ] Attribution: "Data: Dubai Land Department, CC BY 4.0", and "Area locations © OpenStreetMap contributors (ODbL)" in the credits (the report's map uses OSM centroids, Phase 5); disclaimer: independent project, not affiliated with DLD; not investment or lending advice
