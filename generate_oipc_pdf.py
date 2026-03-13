"""
SESSION 53 — MAX NUKAGE EDITION
OIPC Complaint PDF Generator — CFD-2025-53478 / INV-F-26-00220
All content drawn from Phase 1 DB analysis and verified brain facts.
"""
import io, os, sys

try:
    import fitz
except ImportError:
    os.system("pip install pymupdf -q")
    import fitz

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

OUTPUT_PATH = "data/raw/personal/OIPC_COMPLAINT_ONE_PAGE.pdf"
os.makedirs("data/raw/personal", exist_ok=True)


def build_story(body_size=8.0, heading_size=8.5, sub_size=7.5, footer_size=6.5, compact_size=7.0):
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('title', parent=styles['Normal'],
        fontName='Times-Bold', fontSize=10,
        alignment=TA_CENTER, spaceAfter=1, spaceBefore=0)

    sub_style = ParagraphStyle('sub', parent=styles['Normal'],
        fontName='Times-Roman', fontSize=sub_size,
        alignment=TA_CENTER, spaceAfter=2, textColor='#333333')

    heading_style = ParagraphStyle('heading', parent=styles['Normal'],
        fontName='Times-Bold', fontSize=heading_size,
        spaceBefore=3, spaceAfter=0)

    body_style = ParagraphStyle('body', parent=styles['Normal'],
        fontName='Times-Roman', fontSize=body_size,
        leading=body_size * 1.18, alignment=TA_JUSTIFY, spaceAfter=1)

    compact_style = ParagraphStyle('compact', parent=styles['Normal'],
        fontName='Times-Roman', fontSize=compact_size,
        leading=compact_size * 1.18, alignment=TA_JUSTIFY, spaceAfter=1)

    footer_style = ParagraphStyle('footer', parent=styles['Normal'],
        fontName='Times-Roman', fontSize=footer_size,
        leading=footer_size * 1.25, textColor='#444444', spaceBefore=2)

    hr = HRFlowable(width="100%", thickness=0.4, spaceAfter=2, spaceBefore=1)

    story = []

    # ── HEADER ──────────────────────────────────────────────────────────────
    story += [
        Paragraph(
            "COMPLAINT — FOI CFD-2025-53478: PRODUCTION INTEGRITY FAILURE",
            title_style),
        Paragraph(
            "OIPC File: INV-F-26-00220 &nbsp;&#124;&nbsp; Applicant: C.L. &nbsp;&#124;&nbsp; "
            "Public Body: MCFD &nbsp;&#124;&nbsp; March 12, 2026 &nbsp;&#124;&nbsp; "
            "Response Required: <b>March 21, 2026</b>",
            sub_style),
        hr,
    ]

    # ── SECTION 1 — THREE CONFLICTING PAGE COUNTS ───────────────────────────
    story += [
        Paragraph("1. Production Integrity Failure — Three Conflicting Page Counts", heading_style),
        Paragraph(
            "MCFD represented <b>1,792 pages</b> to OIPC when INV-F-26-00220 was opened "
            "(\"complex, containing 1,792 pages that must be reviewed line by line\"). "
            "MCFD's own internal production stamps read <b>\"Page X of 1,233–1,239\"</b> on delivered "
            "pages. The applicant received <b>906 pages</b> on Feb 25, 2026 — <b>886 pages "
            "unaccounted for</b>. Three conflicting counts cannot be attributed to redaction: "
            "they indicate a production integrity failure. Either MCFD withheld 886 pages without "
            "serving a redaction notice (FOIPPA s.7 violation) or misrepresented the file size to "
            "this office (FOIPPA s.74(1)(a) — offence; s.74(2) — fine up to $5,000). "
            "FOIPPA ss.42–44 require investigation.",
            body_style),
    ]

    # ── SECTION 2 — STATUTORY TIMELINE ─────────────────────────────────────
    story += [
        Paragraph("2. FOIPPA Statutory Timeline — Serial Obstruction", heading_style),
        Paragraph(
            "<b>Aug 16, 2025</b>: Request filed. s.7(1) prima facie deadline: ~Sep 26, 2025. "
            "<b>Oct 1, 2025</b>: First 45-day s.10 extension. "
            "<b>Nov 13, 2025</b>: Second extension — granted one day before prior deadline. "
            "<b>Jan 21, 2026</b>: Extended deadline missed — <b>s.7(2) deemed refusal</b>. "
            "OIPC complaint filed; INV-F-26-00220 opened. "
            "<b>Jan 29, 2026</b>: MCFD requests further extension to Mar 4, 2026 — "
            "200 days from original request. "
            "<b>Feb 25, 2026</b>: 906 pages produced, 160+ days overdue. "
            "Granting an extension one day before a prior deadline, missing it, then requesting "
            "41 more days is not administrative complexity — it is obstruction under s.74(1)(a).",
            body_style),
    ]

    # ── SECTION 3 — MISSING RECORDS ─────────────────────────────────────────
    story += [
        Paragraph("3. Missing Responsive Records — Material to May 19 Trial", heading_style),
        Paragraph(
            "(a) <b>Sept 8, 2025 Wolfenden email</b>: Falls within the request date range "
            "(Aug 16, 2025 request). Keyword search of all 906 delivered pages: <b>zero hits</b>. "
            "This email documents N. Wolfenden requesting genetic validation of evidence she "
            "dismissed on Aug 7 as \"unsubstantiated\" — directly contradicting her Form F1. "
            "Its absence is not explained by any redaction notice served. "
            "(b) <b>Attachments pp.601–650</b>: FOI internal index references attachments not "
            "produced — including pharmacogenomic and dietary reports from CLIA-accredited labs "
            "ordered by Dr. Bratt. On Aug 7, 2025, N. Wolfenden stated on camera: "
            "\"I'm not gonna read this\" when offered these reports. N. was subsequently placed "
            "on sertraline + risperidone. N. is a CYP2D6 POOR METABOLIZER (FOI p.803). "
            "Sertraline inhibited CYP2D6 &#8594; risperidone overexposure &#8594; hallucinations, "
            "psychotic break, extrapyramidal symptoms. These records are responsive and material. "
            "They must be produced or specifically exempted.",
            body_style),
    ]

    # ── SECTION 4 — s.96 PRE-REMOVAL PULLS ─────────────────────────────────
    story += [
        Paragraph("4. CFCSA s.96 Pre-Removal Information Pulls", heading_style),
        Paragraph(
            "FOI records confirm MCFD conducted CFCSA s.96 information pulls beginning May 2025 — "
            "three months before the Aug 7 removal and any documented protection concern. "
            "If no bona fide investigation existed at that time, collection was unauthorized "
            "under FOIPPA s.26. These records are responsive to this request and have not been "
            "produced or exempted. Their origin and authorization require investigation.",
            body_style),
    ]

    # ── SECTION 5 — OIPC CONDUCT + DISABILITY ACCOMMODATION ────────────────
    story += [
        Paragraph("5. OIPC Procedural Conduct — March 11, 2026 Email", heading_style),
        Paragraph(
            "The applicant is a CAF Veteran (3 RCR), VAC-pensioned PTSD and ADHD. Written "
            "correspondence is a recognized accommodation for service-related PTSD and ADHD under "
            "CHRA ss.2\u20133, BC Human Rights Code s.8, and MCFD\u2019s own Accessibility &amp; Inclusion Policy. "
            "The March 11, 2026 OIPC response raises three concerns: "
            "(a) <b>Factual error</b>: The email states \"no files have been open\" \u2014 "
            "INV-F-26-00220 was opened Jan 21, 2026 with investigator J. Percy-Campbell assigned. "
            "(b) <b>Procedural trap</b>: Directing restart with a mandatory 30-business-day wait "
            "(\u223cJune 3, 2026) would post-date the <b>May 19\u201321, 2026 trial</b> in PC 19700 \u2014 "
            "the precise proceeding for which this evidence is material. "
            "(c) <b>Policy misapplication</b>: The Respectful Conduct Policy threat implicates "
            "Charter s.2(b) (expression), s.7 (security), s.15(1) (equality), and BC HRC s.8. "
            "The applicant\u2019s s.6(1) right of access is not diminished by the length or tone of "
            "his advocacy for his removed child. Threatening access restriction while 886 FOI pages "
            "remain unproduced raises procedural fairness concerns under FOIPPA ss.42\u201344. "
            "The same records confirm MCFD conducted s.96 information pulls beginning May 2025 \u2014 "
            "three months before any documented protection concern \u2014 and ignored pharmacogenomic "
            "reports (CYP2D6 POOR METABOLIZER, FOI p.803) that would have prevented harm to N.",
            body_style),
    ]

    # ── SECTION 6 — STATUTORY FRAMEWORK ─────────────────────────────────────
    story += [
        Paragraph("6. Statutory Framework", heading_style),
        Paragraph(
            "<b>FOIPPA</b>: s.6(1) right of access; s.7(1)/(2) response/deemed refusal; "
            "s.10 extensions; s.22(1) unauthorized disclosure (N. Wolfenden disclosed "
            "applicant's personal contact info to a therapist without consent, Mar 6 — "
            "triggered VAC-pensioned PTSD); s.25 duty to assist; s.26 collection limits; "
            "ss.42–44 complaint/investigation/order; s.74(1)(a)/(2) offence/fine. "
            "<b>CFCSA</b>: s.30 (removal requires reasonable grounds — impossible without "
            "observation: R. Burnstein, Aug 7, 2025: \"no eyes have been seen on his daughter\"; "
            "see 2025 BCCA 151; 2022 BCSC 168); s.96 information access. "
            "<b>Charter</b>: s.2(b) expression; s.7 security; s.15(1) equality. "
            "<b>BC HRC</b>: s.8 services. <b>CHRA</b>: ss.2–3 disability.",
            compact_style),
    ]

    # ── SECTION 7 — DEMANDS ──────────────────────────────────────────────────
    story += [
        Paragraph("7. Demands — March 21, 2026 (7 Business Days)", heading_style),
        Paragraph(
            "(1) Confirm INV-F-26-00220 is open and active; correct the March 11 factual error. "
            "(2) Explain the 886-page discrepancy — page-by-page, citing applicable ss.13–22 "
            "exemptions for each withheld page. (3) Direct MCFD to produce remaining records "
            "within 7 business days (by March 21, 2026) or cite specific exemptions. "
            "(4) Investigate who authorized representing 1,792 pages to OIPC when 906 were "
            "produced — potential s.74(1)(a) offence. "
            "(5) Investigate pre-removal s.96 pulls (May 2025) and whether lawful authorization "
            "existed. (6) Withdraw or clarify the Respectful Conduct Policy warning in light of "
            "the applicant's disability accommodations and the factual error in the March 11 email.",
            body_style),
    ]

    # ── FOOTER ───────────────────────────────────────────────────────────────
    story += [
        hr,
        Paragraph(
            "<b>C.L.</b> &nbsp;&#124;&nbsp; CAF Veteran, 3 RCR &nbsp;&#124;&nbsp; "
            "778-586-7916 &nbsp;&#124;&nbsp; Trial: May 19–21, 2026, PC 19700",
            footer_style),
        Paragraph(
            "<b>cc:</b> Peter Milobar MLA &#183; BC Ombudsperson &#183; "
            "Representative for Children &amp; Youth &#183; C. Sa&#39;d, Counsel &#183; "
            "MCFD FOI Coordinator &#183; CCLA &#183; BCCLA &#183; "
            "Senate Committee on Legal &amp; Constitutional Affairs &#183; Veterans Ombudsman",
            footer_style),
    ]

    return story


def build_pdf_bytes(body_size=8.0, heading_size=8.5):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.35 * inch, bottomMargin=0.35 * inch,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
    )
    sub_size = max(6.5, body_size - 0.5)
    footer_size = max(5.5, body_size - 1.5)
    compact_size = max(6.5, body_size - 1.0)
    doc.build(build_story(body_size, heading_size, sub_size, footer_size, compact_size))
    buf.seek(0)
    return buf.read()


# ── AUTO 1-PAGE ENFORCEMENT ──────────────────────────────────────────────────
print("Building PDF — auto 1-page enforcement active...")
body_size = 8.0
heading_size = 8.5
step = 0.25
min_body = 6.5
pdf_bytes = None

while body_size >= min_body:
    pdf_bytes = build_pdf_bytes(body_size, heading_size)
    with fitz.open(stream=pdf_bytes, filetype="pdf") as d:
        pages = d.page_count
        chars = len(d[0].get_text())
        print(f"  body={body_size:.2f}pt heading={heading_size:.2f}pt → {pages} page(s), {chars} chars")
        if pages == 1:
            break
    body_size -= step
    heading_size -= step

if fitz.open(stream=pdf_bytes, filetype="pdf").page_count != 1:
    print("ERROR: Cannot fit to 1 page at minimum font size. Review content length.")
    sys.exit(1)

with open(OUTPUT_PATH, "wb") as f:
    f.write(pdf_bytes)

with fitz.open(OUTPUT_PATH) as d:
    char_count = len(d[0].get_text())
    print(f"\nPDF written: {OUTPUT_PATH}")
    print(f"Pages: {d.page_count}")
    print(f"Dimensions: {d[0].rect.width:.0f} x {d[0].rect.height:.0f} pts")
    print(f"Text chars: {char_count}")
