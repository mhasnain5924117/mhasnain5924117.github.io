# mhasnain.github.io (Dedicated Website Repository Contents)

This folder is ready to become your standalone GitHub Pages repository:

- Repository name: `mhasnain.github.io`
- Publish from: repository root
- Final URL: `https://mhasnain.github.io/`

---

## 1) Files you will manage

```text
mhasnain.github.io/
├── .nojekyll
├── index.html
├── updates.html
├── robots.txt
├── sitemap.xml
└── assets/
    ├── css/styles.css
    ├── js/main.js
    └── images/
        ├── real/                  # downloaded LinkedIn post/profile images
        ├── flow-pattern.svg
        └── og-image.svg
```

---

## 2) How to preview locally

From inside this folder:

```bash
python3 -m http.server 8080
```

Open:

- `http://localhost:8080`

---

## 3) How to publish (first time)

1. Create a new GitHub repository named `mhasnain.github.io`.
2. Copy all files from this folder into that repo root.
3. Push to `main`.
4. In GitHub repo settings:
   - Go to **Settings → Pages**
   - Source: **Deploy from a branch**
   - Branch: `main`, folder: `/ (root)`
5. Wait for deployment.
6. Open `https://mhasnain.github.io/`.

---

## 4) How to make edits later

### Update profile/about/research text
- Edit `index.html`

### Add or replace photos
- Add files to `assets/images/real/`
- Update image `src` paths in `index.html`

### Add a new publication update
- Edit `updates.html`
- Duplicate one update card block and modify date/title/text

### Keep SEO updated if URLs change
- `index.html` and `updates.html` canonical + OG tags
- `robots.txt` sitemap line
- `sitemap.xml` URLs

---

## 5) Notes on LinkedIn media

Current real images were pulled from publicly accessible LinkedIn post preview media URLs and mapped into the conference/publication section.
