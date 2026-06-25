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

- `https://mhasnain5924117.github.io/Repos/`

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

