# Muhammad Hasnain Portfolio Website

This repository now keeps the website in a **dedicated folder**:

- `docs/`

That gives you one clean place to manage the site instead of mixing website files with other project files.

---

## Website location (single source of truth)

```text
docs/
├── .nojekyll
├── index.html
├── updates.html
├── robots.txt
├── sitemap.xml
└── assets/
    ├── css/styles.css
    ├── js/main.js
    └── images/
```

---

## Deploy with GitHub Pages (from `docs/`)

1. Open your GitHub repository.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**:
   - Source: **Deploy from a branch**
   - Branch: `main`
   - Folder: `/docs`
4. Save.

This publishes the website from the dedicated `docs/` folder.

---

## If you want a completely separate website repository

Best option: create a new repo named:

- `mhasnain5924117.github.io`

Then copy the **contents of `docs/`** into that repository root.

That gives the clean user-site URL:

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

## Content update workflow

### 1) Update bio/research sections

- Edit: `docs/index.html`
- Sections to maintain:
  - About
  - Journey
  - Research Experience
  - Publications
  - Awards
  - Teaching/Service
  - Contact

### 2) Add new publications

In `docs/index.html` under `#publications`:

- Add citation with title, venue, year, DOI/link
- Keep newest/high-impact works near top

### 3) Add conference photos

1. Upload image to `docs/assets/images/`
2. Replace placeholder paths in `#conferences`
3. Update figure captions and alt text

### 4) Add new updates/blog entries

Edit `docs/updates.html`:

- Duplicate one `<article class="update-item">...</article>`
- Update `time datetime`, title, and summary
- Keep newest entry first

### 5) Keep SEO current

When URL structure changes, update:

- `docs/index.html` canonical + OG URL/image
- `docs/updates.html` canonical + OG URL/image
- `docs/robots.txt` sitemap line
- `docs/sitemap.xml` `<loc>` entries

---

## SEO already implemented

- Meta title, description, and keyword targeting
- Open Graph and Twitter metadata
- Structured data (Schema.org Person + scholarly work)
- Internal linking and semantic headings
- Mobile-first responsive layout
- Sitemap and robots
- Accessible navigation (skip link, landmarks, clear hierarchy)

---

## Narrative guidance (professional, authentic)

Use this framing style for future edits:

1. Fact-first background context
2. Research outcomes and technical depth
3. Scholarship/funding thread as opportunity multiplier
4. Forward-looking mission (impact, mentorship, rigorous science)

Keep tone confident and evidence-based (not dramatic).

