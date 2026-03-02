"""MCFD Files — Full Scrape Pipeline

Runs all available scrapers in sequence. Each scraper is launched as a
subprocess so a crash in one never aborts the others.

Scrapers:
  1. bccourts   — BC Courts + Google Scholar decisions
  2. rcy        — RCY PDF reports
  3. news       — DuckDuckGo news articles
  4. legislation — BC Laws statutes
  5. canlii     — CanLII BC decisions (requires CANLII_API_KEY env var)

Usage:
  cd backend
  .venv/bin/python3.12 -m app.scrapers.run_all              # full run
  .venv/bin/python3.12 -m app.scrapers.run_all --limit 5   # test run
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Scraper registry ──────────────────────────────────────────────────────────
#
# count_dirs / count_glob: used to measure new documents after each run.
# supports_limit:          whether to forward --limit N to this scraper.
# requires_env:            if set, skip the scraper when this env var is absent.

SCRAPERS = [
    {
        "id": "bccourts",
        "module": "app.scrapers.bccourts",
        "supports_limit": True,
        "count_dirs": ["data/raw/bccourts/bccourts", "data/raw/bccourts/google"],
        "count_glob": "*.json",
    },
    {
        "id": "rcy",
        "module": "app.scrapers.rcy",
        "supports_limit": True,
        "count_dirs": ["data/raw/rcy"],
        "count_glob": "*.meta.json",
    },
    {
        "id": "news",
        "module": "app.scrapers.news",
        "supports_limit": True,
        "count_dirs": ["data/raw/news"],
        "count_glob": "*.json",
        "count_exclude": {"manifest.json"},
    },
    {
        "id": "legislation",
        "module": "app.scrapers.legislation",
        "supports_limit": False,          # fetches a fixed set of statutes
        "count_dirs": ["data/raw/legislation"],
        "count_glob": "*.json",
    },
    {
        "id": "canlii",
        "module": "app.scrapers.canlii",
        "supports_limit": True,
        "requires_env": "CANLII_API_KEY",
        "count_dirs": ["data/raw/canlii"],
        "count_glob": "**/*.json",
        "count_exclude": {"manifest.json"},
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────


def _count(scraper: dict) -> int:
    """Count output files for a scraper."""
    exclude = scraper.get("count_exclude", set())
    total = 0
    for d in scraper["count_dirs"]:
        path = Path(d)
        if path.exists():
            total += sum(
                1 for f in path.glob(scraper["count_glob"])
                if f.name not in exclude
            )
    return total


# ── Runner ────────────────────────────────────────────────────────────────────


async def _run_one(scraper: dict, limit: int | None) -> dict:
    """
    Launch one scraper subprocess.
    Returns a result dict with status, doc counts, and elapsed time.
    """
    sid = scraper["id"]

    # Skip if a required env var is absent
    if "requires_env" in scraper:
        env_key = scraper["requires_env"]
        if not os.environ.get(env_key):
            log.info("⏭  %-12s  SKIPPED — %s is not set", sid, env_key)
            return {"id": sid, "status": "skipped", "reason": f"{env_key} not set",
                    "before": 0, "after": 0, "elapsed": 0.0}

    cmd = [sys.executable, "-m", scraper["module"]]
    if limit is not None and scraper["supports_limit"]:
        cmd += ["--limit", str(limit)]

    before = _count(scraper)

    log.info("")
    log.info("━" * 60)
    log.info("▶  %s", sid.upper())
    log.info("━" * 60)

    t0 = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
        elapsed = time.monotonic() - t0
        after = _count(scraper)
        status = "ok" if proc.returncode == 0 else "error"
        if status == "error":
            log.error("   %s exited with code %d", sid, proc.returncode)
        return {"id": sid, "status": status, "returncode": proc.returncode,
                "before": before, "after": after, "elapsed": elapsed}
    except Exception as exc:
        elapsed = time.monotonic() - t0
        log.error("   Failed to launch %s: %s", sid, exc)
        return {"id": sid, "status": "error", "reason": str(exc),
                "before": before, "after": before, "elapsed": elapsed}


# ── Entry point ───────────────────────────────────────────────────────────────


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run all MCFD scrapers in sequence"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Pass --limit N to each scraper that supports it (useful for testing)",
    )
    args = parser.parse_args()

    log.info("━" * 60)
    log.info("  MCFD FILES — SCRAPE PIPELINE")
    limit_label = f"--limit {args.limit}" if args.limit else "full run"
    log.info("  mode: %s", limit_label)
    log.info("━" * 60)

    wall_start = time.monotonic()
    results = []

    for scraper in SCRAPERS:
        result = await _run_one(scraper, args.limit)
        results.append(result)

    total_elapsed = time.monotonic() - wall_start

    # ── Summary ───────────────────────────────────────────────────────────────
    log.info("")
    log.info("━" * 60)
    log.info("  SUMMARY")
    log.info("━" * 60)

    total_new = 0
    total_errors = 0

    for r in results:
        sid = r["id"]
        status = r["status"]
        elapsed = r.get("elapsed", 0.0)
        new = r.get("after", 0) - r.get("before", 0)
        after = r.get("after", 0)

        if status == "skipped":
            log.info("  %-12s  SKIPPED   %s", sid, r.get("reason", ""))
        elif status == "error":
            total_errors += 1
            log.info("  %-12s  ERROR     %.1fs", sid, elapsed)
        else:
            total_new += new
            log.info("  %-12s  OK  +%-5d  (%d total)  %.1fs",
                     sid, new, after, elapsed)

    log.info("  %s", "─" * 50)
    log.info("  New documents : %d", total_new)
    log.info("  Errors        : %d", total_errors)
    log.info("  Total time    : %.1fs", total_elapsed)
    log.info("━" * 60)

    if total_errors:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
