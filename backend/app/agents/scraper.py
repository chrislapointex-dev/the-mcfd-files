"""MCFD Historical Scraper — CanLII, RCY, Hansard.

All scrapers:
- Use httpx.AsyncClient with a public-interest User-Agent
- Sleep 2s between requests (polite rate limiting)
- Stop on 403/429
- Redact names via redact_name() before storage
- Deduplicate on UNIQUE citation/url before insert
- Return AgentResult
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ScrapedDecision, ScrapedReport, ScrapedHansard
from ..redact import redact_name
from .core import AgentResult, AgentStatus, register_agent, update_status

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "MCFD-Files-Research/1.0 (public-interest-research)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_SLEEP = 2.0  # seconds between requests


# ── CanLII ────────────────────────────────────────────────────────────────────

async def scrape_canlii(pages: int, db: AsyncSession) -> AgentResult:
    """Scrape CanLII for BC MCFD-related decisions."""
    name = "canlii"
    result = register_agent(name)
    result.status = AgentStatus.RUNNING
    result.started_at = datetime.now(timezone.utc)
    result.errors = []
    result.log = []
    result.records_found = 0
    result.records_added = 0
    update_status(name, result)

    # CanLII search: BC Court of Appeal + "Ministry of Children" keyword
    base_url = "https://www.canlii.org/en/bc/bcca/nav/date/2020-2025.html"
    search_url = "https://www.canlii.org/en/search/results.html"
    params_base = {
        "text": '"Ministry of Children" "family development"',
        "origin": "en",
        "jId": "bcca,bcsc",
    }

    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
            for page_num in range(1, pages + 1):
                params = {**params_base, "startIndex": str((page_num - 1) * 10)}
                result.log.append(f"Fetching CanLII page {page_num}")
                try:
                    resp = await client.get(search_url, params=params)
                    if resp.status_code in (403, 429):
                        result.log.append(f"Rate limited ({resp.status_code}) — stopping")
                        result.errors.append(f"HTTP {resp.status_code} on page {page_num}")
                        break
                    if not resp.is_success:
                        result.log.append(f"HTTP {resp.status_code} on page {page_num} — skipping")
                        result.errors.append(f"HTTP {resp.status_code} on page {page_num}")
                        await asyncio.sleep(_SLEEP)
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    result_links = soup.select("a.result-title, .result a[href*='/bc/']")

                    if not result_links:
                        result.log.append(f"No results on page {page_num} — done")
                        break

                    for link in result_links:
                        href = link.get("href", "")
                        if not href.startswith("http"):
                            href = f"https://www.canlii.org{href}"
                        case_name = redact_name(link.get_text(strip=True))
                        citation_el = link.find_next_sibling(class_="result-citation")
                        citation = citation_el.get_text(strip=True) if citation_el else None
                        result.records_found += 1

                        # Dedup check
                        existing = await db.execute(
                            select(ScrapedDecision).where(
                                ScrapedDecision.url == href
                            )
                        )
                        if existing.scalar_one_or_none():
                            continue

                        # Fetch decision page for excerpt
                        await asyncio.sleep(_SLEEP)
                        try:
                            dec_resp = await client.get(href)
                            if dec_resp.status_code in (403, 429):
                                result.errors.append(f"Rate limited on {href}")
                                break
                            if not dec_resp.is_success:
                                continue
                            dec_soup = BeautifulSoup(dec_resp.text, "html.parser")
                            content_el = dec_soup.select_one("#documentContent, .documentContent, article")
                            raw_excerpt = content_el.get_text(" ", strip=True)[:1000] if content_el else ""
                            excerpt = redact_name(raw_excerpt)

                            # Parse date and court from page
                            date_el = dec_soup.select_one(".decision-date, .date")
                            court_el = dec_soup.select_one(".court-name, .tribunal")
                            from datetime import date as date_type
                            dec_date = None
                            if date_el:
                                try:
                                    from dateutil import parser as dp
                                    dec_date = dp.parse(date_el.get_text(strip=True)).date()
                                except Exception:
                                    pass
                            court = court_el.get_text(strip=True) if court_el else "BC Courts"

                        except Exception as e:
                            result.errors.append(f"Error fetching {href}: {e}")
                            excerpt = ""
                            dec_date = None
                            court = "BC Courts"

                        row = ScrapedDecision(
                            case_name=case_name,
                            citation=citation,
                            court=court,
                            date=dec_date,
                            url=href,
                            excerpt=excerpt,
                            source="canlii",
                            scraped_at=datetime.now(timezone.utc),
                        )
                        db.add(row)
                        result.records_added += 1

                    await db.commit()
                    await asyncio.sleep(_SLEEP)

                except httpx.RequestError as e:
                    result.errors.append(f"Request error page {page_num}: {e}")
                    result.log.append(f"Request error page {page_num}: {e}")
                    await asyncio.sleep(_SLEEP)

    except Exception as e:
        result.errors.append(f"Fatal: {e}")
        result.status = AgentStatus.ERROR
    else:
        result.status = AgentStatus.COMPLETED

    result.completed_at = datetime.now(timezone.utc)
    update_status(name, result)
    return result


# ── RCY ───────────────────────────────────────────────────────────────────────

async def scrape_rcy(db: AsyncSession) -> AgentResult:
    """Scrape Representative for Children and Youth (RCY) BC reports."""
    name = "rcy"
    result = register_agent(name)
    result.status = AgentStatus.RUNNING
    result.started_at = datetime.now(timezone.utc)
    result.errors = []
    result.log = []
    result.records_found = 0
    result.records_added = 0
    update_status(name, result)

    index_url = "https://rcybc.ca/reports-and-publications/"

    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
            result.log.append("Fetching RCY reports index")
            resp = await client.get(index_url)
            if resp.status_code in (403, 429):
                result.errors.append(f"HTTP {resp.status_code} on RCY index")
                result.status = AgentStatus.ERROR
                result.completed_at = datetime.now(timezone.utc)
                update_status(name, result)
                return result

            if not resp.is_success:
                result.errors.append(f"HTTP {resp.status_code} on RCY index")
                result.status = AgentStatus.ERROR
                result.completed_at = datetime.now(timezone.utc)
                update_status(name, result)
                return result

            soup = BeautifulSoup(resp.text, "html.parser")
            report_links = soup.select("article a, .report-card a, h2 a, h3 a")

            for link in report_links:
                href = link.get("href", "")
                if not href:
                    continue
                if not href.startswith("http"):
                    href = f"https://rcybc.ca{href}"
                title = redact_name(link.get_text(strip=True))
                if not title:
                    continue
                result.records_found += 1

                # Dedup check
                existing = await db.execute(
                    select(ScrapedReport).where(ScrapedReport.url == href)
                )
                if existing.scalar_one_or_none():
                    continue

                # Fetch report page for summary
                await asyncio.sleep(_SLEEP)
                try:
                    rep_resp = await client.get(href)
                    if rep_resp.status_code in (403, 429):
                        result.errors.append(f"Rate limited on {href}")
                        break
                    if not rep_resp.is_success:
                        continue
                    rep_soup = BeautifulSoup(rep_resp.text, "html.parser")
                    summary_el = rep_soup.select_one(".entry-content p, .report-summary, article p")
                    raw_summary = summary_el.get_text(" ", strip=True)[:800] if summary_el else ""
                    summary = redact_name(raw_summary)

                    date_el = rep_soup.select_one("time, .date, .published")
                    rep_date = None
                    if date_el:
                        try:
                            from dateutil import parser as dp
                            rep_date = dp.parse(date_el.get("datetime", date_el.get_text(strip=True))).date()
                        except Exception:
                            pass

                    # Classify report type
                    title_lower = title.lower()
                    if "investigation" in title_lower or "audit" in title_lower:
                        report_type = "investigation"
                    elif "annual" in title_lower:
                        report_type = "annual"
                    elif "review" in title_lower:
                        report_type = "review"
                    else:
                        report_type = "report"

                except Exception as e:
                    result.errors.append(f"Error fetching {href}: {e}")
                    summary = ""
                    rep_date = None
                    report_type = "report"

                row = ScrapedReport(
                    title=title,
                    date=rep_date,
                    url=href,
                    summary=summary,
                    report_type=report_type,
                    source="rcy",
                    scraped_at=datetime.now(timezone.utc),
                )
                db.add(row)
                result.records_added += 1

            await db.commit()

    except Exception as e:
        result.errors.append(f"Fatal: {e}")
        result.status = AgentStatus.ERROR
    else:
        result.status = AgentStatus.COMPLETED

    result.completed_at = datetime.now(timezone.utc)
    update_status(name, result)
    return result


# ── Hansard ───────────────────────────────────────────────────────────────────

async def scrape_hansard(pages: int, db: AsyncSession) -> AgentResult:
    """Scrape BC Legislature Hansard debates mentioning MCFD."""
    name = "hansard"
    result = register_agent(name)
    result.status = AgentStatus.RUNNING
    result.started_at = datetime.now(timezone.utc)
    result.errors = []
    result.log = []
    result.records_found = 0
    result.records_added = 0
    update_status(name, result)

    search_url = "https://www.leg.bc.ca/hansard/40th4th/H{date}am-Room8.htm"
    # Use the Hansard search API endpoint
    hansard_search = "https://www.leg.bc.ca/cgi-bin/XXstatement.pl"

    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
            for page_num in range(1, pages + 1):
                params = {
                    "qryType": "phrase",
                    "qryWord": "Ministry of Children Family Development",
                    "qrySess": "",
                    "offset": str((page_num - 1) * 20),
                }
                result.log.append(f"Fetching Hansard page {page_num}")
                try:
                    resp = await client.get(hansard_search, params=params)
                    if resp.status_code in (403, 429):
                        result.log.append(f"Rate limited ({resp.status_code}) — stopping")
                        result.errors.append(f"HTTP {resp.status_code} on page {page_num}")
                        break
                    if not resp.is_success:
                        result.errors.append(f"HTTP {resp.status_code} on page {page_num}")
                        await asyncio.sleep(_SLEEP)
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    rows = soup.select("table tr, .result-row, li.hansard-result")

                    if not rows:
                        result.log.append(f"No results on page {page_num} — done")
                        break

                    for row in rows:
                        link_el = row.select_one("a")
                        if not link_el:
                            continue
                        href = link_el.get("href", "")
                        if not href.startswith("http"):
                            href = f"https://www.leg.bc.ca{href}"

                        # Extract speaker and excerpt from row
                        cells = row.select("td")
                        speaker = redact_name(cells[1].get_text(strip=True)) if len(cells) > 1 else "Unknown"
                        raw_excerpt = cells[-1].get_text(" ", strip=True)[:800] if cells else ""
                        excerpt = redact_name(raw_excerpt)

                        # Parse date
                        date_text = cells[0].get_text(strip=True) if cells else ""
                        debate_date = None
                        if date_text:
                            try:
                                from dateutil import parser as dp
                                debate_date = dp.parse(date_text).date()
                            except Exception:
                                pass

                        result.records_found += 1

                        # Dedup check (url + debate_date + speaker unique)
                        existing = await db.execute(
                            select(ScrapedHansard).where(
                                ScrapedHansard.url == href,
                                ScrapedHansard.speaker == speaker,
                            )
                        )
                        if existing.scalar_one_or_none():
                            continue

                        hansard_row = ScrapedHansard(
                            debate_date=debate_date,
                            speaker=speaker,
                            excerpt=excerpt,
                            url=href,
                            session="",
                            source="hansard",
                            scraped_at=datetime.now(timezone.utc),
                        )
                        db.add(hansard_row)
                        result.records_added += 1

                    await db.commit()
                    await asyncio.sleep(_SLEEP)

                except httpx.RequestError as e:
                    result.errors.append(f"Request error page {page_num}: {e}")
                    await asyncio.sleep(_SLEEP)

    except Exception as e:
        result.errors.append(f"Fatal: {e}")
        result.status = AgentStatus.ERROR
    else:
        result.status = AgentStatus.COMPLETED

    result.completed_at = datetime.now(timezone.utc)
    update_status(name, result)
    return result
