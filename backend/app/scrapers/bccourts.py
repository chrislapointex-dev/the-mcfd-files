"""BC Courts / Google Scholar MCFD decision scraper — no API key required.

Sources
-------
1. BC Courts (bccourts.ca) — 954+ decisions via POST search form.
   Full case text available on case detail pages (plain HTML, no JS needed).

2. Google Scholar — best-effort fallback.
   Note: as_sdt=2006 (Canadian case law) requires Google login.
   Falls back to as_sdt=6 (North America), filters for BC citations.
   If Google redirects to login → logs a clear message and skips.

Output
------
  data/raw/bccourts/bccourts/{slug}.json
  data/raw/bccourts/google/{slug}.json
  data/raw/bccourts/manifest.json          ← tracks what's saved (resume-safe)

Usage
-----
  python -m app.scrapers.bccourts                   # both sources, fetch full text
  python -m app.scrapers.bccourts --limit 20        # stop after 20 total
  python -m app.scrapers.bccourts --source bccourts # only BC Courts
  python -m app.scrapers.bccourts --no-fulltext     # metadata only (faster)
  python -m app.scrapers.bccourts --reset           # clear manifest, start fresh

Rate limits
-----------
  BC Courts : 2 s between requests (BC_RATE_DELAY env var)
  Google    : 5 s between requests (GS_RATE_DELAY env var)
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
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

KEYWORD = "Ministry of Children and Family Development"
DATA_DIR = Path(os.getenv("BCCOURTS_DATA_DIR", "data/raw/bccourts"))

BC_DELAY = float(os.getenv("BC_RATE_DELAY", "2.0"))
GS_DELAY = float(os.getenv("GS_RATE_DELAY", "5.0"))

BC_BASE = "https://www.bccourts.ca"
BC_SEARCH = f"{BC_BASE}/search_judgments.aspx"
GS_SEARCH = "https://scholar.google.com/scholar"

# Verified against live site: results are 50 per page
BC_PAGE_SIZE = 50

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

_CITATION_RE = re.compile(r"\d{4}\s+BC(?:CA|SC|PC)\s+\d+")
_DATE_RE = re.compile(r"(\d{4})/(\d{2})/(\d{2})")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _next_ua() -> str:
    import random
    return random.choice(USER_AGENTS)


def _slug(title: str, url: str) -> str:
    """Filesystem-safe filename from title, fallback to URL hash."""
    if title:
        s = re.sub(r"[^\w\s-]", "", title.lower())
        s = re.sub(r"\s+", "-", s).strip("-")[:80]
        if s:
            return s
    return hashlib.md5(url.encode()).hexdigest()[:16]


def _is_bot_blocked(resp: httpx.Response) -> bool:
    if resp.status_code in (403, 429, 503):
        return True
    body = resp.text.lower()
    return any(x in body for x in ["captcha", "unusual traffic", "automated", "recaptcha"])


def _parse_court(text: str) -> str:
    if "Court of Appeal" in text or "BCCA" in text.upper():
        return "BC Court of Appeal"
    if "Supreme Court" in text or "BCSC" in text.upper():
        return "BC Supreme Court"
    if "Provincial Court" in text or "BCPC" in text.upper():
        return "BC Provincial Court"
    return ""


def _format_date(raw: str) -> str:
    """Convert 2026/02/26 → 2026-02-26."""
    m = _DATE_RE.search(raw)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else raw


# ── Manifest ──────────────────────────────────────────────────────────────────

class Manifest:
    """Tracks every saved URL. Flush after each page for crash-safe resumability."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._d: dict = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return {
            "last_updated": None,
            "sources": {
                "bccourts": {"saved_urls": [], "blocked": False},
                "google": {"saved_urls": [], "blocked": False},
            },
        }

    def flush(self) -> None:
        self._d["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._d, indent=2))

    def has(self, source: str, url: str) -> bool:
        return url in self._d["sources"][source]["saved_urls"]

    def add(self, source: str, url: str) -> None:
        saved = self._d["sources"][source]["saved_urls"]
        if url not in saved:
            saved.append(url)

    def is_blocked(self, source: str) -> bool:
        return self._d["sources"][source]["blocked"]

    def mark_blocked(self, source: str) -> None:
        self._d["sources"][source]["blocked"] = True
        log.warning(
            "[%s] Marked blocked in manifest. Run with --reset to clear.", source
        )
        self.flush()

    def count(self, source: str) -> int:
        return len(self._d["sources"][source]["saved_urls"])


# ── BC Courts scraper ─────────────────────────────────────────────────────────

class BCCourtsScraper:
    """
    Scrapes bccourts.ca via ASP.NET WebForms POST.

    Flow:
      GET  /search_judgments.aspx          → extract __VIEWSTATE and friends
      POST /search_judgments.aspx          → initial search, page 1 results
      POST /search_judgments.aspx (repeat) → page 2, 3 … via __doPostBack

    Each page yields up to 50 results. Live count: 954 decisions.
    """

    def __init__(
        self,
        manifest: Manifest,
        data_dir: Path,
        limit: int | None,
        fetch_fulltext: bool,
    ) -> None:
        self.manifest = manifest
        self.out_dir = data_dir / "bccourts"
        self.limit = limit
        self.fetch_fulltext = fetch_fulltext
        self.saved = 0
        self._hidden: dict[str, str] = {}

    # ── Public ────────────────────────────────────────────────────────────────

    async def run(self) -> None:
        if self.manifest.is_blocked("bccourts"):
            log.warning("[bccourts] Blocked in manifest. Use --reset to retry.")
            return

        self.out_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"Referer": BC_SEARCH, "User-Agent": _next_ua()},
            follow_redirects=True,
        ) as client:
            self._client = client

            # Step 1: GET page to seed hidden fields
            log.info("[bccourts] Loading search page…")
            resp = await self._get(BC_SEARCH)
            if resp is None:
                return
            self._update_hidden(resp.text)

            # Step 2: POST initial search
            log.info("[bccourts] Submitting search: %s", KEYWORD)
            resp = await self._post_search()
            if resp is None:
                return

            page = 1
            while True:
                if _is_bot_blocked(resp):
                    log.error("[bccourts] Bot-blocked (HTTP %d). Stopping.", resp.status_code)
                    self.manifest.mark_blocked("bccourts")
                    break

                count, total, has_next = await self._process_page(resp.text, page)
                log.info(
                    "[bccourts] Page %d: +%d saved | session total: %d | result count: %s",
                    page, count, self.saved, total or "?",
                )
                self.manifest.flush()

                if self._at_limit() or not has_next:
                    break

                # Update hidden fields from this response before POSTing next page
                self._update_hidden(resp.text)
                page += 1
                resp = await self._post_page(page)
                if resp is None:
                    break

        log.info("[bccourts] Done. %d cases saved.", self.saved)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _at_limit(self) -> bool:
        return self.limit is not None and self.saved >= self.limit

    def _update_hidden(self, html: str) -> None:
        """Extract all hidden input fields from the page."""
        soup = BeautifulSoup(html, "lxml")
        for inp in soup.find_all("input", type="hidden"):
            name = inp.get("name", "")
            if name:
                self._hidden[name] = inp.get("value", "")

    def _search_fields(self) -> dict:
        """Common search field values shared by all POST requests."""
        return {
            "TabContainer$search$txtCitation": "",
            "TabContainer$search$txtCaseName": "",
            "TabContainer$search$chkExact": "on",
            "TabContainer$search$txtFullText": KEYWORD,
            "TabContainer$search$txtFrom": "",
            "TabContainer$search$txtTo": "",
            "TabContainer$search$type": "radBoth",
            "TabContainer$search$txtJudge": "",
            "TabContainer$search$txtDocket": "",
        }

    async def _post_search(self) -> httpx.Response | None:
        data = {
            **self._hidden,
            **self._search_fields(),
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "TabContainer$search$btnSubmit": "Submit",
        }
        return await self._post(BC_SEARCH, data)

    async def _post_page(self, page_num: int) -> httpx.Response | None:
        """Trigger ASP.NET GridView pagination postback."""
        data = {
            **self._hidden,
            **self._search_fields(),
            "__EVENTTARGET": "gvResults",
            "__EVENTARGUMENT": f"Page${page_num}",
        }
        return await self._post(BC_SEARCH, data)

    async def _process_page(
        self, html: str, page_num: int
    ) -> tuple[int, int | None, bool]:
        """Parse one result page. Returns (saved_count, total_results, has_next_page)."""
        soup = BeautifulSoup(html, "lxml")

        # Total result count
        total: int | None = None
        for s in soup.stripped_strings:
            m = re.search(r"Number found:\s*([\d,]+)", s)
            if m:
                total = int(m.group(1).replace(",", ""))
                break

        grid = soup.find(id="gvResults")
        if not grid:
            log.warning("[bccourts] gvResults not found on page %d", page_num)
            return 0, total, False

        # Parse result rows
        results: list[dict] = []
        for row in grid.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            links = cells[0].find_all("a")
            if not links:
                continue
            href = links[0].get("href", "")
            if not href or href.startswith("javascript:"):
                continue

            cell_text = cells[0].get_text(" ", strip=True)
            title = links[0].get_text(strip=True)
            url = href if href.startswith("http") else f"{BC_BASE}{href}"
            citation_m = _CITATION_RE.search(cell_text)
            date_m = _DATE_RE.search(cell_text)

            results.append({
                "source": "bccourts",
                "title": title,
                "citation": citation_m.group(0) if citation_m else "",
                "date": _format_date(date_m.group(0)) if date_m else "",
                "court": _parse_court(cell_text),
                "url": url,
                "snippet": "",
                "full_text": "",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

        # Has next page: look for page link beyond current
        has_next = False
        for a in grid.find_all("a"):
            href = a.get("href", "")
            if f"Page${page_num + 1}" in href:
                has_next = True
                break

        # Save results (async full-text fetch per result)
        saved = 0
        for record in results:
            if self._at_limit():
                break
            if self.manifest.has("bccourts", record["url"]):
                continue
            if self.fetch_fulltext:
                await self._add_fulltext(record)
            self._write(record, "bccourts")
            saved += 1
            self.saved += 1

        return saved, total, has_next

    async def _add_fulltext(self, record: dict) -> None:
        resp = await self._get(record["url"])
        if not resp:
            return
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style"]):
            tag.decompose()
        record["full_text"] = soup.get_text("\n", strip=True)[:150_000]

    def _write(self, record: dict, source: str) -> None:
        slug = _slug(record.get("title", "") or record.get("citation", ""), record["url"])
        out = self.out_dir / f"{slug}.json"
        n = 1
        while out.exists():
            out = self.out_dir / f"{slug}-{n}.json"
            n += 1
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        self.manifest.add(source, record["url"])
        log.info(
            "[bccourts] ✓ %s",
            record.get("citation") or record.get("title", "?")[:50],
        )

    async def _get(self, url: str) -> httpx.Response | None:
        await asyncio.sleep(BC_DELAY)
        try:
            self._client.headers["User-Agent"] = _next_ua()
            resp = await self._client.get(url)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            log.warning("[bccourts] GET failed %s — %s", url, exc)
            return None

    async def _post(self, url: str, data: dict) -> httpx.Response | None:
        await asyncio.sleep(BC_DELAY)
        try:
            self._client.headers["User-Agent"] = _next_ua()
            resp = await self._client.post(url, data=data)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            log.warning("[bccourts] POST failed %s — %s", url, exc)
            return None


# ── Google Scholar scraper ────────────────────────────────────────────────────

class GoogleScholarScraper:
    """
    Searches Google Scholar for BC MCFD cases.

    Uses as_sdt=6 (North America) since as_sdt=2006 (Canadian case law)
    requires a Google login. Filters results to BC citations only.

    If Google redirects to accounts.google.com → logs instructions and stops.
    """

    def __init__(
        self,
        manifest: Manifest,
        data_dir: Path,
        limit: int | None,
    ) -> None:
        self.manifest = manifest
        self.out_dir = data_dir / "google"
        self.limit = limit
        self.saved = 0

    async def run(self) -> None:
        if self.manifest.is_blocked("google"):
            log.warning("[google] Blocked in manifest. Use --reset to retry.")
            return

        self.out_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=False,  # detect login redirects explicitly
        ) as client:
            start = 0
            consecutive_empty = 0

            while not self._at_limit():
                await asyncio.sleep(GS_DELAY)

                params = {
                    "as_sdt": "6",
                    "q": f'"{KEYWORD}" BC court',
                    "hl": "en",
                    "start": start,
                }
                try:
                    resp = await client.get(
                        GS_SEARCH,
                        params=params,
                        headers={
                            "User-Agent": _next_ua(),
                            "Accept": "text/html,application/xhtml+xml",
                            "Accept-Language": "en-US,en;q=0.9",
                        },
                    )
                except Exception as exc:
                    log.warning("[google] Request error at start=%d: %s", start, exc)
                    break

                # Login redirect
                if resp.status_code in (301, 302, 303, 307, 308):
                    loc = resp.headers.get("location", "")
                    if "accounts.google.com" in loc or "signin" in loc.lower():
                        log.warning(
                            "[google] Google Scholar requires login for case law search."
                        )
                        log.warning(
                            "[google] To use: log in to Google in Chrome, export cookies,"
                            " then set GOOGLE_SCHOLAR_COOKIES env var."
                        )
                        self.manifest.mark_blocked("google")
                        break

                if _is_bot_blocked(resp):
                    log.warning(
                        "[google] Bot-blocked at start=%d (HTTP %d). Stopping.",
                        start, resp.status_code,
                    )
                    self.manifest.mark_blocked("google")
                    break

                count = self._parse_and_save(resp.text)
                log.info(
                    "[google] start=%d: +%d saved | session total: %d",
                    start, count, self.saved,
                )
                self.manifest.flush()

                if count == 0:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        log.info("[google] No more results.")
                        break
                else:
                    consecutive_empty = 0

                start += 10

        log.info("[google] Done. %d cases saved.", self.saved)

    def _at_limit(self) -> bool:
        return self.limit is not None and self.saved >= self.limit

    def _parse_and_save(self, html: str) -> int:
        soup = BeautifulSoup(html, "lxml")
        saved = 0

        for div in soup.find_all("div", class_=re.compile(r"\bgs_r\b")):
            if self._at_limit():
                break

            h3 = div.find("h3", class_="gs_rt")
            if not h3:
                continue
            a = h3.find("a")
            if not a:
                continue

            title = a.get_text(strip=True)
            url = a.get("href", "")
            if not url:
                continue

            gs_a = div.find("div", class_="gs_a")
            cite_line = gs_a.get_text(" ", strip=True) if gs_a else ""
            gs_rs = div.find("div", class_="gs_rs")
            snippet = gs_rs.get_text(" ", strip=True) if gs_rs else ""

            # Only keep BC court cases
            combined = (title + " " + cite_line).upper()
            if not any(
                x in combined
                for x in ["BC", "BRITISH COLUMBIA", "BCSC", "BCCA", "BCPC"]
            ):
                continue

            if self.manifest.has("google", url):
                continue

            citation_m = _CITATION_RE.search(title + " " + cite_line)
            year_m = _YEAR_RE.search(cite_line)

            record = {
                "source": "google_scholar",
                "title": title,
                "citation": citation_m.group(0) if citation_m else "",
                "date": year_m.group(0) if year_m else "",
                "court": _parse_court(cite_line),
                "url": url,
                "snippet": snippet,
                "full_text": "",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }

            slug = _slug(
                record["title"] or record["citation"],
                url,
            )
            out = self.out_dir / f"{slug}.json"
            n = 1
            while out.exists():
                out = self.out_dir / f"{slug}-{n}.json"
                n += 1
            out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            self.manifest.add("google", url)
            self.saved += 1
            saved += 1
            log.info("[google] ✓ %s", record["citation"] or title[:50])

        return saved


# ── Entry point ───────────────────────────────────────────────────────────────

async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape MCFD BC court decisions — no API key required"
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Stop after saving N cases total per source",
    )
    parser.add_argument(
        "--source", choices=["bccourts", "google", "both"], default="both",
        help="Which source to scrape (default: both)",
    )
    parser.add_argument(
        "--no-fulltext", action="store_true",
        help="Skip fetching full case text from BC Courts (faster, metadata only)",
    )
    parser.add_argument(
        "--data-dir", default=str(DATA_DIR),
        help=f"Output root directory (default: {DATA_DIR})",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Clear manifest and start from scratch",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    manifest_path = data_dir / "manifest.json"

    if args.reset and manifest_path.exists():
        manifest_path.unlink()
        log.info("Manifest cleared.")

    manifest = Manifest(manifest_path)
    sources = (
        ["bccourts", "google"] if args.source == "both" else [args.source]
    )

    for source in sources:
        if source == "bccourts":
            await BCCourtsScraper(
                manifest=manifest,
                data_dir=data_dir,
                limit=args.limit,
                fetch_fulltext=not args.no_fulltext,
            ).run()
        else:
            await GoogleScholarScraper(
                manifest=manifest,
                data_dir=data_dir,
                limit=args.limit,
            ).run()


if __name__ == "__main__":
    asyncio.run(_main())
