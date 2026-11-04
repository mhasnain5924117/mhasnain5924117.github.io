"""Refresh citation numbers and look for publications that are not on the site yet.

Run by .github/workflows/build-site.yml every two weeks:

1. Reads total citations and h-index from the Google Scholar profile and updates content/metrics.yml.
   If Google Scholar cannot be reached (it sometimes blocks automated visits), the numbers are left as they are.
2. Lists the DOIs on the ORCID record and reports any whose paper is not in content/publications.yml.
   Preprints of papers already on the site (same title) are ignored. The report is written to
   new-publications.md so the workflow can open a GitHub issue, which GitHub emails to the owner.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "content" / "metrics.yml"
PUBLICATIONS = ROOT / "content" / "publications.yml"
REPORT = ROOT / "new-publications.md"

SCHOLAR_URL = "https://scholar.google.com/citations?user=YYpAj5AAAAAJ&hl=en"
ORCID_ID = "0009-0004-6871-9713"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def get(url: str, accept: str = "text/html") -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "ignore")


def norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def refresh_scholar() -> None:
    try:
        page = get(SCHOLAR_URL)
    except Exception as err:  # network errors or a block page
        print(f"Google Scholar not reachable ({err}); keeping the current numbers.")
        return
    numbers = re.findall(r'class="gsc_rsb_std">(\d+)<', page)
    if len(numbers) < 3:
        print("Google Scholar page did not contain the citation table; keeping the current numbers.")
        return
    citations, h_index = int(numbers[0]), int(numbers[2])
    current = yaml.safe_load(METRICS.read_text(encoding="utf-8")) or {}
    if citations < int(current.get("citations", 0)) * 0.8:
        print(f"Google Scholar returned {citations} citations, far below {current.get('citations')}; ignoring.")
        return
    text = METRICS.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^citations:.*$", f"citations: {citations}", text)
    text = re.sub(r"(?m)^h_index:.*$", f"h_index: {h_index}", text)
    if (citations, h_index) != (current.get("citations"), current.get("h_index")):
        text = re.sub(r"(?m)^updated:.*$", f"updated: {dt.date.today().isoformat()}", text)
    METRICS.write_text(text, encoding="utf-8", newline="\n")
    print(f"Google Scholar: {citations} citations, h-index {h_index}.")


def find_new_publications() -> list[str]:
    pubs = (yaml.safe_load(PUBLICATIONS.read_text(encoding="utf-8")) or {}).get("items", [])
    known_dois = {m.lower() for p in pubs for l in p.get("links") or []
                  for m in re.findall(r"(10\.\d{4,9}/[^\s?#]+)", l.get("url", ""))}
    known_titles = {norm(p.get("title", "")) for p in pubs}

    try:
        works = json.loads(get(f"https://pub.orcid.org/v3.0/{ORCID_ID}/works", "application/json"))
    except Exception as err:
        print(f"ORCID not reachable ({err}); skipping the publication check.")
        return []

    found = []
    for group in works.get("group", []):
        summary = (group.get("work-summary") or [{}])[0]
        title = ((summary.get("title") or {}).get("title") or {}).get("value", "")
        dois = [e["external-id-value"].lower() for e in group.get("external-ids", {}).get("external-id", [])
                if e.get("external-id-type") == "doi"]
        if any(d in known_dois for d in dois):
            continue
        if title and norm(title) in known_titles:
            continue  # same paper already listed (for example its SSRN or arXiv preprint)
        year = ((summary.get("publication-date") or {}).get("year") or {}).get("value", "")
        venue = (summary.get("journal-title") or {}).get("value", "")
        link = f"https://doi.org/{dois[0]}" if dois else ""
        found.append(f"- **{title or 'Untitled'}**{f' ({venue})' if venue else ''}{f', {year}' if year else ''}"
                     f"{f' — {link}' if link else ''}")
    return found


def main() -> None:
    refresh_scholar()
    new = find_new_publications()
    if new:
        REPORT.write_text(
            "These works are on your ORCID record but not on your website yet. To add one, open "
            "Pages CMS → Publications → Add an entry.\n\n" + "\n".join(new) + "\n",
            encoding="utf-8",
        )
        print(f"{len(new)} publication(s) on ORCID are not on the site; see {REPORT.name}.")
    else:
        REPORT.unlink(missing_ok=True)
        print("No new publications found on ORCID.")


if __name__ == "__main__":
    sys.exit(main())
