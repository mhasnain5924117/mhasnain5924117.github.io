# Muhammad Hasnain Portfolio Website

Live site: https://mhasnain5924117.github.io/

## Editing the site (no coding needed)

1. Go to **https://app.pagescms.org** and sign in with your GitHub account.
2. Open this repository (`mhasnain5924117.github.io`).
3. Pick a section on the left (Publications, News, Talks, Awards, Profile, Research, Teaching, Service, Contact).
4. Change the form fields, add an item with **Add an entry**, drag items to reorder them, and click **Save**.

About two minutes after saving, the live site updates by itself.

In any text field you can write:

- `*italic*` for *italic* (journal names),
- `**bold**` for **bold**,
- `[link text](https://address)` for a link.

Helpful details:

- **New items go at the top** of their list (newest first).
- **Publications:** write your name as `M. Hasnain`; it is bolded automatically. Choose the group
  (journal, conference, preprint, presentation, poster) and the status (published, in print, to appear,
  under review). Tick "Show in Selected publications" for your 3–5 best papers. The publication counts in
  "At a glance" and the key numbers at the top update by themselves.
- **Dates for news and talks** are written as year-month, for example `2026-11`.
- **Photos:** upload them in the photo field. Keep them under about 1200 px on the long side, and always
  fill in the description. Never upload transcripts, certificates, ID documents, or other personal records.
- **CV:** upload the new PDF in Profile → CV file, using the same file name
  (`Muhammad_Hasnain_CV.pdf`). Remove the phone number and home address from the PDF first.

If something is typed incorrectly (for example a date written as "Nov 2026"), the site simply does not
update and GitHub emails you the reason; fix the field in Pages CMS and save again. The live site keeps
showing the last good version in the meantime.

---

## How it works (for reference)

| Folder or file | What it holds |
| --- | --- |
| `content/*.yml` | All the words, lists, and photo choices on the page (what Pages CMS edits) |
| `templates/index.html.j2` | The page layout |
| `tools/build_site.py` | Combines the two into `docs/index.html`, checking for missing files and typos |
| `docs/` | The published website: styles, scripts, photos, figures, videos, CV |
| `.github/workflows/build-site.yml` | Rebuilds and publishes the site after every change |
| `.pages.yml` | Defines the Pages CMS editing forms |
| `tools/research-animations/` | Renderer for the four animated research summaries |

**Publishing setting:** Settings → Pages → Build and deployment → Source must be **GitHub Actions**.

**Building on a computer** (optional, for developers):

```bash
pip install -r tools/requirements.txt
python tools/build_site.py
python -m http.server 8080 --directory docs   # then open http://localhost:8080/
```

Do not edit `docs/index.html` by hand; it is regenerated from `content/` on every change.

### Re-render an animated summary

The animations are generated, not hand-edited. Install `numpy pillow matplotlib contourpy` plus `ffmpeg`, then:

```bash
cd tools/research-animations
python3 render_animations.py --animation bfs --preview --times 4,18,30   # quick PNG frames in out/preview
python3 render_animations.py --animation all --render --out ../../docs/assets/videos
```

Each one is a short, silent animation driven by a simplified model of the paper's physics; the captions
double as the on-page narration. Keep the "Illustrative animation" footnote.

### Search engines

When the site address changes, update `SITE_URL` in `tools/build_site.py`, `docs/robots.txt`, and
`docs/sitemap.xml`.
