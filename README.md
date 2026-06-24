# Muhammad Hasnain Research Portfolio (GitHub Pages)

Production-ready personal researcher portfolio for **Muhammad Hasnain** with:

- Modern, formal, mobile-first design
- Personal narrative integrated with academic credibility
- SEO-ready metadata and structured data
- Fast static deployment on GitHub Pages
- Simple update workflows for publications, conference photos, and milestones

---

## 1) File Structure

```text
.
├── .nojekyll
├── index.html
├── updates.html
├── robots.txt
├── sitemap.xml
├── README.md
└── assets
    ├── css
    │   └── styles.css
    ├── js
    │   └── main.js
    └── images
        ├── og-image.svg
        ├── profile-placeholder.svg
        ├── conference-placeholder-1.svg
        ├── conference-placeholder-2.svg
        └── conference-placeholder-3.svg
```

---

## 2) Quick Start (Local Preview)

From the repository root:

```bash
python3 -m http.server 8080
```

Then open:

- `http://localhost:8080/`

---

## 3) Deploy to GitHub Pages

### Option A (Recommended): User Site
Use repository name: **`mhasnain5924117.github.io`**  
This gives the clean URL:

- `https://mhasnain5924117.github.io/`

### Option B: Project Site
If repository name is different, URL will be:

- `https://mhasnain5924117.github.io/<repo-name>/`

If using Option B, update these URLs in:

- `index.html` (canonical + OG URL/image)
- `updates.html` (canonical + OG URL/image)
- `robots.txt` (sitemap URL)
- `sitemap.xml` (`<loc>` values)

### GitHub Pages Setup Steps

1. Push this code to GitHub.
2. Open repository **Settings**.
3. Go to **Pages**.
4. Under **Build and deployment**, choose:
   - **Source:** Deploy from a branch
   - **Branch:** `main` (or your portfolio branch), folder `/ (root)`
5. Save and wait for deployment.
6. Verify the public URL and test on mobile + desktop.

---

## 4) Content Update Guide

### A) Replace personal photo

1. Add your image to `assets/images/` (example: `profile.jpg`).
2. In `index.html`, update hero image:
   - From: `assets/images/profile-placeholder.svg`
   - To: `assets/images/profile.jpg`
3. Keep portrait ratio close to 1:1 and optimized size (WebP/JPEG under ~300 KB if possible).

### B) Add conference/event photos

1. Add images to `assets/images/` (example: `icml-2026-talk.webp`).
2. In `index.html`, section `#conferences`, replace placeholder `src`.
3. Update each `<figcaption>` with real event + year.
4. Keep descriptive `alt` text for accessibility and image SEO.

### C) Add/update publications

Recommended approach:

- Keep full authoritative list on **Google Scholar** and **OpenReview**.
- On this site, highlight selected works and link out.

How to edit:

1. Open `index.html`.
2. Go to section `#research`.
3. Add publication entries as short citation bullets inside the Publications card or create an additional card.
4. Keep each citation with:
   - Title
   - Venue
   - Year
   - Link (DOI/arXiv/OpenReview/Publisher)

### D) Add awards/scholarships

1. Open `index.html`.
2. Edit section `#awards`.
3. Add concise entries with award name, institution, and year.
4. Keep impact-oriented phrasing (avoid overstatement).

### E) Add updates/blog entries

1. Open `updates.html`.
2. Duplicate one `<article class="update-item">...</article>` block.
3. Update:
   - `datetime` in `<time>`
   - heading
   - short summary with links
4. Keep newest entry at the top.

---

## 5) SEO Checklist (Implemented + Ongoing)

### Implemented in code

- [x] Unique `<title>` and meta description
- [x] Keyword-targeted metadata
- [x] Canonical URLs
- [x] Open Graph + Twitter metadata
- [x] `robots.txt`
- [x] `sitemap.xml`
- [x] Structured data (Schema.org Person + publication work entity)
- [x] Internal links (header anchors + updates page link)
- [x] Mobile-responsive design
- [x] Accessibility basics (landmarks, heading hierarchy, skip link, alt text)

### Keep doing after launch

- [ ] Add exact publication titles and links for long-tail indexing
- [ ] Use real conference image filenames (`neurips-2026-poster.webp`) for semantic SEO
- [ ] Keep updates page active (freshness signal)
- [ ] Compress all images before upload
- [ ] Re-check canonical/sitemap URLs if repo path changes

---

## 6) Personal Narrative Guidance (Professional, Not Melodramatic)

Use this framing consistently:

1. **Fact-first storytelling**  
   State concrete facts (first from village abroad, scholarship-supported trajectory, family responsibility).

2. **Research-forward identity**  
   Pair story with outcomes: publications, conferences, ongoing PhD research impact.

3. **Tone discipline**  
   Avoid emotional exaggeration. Use calm, credible phrasing with measurable details.

4. **Bridge narrative and mission**  
   Connect adversity to purpose: rigorous research, mentorship, and broader educational access.

Suggested recurring sentence style:

> "My background shaped my resilience; my research reflects my commitment to practical, high-impact scholarship."

---

## 7) Recommended Next Improvements

- Add a downloadable CV PDF (`assets/docs/muhammad-hasnain-cv.pdf`) and link in hero/contact.
- Add "Selected Publications" with 5-8 fully formatted citations.
- Add a "Research Projects" subsection with methods, datasets, and outcomes.
- Add conference-specific pages if media/story depth grows.

---

## 8) Reference Links Used

- LinkedIn: <https://www.linkedin.com/in/mhasnain1/>
- Google Scholar: <https://scholar.google.com/citations?user=YYpAj5AAAAAJ&hl=en>
- OpenReview: <https://openreview.net/profile?id=~Muhammad_Hasnain1>
- ORCID: <https://orcid.org/0009-0004-6871-9713>
- GitHub: <https://github.com/mhasnain5924117>

---

## 9) Maintenance Routine (Monthly)

1. Add latest publication(s) and conference activity.
2. Add one brief update post.
3. Review contact details and active links.
4. Rebuild social preview image if major profile changes happen.
5. Commit and push updates.

