"""Build docs/index.html from the content/*.yml files and templates/index.html.j2.

Run from the repository root:

    pip install -r tools/requirements.txt
    python tools/build_site.py

GitHub Actions runs this automatically whenever content/ or templates/ change (see
.github/workflows/build-site.yml), so editing the YAML files is all that is needed to update the site.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, Undefined
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
OUTPUT = ROOT / "docs" / "index.html"
SITE_URL = "https://mhasnain5924117.github.io/"
OWN_NAME = "M. Hasnain"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# (category, heading, folded behind a "show" toggle to keep the page short)
PUB_GROUPS = [
    ("journal", "Journal articles", False),
    ("conference", "Refereed conference papers", False),
    ("preprint", "Preprints and manuscripts under review", False),
    ("presentation", "Conference presentations and abstracts", True),
    ("poster", "Posters", True),
]
STATUSES = {"published", "in print", "to appear", "under review"}


# ---------------------------------------------------------------- text formatting


def _link_attrs(url: str) -> str:
    if url.startswith(("http://", "https://", "assets/")):
        return ' target="_blank" rel="noopener"'
    return ""


def md(text) -> Markup:
    """Turn the small formatting set used in content/ into HTML: *italic*, **bold**, [text](url)."""
    if text is None or isinstance(text, Undefined):
        return Markup("")
    s = html.escape(" ".join(str(text).split()), quote=False)

    def link(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        return f'<a href="{url.replace(chr(34), "%22")}"{_link_attrs(html.unescape(url))}>{label}</a>'

    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\*\w])\*(?![\s\*])(.+?)(?<![\s\*])\*(?![\*\w])", r"<em>\1</em>", s)
    return Markup(s)


def month(value) -> str:
    """'2026-04' -> 'Apr 2026'."""
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", str(value).strip())
    if not m:
        return str(value)
    return f"{MONTHS[int(m.group(2)) - 1]} {m.group(1)}"


def lower_first(text: str) -> str:
    text = str(text)
    return text[:1].lower() + text[1:] if text and not text[:2].isupper() else text


def links_json(links) -> str:
    return json.dumps([{"label": l["label"], "href": l["url"]} for l in links or []], ensure_ascii=False)


# ---------------------------------------------------------------- publications


def citation(p: dict) -> Markup:
    status = p.get("status", "published")
    authors = html.escape(p["authors"], quote=False).replace(OWN_NAME, f"<strong>{OWN_NAME}</strong>")
    parts = [authors + ".", str(md(p["title"])).rstrip(".") + "."]
    venue = f"<em>{md(p['venue'])}</em>"
    if status == "under review":
        venue = "Under review, " + venue
    if p.get("details"):
        venue += ", " + str(md(p["details"]))
    parts.append(venue + ".")
    if status in ("to appear", "in print"):
        parts.append(f'<span class="pub-status">{status.capitalize()}</span>')
    links = [f'<a class="doi" href="{html.escape(l["url"])}" target="_blank" rel="noopener">{html.escape(l["label"])}</a>'
             for l in p.get("links") or []]
    if links:
        parts.append(" · ".join(links))
    if p.get("award"):
        parts.append(f"<strong>{md(p['award'])}</strong>")
    return Markup(" ".join(parts))


def publication_counts(items: list[dict]) -> str:
    def count(pred):
        return sum(1 for p in items if pred(p))

    journals = count(lambda p: p["category"] == "journal" and p.get("status") in ("published", "in print"))
    conferences = count(lambda p: p["category"] == "conference" and p.get("status", "published") == "published")
    to_appear = count(lambda p: p.get("status") == "to appear")
    under_review = count(lambda p: p.get("status") == "under review")

    def n(k, one, many):
        return f"{k} {one if k == 1 else many}"

    bits = [n(journals, "journal article", "journal articles"),
            n(conferences, "refereed conference paper", "refereed conference papers")]
    if to_appear:
        bits.append(f"{to_appear} to appear")
    if under_review:
        bits.append(f"{under_review} under review")
    return ", ".join(bits)


# ---------------------------------------------------------------- checks


def check(content: dict) -> list[str]:
    """Catch the mistakes that are easy to make when editing by hand."""
    problems = []
    areas = len(content["research"].get("areas") or [])
    for f in content["profile"].get("research_focus") or []:
        if not isinstance(f.get("area"), int) or not 1 <= f["area"] <= areas:
            problems.append(f"profile.yml: research focus '{f.get('label')}' should point to an area number from 1 to {areas}")
    groups = {g for g, _, _ in PUB_GROUPS}
    for i, p in enumerate(content["publications"]["items"], 1):
        label = f'publication #{i} ("{str(p.get("title", "?"))[:50]}")'
        for field in ("authors", "title", "venue", "category"):
            if not p.get(field):
                problems.append(f"{label} is missing '{field}'")
        if p.get("category") and p["category"] not in groups:
            problems.append(f"{label}: category must be one of {', '.join(sorted(groups))}")
        if p.get("status", "published") not in STATUSES:
            problems.append(f"{label}: status must be one of {', '.join(sorted(STATUSES))}")
    for file, key in (("news", "items"), ("talks", "invited"), ("talks", "contributed")):
        for item in content[file].get(key) or []:
            if not re.fullmatch(r"\d{4}-\d{1,2}", str(item.get("date", ""))):
                problems.append(f"{file}.yml: date '{item.get('date')}' should look like 2026-04")
    for path in re.findall(r'(assets/[^\s"\')]+)', json.dumps(content, default=str)):
        if not (ROOT / "docs" / path).exists():
            problems.append(f"file not found: docs/{path}")
    for project in content["research"]["selected_projects"]:
        for suffix in ("-720p.mp4", "-1080p.mp4", "-poster.jpg", ".vtt"):
            if not (ROOT / "docs" / "assets" / "videos" / f"{project['video']}{suffix}").exists():
                problems.append(f"video file not found: docs/assets/videos/{project['video']}{suffix}")
    return problems


# ---------------------------------------------------------------- structured data for search engines


def person_json(profile: dict, contact: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "@id": f"{SITE_URL}#person",
        "name": profile["name"],
        "givenName": profile["name"].split()[0],
        "familyName": profile["name"].split()[-1],
        "jobTitle": profile["title"].split(", Texas")[0],
        "description": " ".join(profile["seo"]["description"].split()),
        "url": SITE_URL,
        "image": SITE_URL + profile["photo"]["image"],
        "email": "mailto:" + profile["email"],
        "affiliation": {
            "@type": "CollegeOrUniversity",
            "name": "Texas A&M University",
            "department": "J. Mike Walker '66 Department of Mechanical Engineering",
            "url": "https://engineering.tamu.edu/mechanical/",
        },
        "alumniOf": [
            {"@type": "CollegeOrUniversity", "name": "Georgia Southern University", "url": "https://www.georgiasouthern.edu/"},
            {"@type": "CollegeOrUniversity", "name": "Ghulam Ishaq Khan Institute of Engineering Sciences and Technology", "url": "https://giki.edu.pk/"},
        ],
        "sameAs": [l["url"] for l in contact["profiles"]],
        "knowsAbout": profile["seo"].get("topics", []),
    }
    return json.dumps(data, indent=2, ensure_ascii=False).replace("</", "<\\/")


def videos_json(research: dict, profile: dict) -> str:
    items = []
    for i, p in enumerate(research["selected_projects"], 1):
        v = f"{SITE_URL}assets/videos/{p['video']}"
        items.append({
            "@type": "VideoObject",
            "position": i,
            "name": p["video_title"],
            "description": " ".join(p["video_description"].split()),
            "thumbnailUrl": f"{v}-poster.jpg",
            "contentUrl": f"{v}-1080p.mp4",
            "uploadDate": "2026-10-21",
            "duration": f"PT{p.get('video_length_seconds', 32)}S",
            "author": {"@id": f"{SITE_URL}#person"},
        })
    data = {"@context": "https://schema.org", "@type": "ItemList",
            "name": f"Research animations by {profile['name']}", "itemListElement": items}
    return json.dumps(data, indent=2, ensure_ascii=False).replace("</", "<\\/")


# ---------------------------------------------------------------- build


def load_content() -> dict:
    content = {}
    for path in sorted(CONTENT.glob("*.yml")):
        with path.open(encoding="utf-8") as f:
            try:
                content[path.stem] = yaml.safe_load(f) or {}
            except yaml.YAMLError as err:
                sys.exit(f"Could not read {path.relative_to(ROOT)}:\n{err}")
    return content


def build(today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    c = load_content()
    problems = check(c)
    if problems:
        sys.exit("Please fix these before the site can be built:\n  - " + "\n  - ".join(problems))

    pubs = c["publications"]["items"]
    counts = publication_counts(pubs)

    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True, undefined=StrictUndefined,
                      keep_trailing_newline=True)
    env.undefined = Undefined  # optional fields may be left out of the YAML files
    journals = sum(1 for p in pubs if p["category"] == "journal" and p.get("status") in ("published", "in print"))
    tokens = {"[[publication counts]]": counts, "[[journal articles]]": str(journals),
              "[[total publications]]": str(sum(1 for p in pubs if p["category"] in ("journal", "conference")
                                                and p.get("status") in ("published", "in print"))),
              "[[citations]]": str(c.get("metrics", {}).get("citations", "")),
              "[[h-index]]": str(c.get("metrics", {}).get("h_index", ""))}

    def fill(text) -> Markup:
        text = str(text)
        for key, value in tokens.items():
            text = text.replace(key, value)
        return md(text)

    env.filters.update(md=md, month=month, lower_first=lower_first, links_json=links_json, citation=citation,
                       glance=fill, tokens=fill)

    profile = c["profile"]
    return env.get_template("index.html.j2").render(
        **c,
        site_url=SITE_URL,
        page_title=f"{profile['name']} | {profile['title']}",
        selected_pubs=[p for p in pubs if p.get("selected")],
        pub_groups=[{"heading": h, "collapsed": folded, "items": [p for p in pubs if p["category"] == g]}
                    for g, h, folded in PUB_GROUPS if any(p["category"] == g for p in pubs)],
        person_json=Markup(person_json(profile, c["contact"])),
        videos_json=Markup(videos_json(c["research"], profile)),
        updated_iso=today.isoformat(),
        updated_label=today.strftime("%B %Y"),
    )


def main() -> None:
    page = build()
    OUTPUT.write_text(page, encoding="utf-8", newline="\n")
    print(f"Built {OUTPUT.relative_to(ROOT)} ({len(page):,} characters)")


if __name__ == "__main__":
    main()
