"""CanLII scraper — BC court decisions mentioning MCFD.

Searches BC Court of Appeal, BC Supreme Court, and BC Provincial Court
for all decisions referencing 'Ministry of Children and Family Development'.

For each decision saves:
  citation, date, court, judge, full_text, url → data/raw/canlii/{db}/{caseId}.json

Usage
-----
  # Full run:
  python -m app.scrapers.canlii

  # Test with first 20 results:
  python -m app.scrapers.canlii --limit 20

  # One database only:
  python -m app.scrapers.canlii --db bcsc

Requirements
------------
  CANLII_API_KEY env var.
  Free key at: https://api.canlii.org/

Rate limiting
-------------
  RATE_DELAY (default 1.5 s) between every HTTP request.
  Doubles to 30 s on HTTP 429, then resumes.
"""

import argparse
import asyncio
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

API_BASE = "https://api.canlii.org/v1"
WEB_BASE = "https://www.canlii.org"
KEYWORD = "Ministry of Children and Family Development"
PAGE_SIZE = 100  # CanLII API max per request

BC_DATABASES: dict[str, str] = {
    "bcca": "BC Court of Appeal",
    "bcsc": "BC Supreme Court",
    "bcpc": "BC Provincial Court",
}

RATE_DELAY: float = float(os.getenv("CANLII_RATE_DELAY", "1.5"))
DATA_DIR = Path(os.getenv("CANLII_DATA_DIR", "data/raw/canlii"))

# Patterns tried in order; match group 1 is the judge name/string
_JUDGE_RE: list[re.Pattern] = [
    # "Before: The Honourable Madam Justice Smith"
    re.compile(
        r"(?:Before|BEFORE)[:\s]+"
        r"(?:The Honourable[ \t]+)?"
        r"((?:Madam |Mr\. |Associate Chief |Chief |Deputy Chief )?Justice [A-Z][A-Za-z\-']+(?:[ \t]+[A-Z][A-Za-z\-']+)*)",
        re.MULTILINE,
    ),
    # "Before: Judge Doe"
    re.compile(
        r"(?:Before|BEFORE)[:\s]+(Judge [A-Z][A-Za-z\-']+(?:[ \t]+[A-Z][A-Za-z\-']+)*)",
        re.MULTILINE,
    ),
    # Bare title anywhere near the top
    re.compile(
        r"((?:Madam |Mr\. |Associate Chief |Chief |Deputy Chief )?Justice [A-Z][A-Za-z\-']+(?:[ \t]+[A-Z][A-Za-z\-']+)*)"
    ),
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract_judge(text: str) -> str:
    """Best-effort extraction of judge name from the first 4 000 chars."""
    snippet = text[:4000]
    for pat in _JUDGE_RE:
        m = pat.search(snippet)
        if m:
            return m.group(1).strip()
    return ""


def _parse_decision_html(html: str) -> tuple[str, str]:
    """Return (full_text, judge) from a CanLII case page."""
    soup = BeautifulSoup(html, "lxml")

    # Drop chrome
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # CanLII wraps decision body in #documentContent or .documentContent
    body = (
        soup.find(id="documentContent")
        or soup.find(class_="documentContent")
        or soup.find(id="mainContent")
        or soup.find(class_="content")
        or soup.body
    )
    text = body.get_text("\n", strip=True) if body else soup.get_text("\n", strip=True)
    judge = _extract_judge(text)
    return text, judge


# ── Scraper class ─────────────────────────────────────────────────────────────


class CanLIIScraper:
    def __init__(
        self,
        api_key: str,
        data_dir: Path = DATA_DIR,
        databases: list[str] | None = None,
        limit: int | None = None,
    ) -> None:
        self.api_key = api_key
        self.data_dir = data_dir
        self.databases = databases or list(BC_DATABASES.keys())
        self.limit = limit
        self.saved = 0
        self.skipped = 0
        self.errors = 0

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "User-Agent": "MCFD-Files-Legal-Research/1.0 (non-commercial; contact: research@example.com)"
            },
            follow_redirects=True,
        )

    # ── Public ────────────────────────────────────────────────────────────────

    async def run(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

        for db_id in self.databases:
            if self._hit_limit():
                break
            court = BC_DATABASES.get(db_id, db_id)
            log.info("=== %s (%s) ===", court, db_id)
            await self._scrape_database(db_id)

        log.info(
            "Finished. saved=%d  skipped=%d  errors=%d",
            self.saved,
            self.skipped,
            self.errors,
        )
        await self._client.aclose()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _hit_limit(self) -> bool:
        return self.limit is not None and self.saved >= self.limit

    async def _scrape_database(self, db_id: str) -> None:
        offset = 0
        while not self._hit_limit():
            data = await self._api_search(db_id, offset)
            cases = data.get("cases", [])
            if not cases:
                break

            total = data.get("resultCount", "?")
            log.info("[%s] page offset=%d  page_size=%d  total=%s", db_id, offset, len(cases), total)

            for case_stub in cases:
                if self._hit_limit():
                    break
                await self._process_case(db_id, case_stub)

            if len(cases) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

    async def _process_case(self, db_id: str, stub: dict) -> None:
        case_id = stub.get("caseId", "")
        if not case_id:
            return

        out_path = self.data_dir / db_id / f"{case_id}.json"
        if out_path.exists():
            self.skipped += 1
            log.debug("[%s] already have %s", db_id, case_id)
            return

        # Full metadata from API
        meta = await self._api_case_meta(db_id, case_id)
        if not meta:
            self.errors += 1
            return

        # HTML for full text + judge
        case_url = f"{WEB_BASE}/en/{db_id}/{case_id}/"
        html = await self._fetch_html(case_url)
        full_text, judge = ("", "")
        if html:
            full_text, judge = _parse_decision_html(html)

        record = {
            "citation": meta.get("citation", ""),
            "title": meta.get("title", ""),
            "date": meta.get("decisionDate", ""),
            "court": BC_DATABASES.get(db_id, db_id),
            "database_id": db_id,
            "case_id": case_id,
            "judge": judge,
            "url": case_url,
            "full_text": full_text,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        self.saved += 1
        log.info("[%s] ✓ %s  judge=%s  (%d saved)", db_id, meta.get("citation", case_id), judge or "unknown", self.saved)

    # ── API calls ─────────────────────────────────────────────────────────────

    async def _api_search(self, db_id: str, offset: int) -> dict:
        url = f"{API_BASE}/caseSearch/en/{db_id}/"
        params = {
            "keyword": KEYWORD,
            "offset": offset,
            "resultCount": PAGE_SIZE,
            "api_key": self.api_key,
        }
        resp = await self._get(url, params=params)
        return resp.json() if resp else {}

    async def _api_case_meta(self, db_id: str, case_id: str) -> dict:
        url = f"{API_BASE}/cases/en/{db_id}/{case_id}/"
        resp = await self._get(url, params={"api_key": self.api_key})
        return resp.json() if resp else {}

    async def _fetch_html(self, url: str) -> str | None:
        resp = await self._get(url)
        return resp.text if resp else None

    # ── HTTP with rate limiting ───────────────────────────────────────────────

    async def _get(
        self,
        url: str,
        params: dict | None = None,
        _retry: int = 0,
    ) -> httpx.Response | None:
        await asyncio.sleep(RATE_DELAY)
        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429 and _retry < 3:
                wait = 30 * (2 ** _retry)
                log.warning("Rate-limited (429). Waiting %ds before retry %d…", wait, _retry + 1)
                await asyncio.sleep(wait)
                return await self._get(url, params=params, _retry=_retry + 1)
            log.warning("HTTP %d: %s", status, url)
            self.errors += 1
            return None
        except httpx.RequestError as exc:
            log.warning("Request error: %s — %s", url, exc)
            self.errors += 1
            return None


# ── CLI entry point ───────────────────────────────────────────────────────────


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape CanLII BC decisions mentioning MCFD"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Stop after saving N cases (useful for testing)",
    )
    parser.add_argument(
        "--db",
        choices=list(BC_DATABASES.keys()),
        default=None,
        metavar="DB",
        help="Only scrape one database (bcca | bcsc | bcpc)",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DATA_DIR),
        help=f"Output directory (default: {DATA_DIR})",
    )
    args = parser.parse_args()

    api_key = os.getenv("CANLII_API_KEY", "").strip()
    if not api_key:
        print("Error: CANLII_API_KEY environment variable is not set.", file=sys.stderr)
        print("Get a free API key at: https://api.canlii.org/", file=sys.stderr)
        print("Then run:  export CANLII_API_KEY=your_key_here", file=sys.stderr)
        sys.exit(1)

    scraper = CanLIIScraper(
        api_key=api_key,
        data_dir=Path(args.data_dir),
        databases=[args.db] if args.db else None,
        limit=args.limit,
    )
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(_main())
