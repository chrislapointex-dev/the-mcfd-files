"""BC Legislation Scraper

Downloads key BC child protection statutes from bclaws.gov.bc.ca,
parses them into structured JSON with part/division/section hierarchy.

Statutes fetched:
  - Child, Family and Community Service Act (CFCSA)  → data/raw/legislation/cfcsa.json
  - Representative for Children and Youth Act (RCYA) → data/raw/legislation/rcya.json

Special sections of CFCSA are tagged in the output:
  s29   — Section 29 (less disruptive measures)
  s30   — Section 30 (removal powers)
  s96   — Section 96 (information sharing — ruled unconstitutional)
  part3 — all elements within Part 3 (Child Protection)

Usage:
  cd backend
  .venv/bin/python3.12 -m app.scrapers.legislation
"""

import asyncio
import json
import logging
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = Path("data/raw/legislation")
RATE_DELAY = 2.0

HEADERS = {
    "User-Agent": (
        "MCFD-Files-Research/1.0 (non-commercial; "
        "public interest; contact: research@example.com)"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

STATUTES = [
    {
        "id": "cfcsa",
        "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96046_01",
        # Sections with dedicated tags
        "tagged_sections": {
            "29": ["s29"],
            "30": ["s30"],
            "96": ["s96"],
        },
        # Parts whose elements all receive a tag
        "tagged_parts": {
            "3": ["part3"],
        },
    },
    {
        "id": "rcya",
        "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/06029_01",
        "tagged_sections": {},
        "tagged_parts": {},
    },
]


# ── Parsing helpers ───────────────────────────────────────────────────────────


def _part_number(text: str) -> str:
    """Extract numeric part number from 'Part 3 — Child Protection'."""
    m = re.search(r"Part\s+(\d+)", text, re.IGNORECASE)
    return m.group(1) if m else text.strip()


def _division_number(text: str) -> str:
    """Extract numeric division number from 'Division 2 — ...'."""
    m = re.search(r"Division\s+(\d+)", text, re.IGNORECASE)
    return m.group(1) if m else text.strip()


def _section_number(p) -> str:
    """Extract section number from the <b> tag inside .secnumholder."""
    holder = p.find(class_="secnumholder")
    if holder:
        b = holder.find("b")
        if b:
            return b.get_text(strip=True)
    return ""


def _section_heading(p) -> str:
    """Return heading text with the section-number span removed (uses deepcopy)."""
    p_copy = deepcopy(p)
    secnum = p_copy.find(class_="secnum")
    if secnum:
        secnum.extract()
    return p_copy.get_text(separator=" ", strip=True)


# ── Core parser ───────────────────────────────────────────────────────────────


def parse(html: str, url: str, statute: dict) -> dict:
    """Parse a bclaws.gov.bc.ca statute page into structured elements."""
    # bclaws pages are XHTML — use the XML parser so class attributes are found correctly
    soup = BeautifulSoup(html, features="xml")

    title = ""
    title_el = soup.find("title")
    if title_el:
        title = title_el.get_text(strip=True)

    # Main content lives in #contentsscroll (not #contents which is just a ToC table)
    contents = soup.find(id="contentsscroll") or soup.find("body")
    all_p = contents.find_all("p") if contents else []

    tagged_sections: dict[str, list[str]] = statute.get("tagged_sections", {})
    tagged_parts: dict[str, list[str]] = statute.get("tagged_parts", {})

    elements: list[dict] = []
    current_part: str | None = None
    current_division: str | None = None
    current_section: dict | None = None
    current_lines: list[str] = []

    def flush_section() -> None:
        nonlocal current_section
        if current_section is not None:
            current_section["full_text"] = "\n".join(current_lines).strip()
            elements.append(current_section)
        current_section = None
        current_lines.clear()

    for p in all_p:
        # XML parser returns class as a plain string; split into a set for membership tests
        classes = set((p.get("class") or "").split())
        raw_text = p.get_text(separator=" ", strip=True)
        if not raw_text:
            continue

        if "part" in classes:
            flush_section()
            pnum = _part_number(raw_text)
            current_part = pnum
            current_division = None
            tags = list(tagged_parts.get(pnum, []))
            elements.append({
                "type": "part",
                "number": pnum,
                "heading": raw_text,
                "tags": tags,
            })

        elif "division" in classes:
            flush_section()
            dnum = _division_number(raw_text)
            current_division = dnum
            # Divisions inside tagged parts inherit the part tag
            tags = list(tagged_parts.get(current_part or "", []))
            elements.append({
                "type": "division",
                "number": dnum,
                "heading": raw_text,
                "part": current_part,
                "tags": tags,
            })

        elif "sec" in classes:
            flush_section()
            snum = _section_number(p)
            heading = _section_heading(p)

            # Collect tags: section-specific + inherited part tag
            tags: list[str] = list(tagged_sections.get(snum, []))
            for ptag in tagged_parts.get(current_part or "", []):
                if ptag not in tags:
                    tags.append(ptag)

            current_section = {
                "type": "section",
                "number": snum,
                "heading": heading,
                "full_text": "",
                "part": current_part,
                "division": current_division,
                "tags": tags,
            }
            current_lines = [raw_text]

        else:
            # Subsections, paragraphs, definitions, etc. — append to current section
            if current_section is not None:
                current_lines.append(raw_text)

    flush_section()

    # Summary stats
    n_parts = sum(1 for e in elements if e["type"] == "part")
    n_divs = sum(1 for e in elements if e["type"] == "division")
    n_secs = sum(1 for e in elements if e["type"] == "section")
    n_tagged = sum(1 for e in elements if e.get("tags"))

    return {
        "title": title,
        "url": url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "parts": n_parts,
            "divisions": n_divs,
            "sections": n_secs,
            "tagged_elements": n_tagged,
        },
        "elements": elements,
    }


# ── Fetcher ───────────────────────────────────────────────────────────────────


async def fetch_and_save(statute: dict, client: httpx.AsyncClient) -> None:
    sid = statute["id"]
    url = statute["url"]
    out_path = DATA_DIR / f"{sid}.json"

    log.info("Fetching %s …", sid.upper())
    await asyncio.sleep(RATE_DELAY)

    try:
        resp = await client.get(url)
        resp.raise_for_status()
    except Exception as exc:
        log.error("Failed to fetch %s: %s", sid, exc)
        return

    log.info("  %.0f KB received, parsing …", len(resp.content) / 1024)
    data = parse(resp.text, url, statute)

    stats = data["stats"]
    log.info(
        "  %s: %d parts · %d divisions · %d sections · %d tagged",
        data["title"],
        stats["parts"],
        stats["divisions"],
        stats["sections"],
        stats["tagged_elements"],
    )

    # Log each tagged section specifically
    for el in data["elements"]:
        if el.get("tags") and el["type"] == "section":
            log.info(
                "    [%s] s.%s — %s",
                " · ".join(el["tags"]),
                el["number"],
                el["heading"][:100],
            )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("  ✓ %s", out_path)


# ── Entry point ───────────────────────────────────────────────────────────────


async def main() -> None:
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0),
        headers=HEADERS,
        follow_redirects=True,
    )
    try:
        for statute in STATUTES:
            await fetch_and_save(statute, client)
    finally:
        await client.aclose()
    log.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
