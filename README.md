# Muhammad Hasnain Portfolio Website

This repository uses a **single** website source:

- `docs/` (GitHub Pages publish source)

---

## Deploy publicly from this repository

1. Open your GitHub repository.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**:
   - Source: **Deploy from a branch**
   - Branch: `main`
   - Folder: `/docs`
4. Save.
5. Wait for Pages to finish building (usually 1-3 minutes).

Public URL for this repo:

- `https://mhasnain5924117.github.io/`

---

## Quick local preview

From repo root:

```bash
python3 -m http.server 8080
```

Open:

- `http://localhost:8080/docs/`

---

## Site structure

Everything lives in a single static page, `docs/index.html`, with these sections (in order):
About (with Education), Research (three thrusts, future directions, software, collaborations),
Publications (selected, then grouped full list), Teaching and Mentoring, Talks, Awards and Funding,
Service and Outreach, News, Contact and References.

Supporting files:

- `docs/assets/css/styles.css` – styles, including print rules
- `docs/assets/js/main.js` – mobile menu and nav highlighting only
- `docs/assets/cv/Muhammad_Hasnain_CV.pdf` – the file behind every "CV (PDF)" link
- `docs/assets/images/photos/` – conference, poster, and teaching photographs
- `docs/assets/images/figures/` – result figures taken from the papers and presentations
- `docs/assets/images/og-image.jpg` – 1200x630 social-preview collage
- `docs/updates.html` – redirect to `/#news` (kept for old links)

## Content update workflow

### 1) Add a publication

In `docs/index.html` under `#publications`, add an `<li>` to the matching group
(Journal articles / Refereed conference papers / Preprints / Presentations / Posters).
Use the full author list with `<strong>M. Hasnain</strong>`, and include the DOI string as a link.
Update the "Selected publications" block only for the 3–5 most important works.

### 2) Add a news item

Add a one-line `<li><time datetime="YYYY-MM">Mon YYYY</time> ...</li>` at the top of `#news`.

### 3) Add a photo

1. Resize to at most 1200 px on the long edge and save as JPEG in `docs/assets/images/photos/`.
2. Reference it with descriptive `alt` text and a `<figcaption>`.
3. Never add transcripts, certificates, ID documents, or other personal records.

### 4) Refresh the CV

Replace `docs/assets/cv/Muhammad_Hasnain_CV.pdf` with the current CV (same filename) and update the
"Last updated" date in the footer of `docs/index.html`. Before uploading, remove the phone number
and any home address from the PDF (true redaction, not a black box drawn over the text) and strip
document metadata; the hosted copy should carry only the university e-mail.

### 5) Keep SEO current

When URL structure changes, update:

- `docs/index.html` canonical + OG URL/image
- `docs/robots.txt` sitemap line
- `docs/sitemap.xml` `<loc>` and `<lastmod>` entries

