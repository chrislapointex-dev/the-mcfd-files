"""MCFD News Scraper

Fetches news articles about MCFD / child welfare from direct BC news sources:
  - CBC BC (RSS feed, filtered for MCFD/child welfare keywords)
  - BC Gov News (Children and Family Development ministry releases)
  - The Tyee (search results for MCFD/child welfare)
  - Vancouver Sun (search results for MCFD/child welfare)

DuckDuckGo is used as a fallback if a direct source fails or returns nothing.

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
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS

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
FETCH_DELAY = 2.0  # seconds between requests per domain

HEADERS = {
    "User-Agent": "MCFDFiles/1.0 (research)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en;q=0.9",
}

# Keywords for filtering CBC RSS items (lowercase match)
KEYWORDS = frozenset({
    "mcfd", "child welfare", "foster care", "child protection",
    "ministry of children", "representative for children", "cfcsa",
    "child apprehension", "family development", "child in care",
    "children in care", "indigenous children", "child removal",
    "children and family", "youth in care",
})

# DuckDuckGo fallback queries (used when a direct source fails)
DDG_FALLBACK_QUERIES = [
    "MCFD BC child welfare news",
    "BC child protection failure news",
    "Representative Children Youth BC report",
    "MCFD wrongful removal BC",
    "BC foster care death news",
    "MCFD class action BC news",
]

BLOCKED_DOMAINS = {
    "zhidao.baidu.com", "baidu.com", "zhihu.com", "weibo.com",
    "tiktok.com", "youtube.com", "facebook.com", "twitter.com", "reddit.com",
    "merriam-webster.com", "wikipedia.org",
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
        any_failed = False

        # ── Direct source scrapers ──────────────────────────────────────────
        sources = [
            ("CBC BC",        self._scrape_cbc),
            ("BC Gov News",   self._scrape_bc_gov),
            ("The Tyee",      self._scrape_tyee),
            ("Vancouver Sun", self._scrape_vsun),
        ]

        for source_name, scraper_fn in sources:
            try:
                results = await scraper_fn()
                log.info("%s: %d articles found", source_name, len(results))
                if len(results) == 0:
                    any_failed = True
                for r in results:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        all_results.append(r)
            except Exception as exc:
                log.warning("%s scraper failed: %s — will use DDG fallback", source_name, exc)
                any_failed = True

        # ── DuckDuckGo fallback (runs if any source failed or returned nothing) ──
        if any_failed:
            log.info("Running DuckDuckGo fallback queries")
            try:
                ddg_results = await self._ddg_fallback()
                log.info("DuckDuckGo: %d results", len(ddg_results))
                for r in ddg_results:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        all_results.append(r)
            except Exception as exc:
                log.warning("DuckDuckGo fallback also failed: %s", exc)

        log.info("Total unique articles to fetch: %d", len(all_results))

        # ── Fetch full text and save each article ───────────────────────────
        for result in all_results:
            if self.limit is not None and self.saved >= self.limit:
                log.info("Limit of %d reached.", self.limit)
                break
            await self._process(result)

        log.info(
            "Done. saved=%d  skipped=%d  errors=%d  manifest_total=%d",
            self.saved, self.skipped, self.errors, len(self.manifest),
        )
        await self._client.aclose()

    # ── Direct source scrapers ─────────────────────────────────────────────────

    async def _scrape_cbc(self) -> list[dict]:
        """Fetch CBC BC RSS feed and filter for MCFD/child welfare articles."""
        rss_url = "https://www.cbc.ca/cmlink/rss-canada-britishcolumbia"
        await asyncio.sleep(FETCH_DELAY)
        resp = await self._client.get(rss_url)
        resp.raise_for_status()

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as exc:
            log.warning("CBC RSS parse error: %s", exc)
            return []

        results = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            # Fallback: guid element often holds the permalink
            if not link:
                guid = item.find("guid")
                if guid is not None and guid.text:
                    link = guid.text.strip()
            desc = (item.findtext("description") or "").strip()

            if not link or not link.startswith("http"):
                continue

            # Only keep items that mention MCFD/child welfare topics
            combined = (title + " " + desc).lower()
            if not any(kw in combined for kw in KEYWORDS):
                continue

            # Strip HTML from RSS description
            desc_clean = BeautifulSoup(desc, "lxml").get_text(strip=True)[:300]

            results.append({
                "title": title,
                "url": link,
                "snippet": desc_clean,
                "domain": "cbc.ca",
                "query": "cbc_rss_bc",
            })

        return results

    async def _scrape_bc_gov(self) -> list[dict]:
        """Fetch BC Gov News press releases for Children and Family Development."""
        url = (
            "https://news.gov.bc.ca/releases"
            "?ministry=Children+and+Family+Development&pageSize=20"
        )
        await asyncio.sleep(FETCH_DELAY)
        resp = await self._client.get(url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        results = []

        # Try multiple selector patterns — BC Gov may restructure their page
        articles = (
            soup.select("article")
            or soup.select(".release-list li")
            or soup.select(".news-releases li")
            or soup.select(".grid-list li")
            or soup.select("li.item")
        )

        for article in articles:
            a = article.select_one("a[href]")
            if not a:
                continue
            href = a.get("href", "").strip()
            if not href:
                continue
            if not href.startswith("http"):
                href = "https://news.gov.bc.ca" + href
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            snippet_el = article.select_one("p, .summary, .description")
            snippet = snippet_el.get_text(strip=True)[:300] if snippet_el else ""

            results.append({
                "title": title,
                "url": href,
                "snippet": snippet,
                "domain": "news.gov.bc.ca",
                "query": "bc_gov_cfcs",
            })

        return results

    async def _scrape_tyee(self) -> list[dict]:
        """Fetch The Tyee search results for MCFD/child welfare."""
        url = "https://thetyee.ca/search/?q=MCFD+child+welfare+british+columbia"
        await asyncio.sleep(FETCH_DELAY)
        resp = await self._client.get(url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        results = []

        for article in soup.select("article, .search-result, .story, li.item"):
            # Prefer heading anchors; fall back to any link in the block
            a = article.select_one(
                "h2 a[href], h3 a[href], .headline a[href], .title a[href]"
            ) or article.select_one("a[href]")
            if not a:
                continue
            href = a.get("href", "").strip()
            if not href:
                continue
            if not href.startswith("http"):
                href = "https://thetyee.ca" + href
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            snippet_el = article.select_one("p, .summary, .excerpt, .description")
            snippet = snippet_el.get_text(strip=True)[:300] if snippet_el else ""

            results.append({
                "title": title,
                "url": href,
                "snippet": snippet,
                "domain": "thetyee.ca",
                "query": "tyee_search",
            })

        return results

    async def _scrape_vsun(self) -> list[dict]:
        """Fetch Vancouver Sun search results for MCFD/child welfare."""
        url = "https://vancouversun.com/search/?q=MCFD+child+welfare"
        await asyncio.sleep(FETCH_DELAY)
        resp = await self._client.get(url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        results = []

        for article in soup.select("article, .article-card, .search-result, .story-card"):
            a = article.select_one(
                "h2 a[href], h3 a[href], .headline a[href], .title a[href]"
            ) or article.select_one("a[href]")
            if not a:
                continue
            href = a.get("href", "").strip()
            if not href:
                continue
            if not href.startswith("http"):
                href = "https://vancouversun.com" + href
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            snippet_el = article.select_one("p, .summary, .excerpt, .description")
            snippet = snippet_el.get_text(strip=True)[:300] if snippet_el else ""

            results.append({
                "title": title,
                "url": href,
                "snippet": snippet,
                "domain": "vancouversun.com",
                "query": "vsun_search",
            })

        return results

    # ── DuckDuckGo fallback ────────────────────────────────────────────────────

    async def _ddg_fallback(self) -> list[dict]:
        """Run DuckDuckGo searches as fallback when direct sources fail."""
        results = []
        seen: set[str] = set()

        for query in DDG_FALLBACK_QUERIES:
            await asyncio.sleep(3.0)  # DDG needs a longer delay
            try:
                ddgs = DDGS()
                for r in ddgs.text(query, region="ca-en", max_results=8):
                        url = r.get("href", "")
                        if not url or not url.startswith("http") or url in seen:
                            continue
                        domain = urlparse(url).netloc.lstrip("www.")
                        if any(domain == b or domain.endswith("." + b) for b in BLOCKED_DOMAINS):
                            continue
                        seen.add(url)
                        results.append({
                            "title": r.get("title", ""),
                            "url": url,
                            "snippet": (r.get("body") or "")[:300],
                            "domain": urlparse(url).netloc,
                            "query": query,
                        })
            except Exception as exc:
                log.warning("DDG query failed (%s): %s", query, exc)

        return results

    # ── Article processing ─────────────────────────────────────────────────────

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

        for tag in soup(["script", "style", "nav", "header", "footer",
                          "aside", "form", "iframe", "noscript"]):
            tag.decompose()

        for selector in ["article", "main", '[role="main"]',
                          ".article-body", ".story-body", ".post-content",
                          ".entry-content", ".article-content", "#content"]:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    return text

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
        description="Scrape BC news sources for MCFD/child welfare articles"
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
