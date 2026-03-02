"""MCFD News Scraper

Searches DuckDuckGo HTML for news articles about MCFD failures, then fetches
full article text via httpx + BeautifulSoup4.

Saves each article as JSON to data/raw/news/.
Manifest at data/raw/news/manifest.json tracks completed downloads.

Usage:
  python -m app.scrapers.news              # full run
  python -m app.scrapers.news --limit 5   # test with first 5 articles
  python -m app.scrapers.news --reset     # clear manifest and re-fetch
"""

import argparse
import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = Path("data/raw/news")
MANIFEST_FILE = DATA_DIR / "manifest.json"
SEARCH_DELAY = 3.0   # seconds between searches
FETCH_DELAY = 2.0    # seconds between article fetches

QUERIES = [
    "MCFD wrongful removal BC",
    "Ministry Children Family Development lawsuit",
    "BC child protection failure",
    "Representative Children Youth BC report",
    "MCFD class action BC",
    "MCFD foster care death BC",
    "MCFD social worker misconduct BC",
    "MCFD BC investigation",
    "foster care BC death",
    "child welfare BC reform",
    "Murphy Battista MCFD class action",
    "T.L. v BC Court of Appeal CFCSA",
    "Representative Children Youth BC",
    # Broader BC coverage
    "BC child welfare Indigenous family removal",
    "CFCSA British Columbia child protection",
    "BC foster care abuse neglect",
    "child apprehension British Columbia wrongful",
    "MCFD accountability transparency BC",
    "BC child welfare death review",
    "representative children youth BC investigation",
    "MCFD social worker negligence British Columbia",
    "child protection BC Supreme Court",
    "BC child welfare class action lawsuit",
    "foster care BC Indigenous children",
    "MCFD wrongful apprehension settlement BC",
    "BC family court child custody MCFD",
    "CFCSA amendment reform British Columbia",
    "child welfare British Columbia news",
    "BC MCFD complaint ombudsman",
]

DDG_URL = "https://html.duckduckgo.com/html/"

BLOCKED_DOMAINS = {
    # Chinese sites (match "BC" as Chinese abbreviation)
    "zhidao.baidu.com", "baidu.com", "zhihu.com", "weibo.com",
    # Social / video (not news)
    "tiktok.com", "youtube.com", "facebook.com", "twitter.com", "reddit.com",
    # Dictionary / generic reference
    "merriam-webster.com", "wikipedia.org",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en;q=0.9",
}

# ── Manifest ──────────────────────────────────────────────────────────────────


class Manifest:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: dict = {}
        if path.exists():
            try:
                self._data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def has(self, url: str) -> bool:
        return url in self._data

    def add(self, url: str, filename: str) -> None:
        self._data[url] = {
            "filename": filename,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        self._flush()

    def _flush(self) -> None:
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def reset(self) -> None:
        self._data = {}
        self._flush()

    def __len__(self) -> int:
        return len(self._data)


# ── Scraper ───────────────────────────────────────────────────────────────────


class NewsScraper:
    def __init__(self, data_dir: Path, limit: int | None = None) -> None:
        self.data_dir = data_dir
        self.limit = limit
        self.manifest = Manifest(MANIFEST_FILE)
        self.saved = 0
        self.skipped = 0
        self.errors = 0

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers=HEADERS,
            follow_redirects=True,
        )

    async def run(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

        all_results: list[dict] = []
        seen_urls: set[str] = set()

        for query in QUERIES:
            if self.limit is not None and self.saved >= self.limit:
                break
            log.info("Searching: %s", query)
            results = await self._search(query)
            log.info("  → %d results", len(results))
            for r in results:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)

        log.info("Total unique search results: %d", len(all_results))

        for result in all_results:
            if self.limit is not None and self.saved >= self.limit:
                log.info("Limit of %d reached.", self.limit)
                break
            await self._process(result)

        log.info(
            "Done. saved=%d  skipped=%d  errors=%d",
            self.saved,
            self.skipped,
            self.errors,
        )
        await self._client.aclose()

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _search(self, query: str) -> list[dict]:
        await asyncio.sleep(SEARCH_DELAY)
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, region="ca-en", max_results=10):
                    url = r.get("href", "")
                    if not url or not url.startswith("http"):
                        continue
                    domain = urlparse(url).netloc.lstrip("www.")
                    if any(domain == b or domain.endswith("." + b) for b in BLOCKED_DOMAINS):
                        continue
                    results.append({
                        "title": r.get("title", ""),
                        "url": url,
                        "snippet": r.get("body", ""),
                        "domain": urlparse(url).netloc,
                        "query": query,
                    })
            return results
        except Exception as exc:
            log.warning("Search failed for %s: %s", query, exc)
            return []

    def _parse_ddg(self, html: str, query: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        results = []

        for result in soup.select(".result"):
            title_el = result.select_one(".result__title a")
            snippet_el = result.select_one(".result__snippet")

            if not title_el:
                continue

            url = title_el.get("href", "")
            # DDG wraps URLs in redirects — extract the real URL
            url = self._extract_real_url(url)
            if not url or not url.startswith("http"):
                continue

            title = title_el.get_text(strip=True)
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            domain = urlparse(url).netloc

            results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "domain": domain,
                "query": query,
            })

        return results

    def _extract_real_url(self, href: str) -> str:
        """DDG sometimes wraps URLs in /l/?uddg=... — extract the real one."""
        if href.startswith("//duckduckgo.com/l/") or "uddg=" in href:
            match = re.search(r"uddg=([^&]+)", href)
            if match:
                from urllib.parse import unquote
                return unquote(match.group(1))
        if href.startswith("//"):
            return "https:" + href
        return href

    async def _process(self, result: dict) -> None:
        url = result["url"]
        if self.manifest.has(url):
            self.skipped += 1
            log.debug("Already saved: %s", url)
            return

        log.info("Fetching: %s", url)
        await asyncio.sleep(FETCH_DELAY)

        full_text = await self._fetch_article(url)
        if full_text is None:
            self.errors += 1
            return

        record = {
            "title": result["title"],
            "url": url,
            "domain": result["domain"],
            "snippet": result["snippet"],
            "query": result["query"],
            "full_text": full_text,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

        filename = self._safe_filename(url)
        filepath = self.data_dir / filename
        filepath.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

        self.manifest.add(url, filename)
        self.saved += 1
        log.info(
            "  ✓ %s  (%d chars)  [%d saved]",
            result["domain"],
            len(full_text),
            self.saved,
        )

    async def _fetch_article(self, url: str) -> str | None:
        """Fetch article and extract main text via BeautifulSoup."""
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            log.warning("HTTP %d: %s — skipping", exc.response.status_code, url)
            return None
        except Exception as exc:
            log.warning("Fetch error %s: %s — skipping", url, exc)
            return None

        return self._extract_text(resp.text, url)

    def _extract_text(self, html: str, url: str) -> str:
        """Extract readable text from article HTML."""
        soup = BeautifulSoup(html, "lxml")

        # Remove boilerplate
        for tag in soup(["script", "style", "nav", "header", "footer",
                          "aside", "form", "iframe", "noscript"]):
            tag.decompose()

        # Try common article containers first
        for selector in ["article", "main", '[role="main"]',
                          ".article-body", ".story-body", ".post-content",
                          ".entry-content", ".article-content", "#content"]:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    return text

        # Fall back to body
        body = soup.find("body")
        if body:
            return body.get_text(separator="\n", strip=True)

        return soup.get_text(separator="\n", strip=True)

    @staticmethod
    def _safe_filename(url: str) -> str:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "").replace(".", "_")
        path = re.sub(r"[^\w\-]", "_", parsed.path.strip("/"))[:60]
        slug = f"{domain}__{path}" if path else domain
        slug = re.sub(r"_+", "_", slug).strip("_")
        return f"{slug}.json"


# ── CLI ───────────────────────────────────────────────────────────────────────


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Search and save news articles about MCFD failures"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Stop after saving N articles (useful for testing)",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DATA_DIR),
        help=f"Output directory (default: {DATA_DIR})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear manifest and re-fetch everything",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    scraper = NewsScraper(data_dir=data_dir, limit=args.limit)

    if args.reset:
        log.info("Resetting manifest.")
        scraper.manifest.reset()

    await scraper.run()


if __name__ == "__main__":
    asyncio.run(_main())
