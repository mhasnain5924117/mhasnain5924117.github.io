# mhasnain.github.io (Dedicated Website Package)

This folder is a complete standalone website package for your portfolio.

- Target repository name: `mhasnain.github.io`
- Website root file: `index.html`

---

## 1) What is included

```text
mhasnain.github.io/
├── index.html
├── updates.html
├── robots.txt
├── sitemap.xml
└── assets/
    ├── css/styles.css
    ├── js/main.js
    ├── data/
    │   ├── publications.json        # interactive publication explorer data
    │   └── linkedin-posts.json      # timeline gallery data
    ├── docs/
    │   ├── bachelors-transcript-evaluation.pdf
    │   ├── masters-official-transcript.pdf
    │   ├── phd-unofficial-transcript-2026-06-23.pdf
    │   └── ugrad-certificate-letter-4gpa.pdf
    └── images/
        ├── posts/                   # LinkedIn milestone images
        ├── real/                    # profile and key visual images
        ├── flow-pattern.svg
        └── og-image.svg
```

---

## 2) Preview the website locally (private, only on your computer)

From this folder:

```bash
python3 -m http.server 8080
```

Then open:

- `http://localhost:8080`

---

## 3) Edit guide (most common changes)

### Change headline / bio / section text
- File: `index.html`

### Add or edit publications
- File: `assets/data/publications.json`
- The publication cards update automatically from this JSON.

### Add or edit milestone timeline posts and image galleries
- File: `assets/data/linkedin-posts.json`
- Add post image files to `assets/images/posts/`.

### Add/replace transcripts
- Put PDF files in `assets/docs/`
- Update links in the Education section of `index.html`.

### Add new updates/blog entries
- File: `updates.html`

---

## 4) Publish later (when ready)

1. Create GitHub repo `mhasnain.github.io`
2. Copy this folder contents into that repo root
3. Push to `main`
4. Enable Pages from `main` branch `/ (root)`

---

## 5) Important privacy note

If you do not enable GitHub Pages, the site is not publicly deployed.
