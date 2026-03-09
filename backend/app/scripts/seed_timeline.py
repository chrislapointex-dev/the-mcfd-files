"""Seed known timeline events into the timeline_events table.

Idempotent: clears existing rows before inserting, so safe to re-run.

Run with:
    docker exec <backend> python3 -m app.scripts.seed_timeline
"""

import asyncio

from sqlalchemy import delete

from ..database import SessionLocal
from ..models import TimelineEvent

EVENTS = [
    {
        "event_date": "2025-08-04",
        "title": "MCFD Internal Coordination Begins",
        "description": (
            "FOI records show directive chain initiated: Muileboom → Burnstein → Wolfenden. "
            "Pre-planned removal timeline begins before any formal protection concern documented."
        ),
        "category": "mcfd_action",
        "severity": "critical",
        "source_ref": "FOI p.601-650",
    },
    {
        "event_date": "2025-08-07",
        "title": "Coordination Timeline Complete",
        "description": (
            "Internal coordination between Muileboom, Burnstein, and Wolfenden finalised. "
            "Removal direction issued by Burnstein without personally observing the child."
        ),
        "category": "mcfd_action",
        "severity": "critical",
        "source_ref": "FOI internal notes",
    },
    {
        "event_date": "2025-08-12",
        "title": "Wolfenden Files Form F1",
        "description": (
            "SW Wolfenden files sworn Form F1 containing statement directly contradicted by "
            "27-minute video recording. PC 19700 filed one day after custody notice served."
        ),
        "category": "mcfd_action",
        "severity": "critical",
        "source_ref": "Form F1, Video evidence",
    },
    {
        "event_date": "2025-08-15",
        "title": "FOI File Cutoff",
        "description": (
            "FOI file (CFD-2025-53478) cuts off. Key documents missing including Sept 8 "
            "Wolfenden email. MCFD represented 1,792 pages to OIPC — 906 pages delivered."
        ),
        "category": "evidence",
        "severity": "critical",
        "source_ref": "CFD-2025-53478",
    },
    {
        "event_date": "2025-09-08",
        "title": "Missing Wolfenden Email",
        "description": (
            "Email from SW Wolfenden identified as missing from FOI production. "
            "OIPC complaint filed re: incomplete disclosure."
        ),
        "category": "evidence",
        "severity": "high",
        "source_ref": "OIPC INV-F-26-00220",
    },
    {
        "event_date": "2025-11-24",
        "title": "Judicial Review Filed",
        "description": "Judicial review petition filed (SC 064851). MCFD defaulted on response.",
        "category": "legal_filing",
        "severity": "high",
        "source_ref": "SC 064851",
    },
    {
        "event_date": "2026-01-21",
        "title": "FOI Deadline Missed",
        "description": "MCFD missed FOI response deadline. OIPC complaint filed.",
        "category": "complaint",
        "severity": "high",
        "source_ref": "OIPC complaint",
    },
    {
        "event_date": "2026-02-25",
        "title": "FOI File Picked Up",
        "description": (
            "906-page FOI file (CFD-2025-53478) picked up from MCFD. "
            "Two physical + two digital copies made. 1,051 keyword hits found across 19 OCR batches."
        ),
        "category": "evidence",
        "severity": "high",
        "source_ref": "CFD-2025-53478",
    },
    {
        "event_date": "2026-05-19",
        "title": "TRIAL DATE — PC 19700",
        "description": "Trial begins. PC 19700 protection order. 3 days scheduled (May 19-21, 2026).",
        "category": "legal_filing",
        "severity": "critical",
        "source_ref": "PC 19700",
    },
    {
        "event_date": "2025-08-19",
        "title": "Newton Approves Post-Removal File Without Reviewing Video",
        "description": "TL Tammy Newton approves post-removal file 12 days after August 7 removal. Never present at removal. Never reviewed 27-minute video contradicting Wolfenden's Form A sworn statements before approving.",
        "category": "mcfd_action",
        "severity": "critical",
        "source_ref": "Form A, March 6 2026 correspondence",
    },
    {
        "event_date": "2025-08-21",
        "title": "Newton Observes Appropriate Parenting — Later Contradicts",
        "description": "Newton's own supervised visit: found materials age-appropriate, agreed with developmental assessment, positive visit (audio recorded). Her September 24 2025 letter then characterized LaPointe as a danger with no new incident in 21 days.",
        "category": "evidence",
        "severity": "critical",
        "source_ref": "August 21 audio recording, Newton Sept 24 2025 letter",
    },
    {
        "event_date": "2025-09-24",
        "title": "Newton Issues False September 24 Letter",
        "description": "Newton letter contains unsubstantiated allegations of harassment, coercion, and harm. OT Branscombe documented excellent parenting July 29. Pharmacist Dayton validated pharmacogenomic concerns day after Wolfenden refused to review them. Newton ignored all professional documentation.",
        "category": "mcfd_action",
        "severity": "high",
        "source_ref": "Newton Sept 24 2025 letter, OT Branscombe July 29 2025, Pharmacist Dayton",
    },
]


async def seed():
    async with SessionLocal() as db:
        # Clear existing rows (idempotent re-run)
        await db.execute(delete(TimelineEvent))
        await db.flush()

        for ev in EVENTS:
            db.add(TimelineEvent(**ev))

        await db.commit()
        print(f"Seeded {len(EVENTS)} timeline events")


if __name__ == "__main__":
    asyncio.run(seed())
