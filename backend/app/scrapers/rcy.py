"""RCY BC Report PDF Downloader

Downloads all PDF reports from the Representative for Children and Youth (BC)
via the WordPress REST API at rcybc.ca.

Source pages:
  https://rcybc.ca/reports-and-publications/
  https://rcybc.ca/reports-and-publications/reports/

Strategy:
  The site uses WordPress with a custom 'reports' post type. All 74 reports
  are available via the WP REST API in a single request. PDF links are embedded
  in each report's content HTML.

  1. GET /wp-json/wp/v2/reports?per_page=100 → all reports (title, date, content)
  2. Parse PDF URLs from content HTML via regex
  3. Download each PDF to data/raw/rcy/
  4. Save companion .meta.json per PDF (title, url, date, file_size_bytes, filename)
  5. Manifest at data/raw/rcy/manifest.json tracks completed downloads

Usage:
  python -m app.scrapers.rcy              # Download all
  python -m app.scrapers.rcy --limit 3   # Test with first 3 PDFs
  python -m app.scrapers.rcy --reset     # Clear manifest and re-download

Rate limit: 2 s between every HTTP request.
"""

import argparse
import asyncio
import html
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

API_URL = "https://rcybc.ca/wp-json/wp/v2/reports"
DATA_DIR = Path("data/raw/rcy")
MANIFEST_FILE = DATA_DIR / "manifest.json"
RATE_DELAY = 2.0  # seconds between requests

PDF_RE = re.compile(r'https?://[^\s"\'<>]+\.pdf', re.IGNORECASE)


# ── Manifest ──────────────────────────────────────────────────────────────────


class Manifest:
    """Tracks downloaded PDF URLs across runs."""

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
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
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


class RCYScraper:
    def __init__(self, data_dir: Path, limit: int | None = None) -> None:
        self.data_dir = data_dir
        self.limit = limit
        self.manifest = Manifest(MANIFEST_FILE)
        self.downloaded = 0
        self.skipped = 0
        self.errors = 0

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={
                "User-Agent": (
                    "MCFD-Files-Research/1.0 (non-commercial; "
                    "public interest; contact: research@example.com)"
                )
            },
            follow_redirects=True,
        )

    async def run(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

        log.info("Fetching report list from WP REST API…")
        reports = await self._fetch_reports()
        if not reports:
            log.error("No reports returned from API.")
            await self._client.aclose()
            return

        log.info("Found %d reports. Extracting PDF links…", len(reports))

        # Build flat list of (pdf_url, report_meta)
        tasks: list[tuple[str, dict]] = []
        for report in reports:
            title = html.unescape(report["title"]["rendered"])
            date = report["date"][:10]
            link = report["link"]
            content = report["content"]["rendered"]
            pdf_urls = list(dict.fromkeys(PDF_RE.findall(content)))  # dedupe, preserve order
            for url in pdf_urls:
                tasks.append((url, {"title": title, "date": date, "report_url": link}))

        log.info("Found %d PDF links across all reports.", len(tasks))

        for pdf_url, meta in tasks:
            if self.limit is not None and self.downloaded >= self.limit:
                log.info("Limit of %d reached.", self.limit)
                break
            await self._process_pdf(pdf_url, meta)

        log.info(
            "Done. downloaded=%d  skipped=%d  errors=%d",
            self.downloaded,
            self.skipped,
            self.errors,
        )
        await self._client.aclose()

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _fetch_reports(self) -> list[dict]:
        await asyncio.sleep(RATE_DELAY)
        try:
            resp = await self._client.get(
                API_URL,
                params={
                    "per_page": 100,
                    "_fields": "id,title,date,link,content",
                },
            )
            resp.raise_for_status()
            total = resp.headers.get("X-WP-Total", "?")
            log.info("API returned %s total reports.", total)
            return resp.json()
        except Exception as exc:
            log.error("Failed to fetch report list: %s", exc)
            return []

    async def _process_pdf(self, pdf_url: str, meta: dict) -> None:
        if self.manifest.has(pdf_url):
            self.skipped += 1
            log.debug("Already downloaded: %s", pdf_url)
            return

        filename = self._safe_filename(pdf_url)
        pdf_path = self.data_dir / filename
        meta_path = self.data_dir / (filename + ".meta.json")

        # Avoid overwriting a different file with the same base name
        if pdf_path.exists() and not self.manifest.has(pdf_url):
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            filename = f"{stem}_{len(list(self.data_dir.glob(stem + '*')))}{suffix}"
            pdf_path = self.data_dir / filename
            meta_path = self.data_dir / (filename + ".meta.json")

        log.info("Downloading: %s → %s", pdf_url, filename)
        await asyncio.sleep(RATE_DELAY)

        file_size = await self._download_pdf(pdf_url, pdf_path)
        if file_size is None:
            self.errors += 1
            return

        record = {
            "title": meta["title"],
            "url": pdf_url,
            "report_url": meta["report_url"],
            "date": meta["date"],
            "filename": filename,
            "file_size_bytes": file_size,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
        meta_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        self.manifest.add(pdf_url, filename)
        self.downloaded += 1
        log.info(
            "  ✓ %s  (%.1f KB)  [%d downloaded]",
            filename,
            file_size / 1024,
            self.downloaded,
        )

    async def _download_pdf(self, url: str, dest: Path) -> int | None:
        """Stream-download a PDF. Returns file size in bytes, or None on error."""
        try:
            async with self._client.stream("GET", url) as resp:
                resp.raise_for_status()
                size = 0
                with dest.open("wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        size += len(chunk)
            return size
        except httpx.HTTPStatusError as exc:
            log.warning("HTTP %d: %s", exc.response.status_code, url)
            if dest.exists():
                dest.unlink()
            return None
        except Exception as exc:
            log.warning("Download error %s: %s", url, exc)
            if dest.exists():
                dest.unlink()
            return None

    @staticmethod
    def _safe_filename(url: str) -> str:
        """Extract the PDF filename from its URL."""
        path = urlparse(url).path
        name = Path(path).name
        # Sanitize: keep only safe characters
        name = re.sub(r'[^\w\-.]', '_', name)
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        return name


# ── CLI ───────────────────────────────────────────────────────────────────────


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Download all PDF reports from rcybc.ca"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Stop after downloading N PDFs (useful for testing)",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DATA_DIR),
        help=f"Output directory (default: {DATA_DIR})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear manifest and re-download everything",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    scraper = RCYScraper(data_dir=data_dir, limit=args.limit)

    if args.reset:
        log.info("Resetting manifest.")
        scraper.manifest.reset()

    await scraper.run()


if __name__ == "__main__":
    asyncio.run(_main())
