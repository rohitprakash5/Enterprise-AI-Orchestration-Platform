"""
Generate the synthetic Apex Analytics Corp Annual Report 2023 PDF.
Run once: python eio/data/demo/generate_annual_report.py
"""
from __future__ import annotations

import os
from pathlib import Path

OUTPUT_PATH = os.getenv(
    "EIO_ANNUAL_REPORT_PATH",
    "eio/data/demo/documents/annual_report_2023.pdf",
)

REPORT_SECTIONS = [
    ("APEX ANALYTICS CORP", "Annual Report 2023\nDriving Enterprise Intelligence Forward"),
    ("LETTER FROM THE CEO", """
Dear Shareholders,

2023 was a transformational year for Apex Analytics Corp. We achieved record revenues
of $185.4 million, representing 22% year-over-year growth — our seventh consecutive
year of double-digit expansion.

Our Cloud Platform business surpassed $80 million in annual recurring revenue,
validating our strategic pivot to cloud-native solutions that began in 2020. Enterprise
adoption accelerated significantly, with 47 new Fortune 500 customers signing multi-year
agreements in Q4 2023 alone.

We remain deeply committed to our growth strategy: expanding our Analytics Suite into
emerging markets, deepening our Professional Services capabilities, and investing
aggressively in AI-powered automation features that our customers increasingly demand.

Looking ahead to 2024, we project revenue growth of 18-24%, driven by strong pipeline
momentum in the financial services and healthcare verticals. Our EBITDA margin expanded
to 38% in Q4 2023, demonstrating the powerful operating leverage inherent in our
software business model.

I am proud of what our 1,240 employees have achieved, and I am confident in our
trajectory toward becoming the leading enterprise analytics platform globally.

Sincerely,
Jonathan R. Caldwell
Chief Executive Officer, Apex Analytics Corp
"""),
    ("FINANCIAL HIGHLIGHTS 2023", """
Key Financial Metrics (Full Year 2023)
=======================================

Total Revenue:             $185.4M    (+22% YoY)
Cloud Platform Revenue:    $ 82.1M    (+41% YoY)
Analytics Suite Revenue:   $ 54.3M    (+18% YoY)
Professional Services:     $ 31.6M    (+12% YoY)
Licensing Revenue:         $ 17.4M    ( -3% YoY, planned decline)

Operating Expenses:        $114.7M    (+15% YoY)
  - R&D Investment:        $ 32.4M    (17.5% of revenue)
  - Sales & Marketing:     $ 41.2M    (22.2% of revenue)
  - G&A:                   $ 18.3M    ( 9.9% of revenue)
  - COGS:                  $ 22.8M    (12.3% of revenue)

EBITDA:                    $ 70.7M    (38.1% margin)
Net Income:                $ 52.8M    (28.5% margin)
Free Cash Flow:            $ 61.3M    (+28% YoY)

Q4 2023 Revenue:           $ 58.2M    (+25% YoY, strongest quarter)
Q4 2023 EBITDA:            $ 22.1M    (38.0% margin)

Annual Recurring Revenue (ARR):   $164.8M (+35% YoY)
Net Revenue Retention:            118%
Customer Count:                   2,847 (+31% YoY)
"""),
    ("QUARTERLY PERFORMANCE SUMMARY", """
Quarterly Revenue Breakdown (2023)
====================================

Q1 2023:  $38.2M  (+18% YoY)  —  Strong enterprise renewals; Q1 traditionally softer
Q2 2023:  $42.7M  (+20% YoY)  —  New logo acceleration in APAC; healthcare vertical wins
Q3 2023:  $46.3M  (+22% YoY)  —  Cloud platform migrations drove upsell motion
Q4 2023:  $58.2M  (+25% YoY)  —  Record quarter; 47 new F500 logos; strong professional services

Sequential Growth (QoQ):
Q1→Q2: +11.8%
Q2→Q3: +8.4%
Q3→Q4: +25.7%  (seasonal + sales cycle)

Three-Year Revenue Trajectory:
2021: $124.3M
2022: $151.9M  (+22.2% YoY)
2023: $185.4M  (+22.1% YoY)
"""),
    ("GROWTH STRATEGY AND OUTLOOK", """
Strategic Priorities for 2024-2026
=====================================

1. AI-Powered Analytics (Top Priority)
   We are investing $45M over the next 18 months to embed generative AI and large
   language model capabilities directly into our Analytics Suite. Early enterprise
   pilots have demonstrated a 40% reduction in time-to-insight for financial analytics
   use cases. We believe AI orchestration will become the dominant paradigm for
   enterprise data analysis by 2026.

2. Geographic Expansion
   International revenue represented 28% of total revenue in 2023, up from 19% in 2021.
   We are establishing regional headquarters in Singapore (APAC), Frankfurt (EMEA), and
   São Paulo (LatAm) to accelerate local market penetration. We project international
   revenue to reach 40% of total revenue by 2026.

3. Vertical Deepening
   Financial services, healthcare, and manufacturing represent 68% of our customer base.
   We are building vertical-specific data connectors, compliance modules, and
   industry-standard reporting templates to deepen switching costs and expand wallet share.

4. Platform Ecosystem
   Our developer platform now has 1,200 certified integration partners. We project
   marketplace revenue to grow from $4.2M in 2023 to $18M by 2025 as the ecosystem matures.

2024 Financial Guidance
========================
Revenue:               $218M - $230M    (+18% to +24% YoY)
EBITDA Margin:         38% - 41%
Free Cash Flow:        $72M - $80M
R&D Investment:        ~18% of revenue
Capital Expenditures:  ~3% of revenue
"""),
    ("RISK FACTORS", """
Principal Risks and Mitigations
=================================

Market Concentration Risk
  28% of revenue is concentrated in the top 50 customers. We are actively diversifying
  by investing in mid-market sales capacity and self-serve onboarding capabilities.

Competitive Landscape
  The enterprise analytics market is intensely competitive. Key competitors include
  Tableau (Salesforce), Power BI (Microsoft), and Looker (Google). We differentiate
  through superior data connectors, AI-native architecture, and enterprise security.

Macroeconomic Sensitivity
  Enterprise software spending is correlated with GDP growth and IT budget cycles.
  Our 118% net revenue retention provides resilience through cycles as existing
  customers expand usage even when new logo acquisition slows.

AI Regulatory Risk
  Emerging AI governance regulations in the EU (EU AI Act) and North America may
  require product modifications. We are proactively investing in explainability
  and audit trail capabilities to achieve compliance ahead of regulatory deadlines.

Talent Retention
  Demand for AI and data engineering talent is intense. We have implemented
  equity refresh programs and launched an AI apprenticeship program targeting
  200 new hires in 2024.
"""),
    ("CORPORATE GOVERNANCE", """
Board Composition and Executive Team
======================================

Board of Directors:
  - Dr. Sarah Chen (Chairwoman) — Former CTO, Oracle Corporation
  - Jonathan R. Caldwell — CEO, Apex Analytics Corp
  - Marcus T. Williams — CFO, Apex Analytics Corp
  - Elena Rodriguez — Former SVP, Salesforce
  - Prof. David Kim — AI Research Lead, Stanford University

Executive Leadership:
  CEO:  Jonathan R. Caldwell  (tenure: 7 years)
  CFO:  Marcus T. Williams    (tenure: 4 years)
  CTO:  Priya Patel           (tenure: 3 years)
  COO:  Robert A. Fischer     (tenure: 5 years)
  CMO:  Amanda Liu            (tenure: 2 years)

ESG Commitments:
  - Carbon neutral operations achieved in Q3 2023
  - 42% female representation in leadership roles (+8pp YoY)
  - $2.1M invested in STEM education partnerships
  - SOC 2 Type II, ISO 27001, and FedRAMP Moderate certified
"""),
]


def generate() -> None:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph, SimpleDocTemplate, Spacer, PageBreak, HRFlowable
        )
        from reportlab.lib.colors import HexColor
    except ImportError:
        print("[EIO] reportlab not available — generating text fallback PDF")
        _generate_text_fallback()
        return

    output_path = Path(OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "EIOTitle", parent=styles["Title"],
        fontSize=24, spaceAfter=12, textColor=HexColor("#1a365d")
    )
    subtitle_style = ParagraphStyle(
        "EIOSubtitle", parent=styles["Normal"],
        fontSize=14, spaceAfter=20, textColor=HexColor("#4a5568")
    )
    section_style = ParagraphStyle(
        "EIOSection", parent=styles["Heading1"],
        fontSize=16, spaceBefore=20, spaceAfter=10, textColor=HexColor("#2d3748")
    )
    body_style = ParagraphStyle(
        "EIOBody", parent=styles["Normal"],
        fontSize=10, spaceAfter=8, leading=16
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
    )

    story = []
    for i, (title, content) in enumerate(REPORT_SECTIONS):
        if i == 0:
            parts = content.split("\n") if isinstance(content, str) else [content]
            story.append(Paragraph(title, title_style))
            for part in parts:
                if part.strip():
                    story.append(Paragraph(part.strip(), subtitle_style))
        else:
            story.append(Paragraph(title, section_style))
            story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
            story.append(Spacer(1, 0.1 * inch))
            for line in content.strip().split("\n"):
                if line.strip():
                    story.append(Paragraph(line, body_style))
            story.append(PageBreak())

    doc.build(story)
    print(f"[EIO] Annual report PDF generated: {output_path}")


def _generate_text_fallback() -> None:
    """Plain text fallback when reportlab is not available."""
    output_path = Path(OUTPUT_PATH).with_suffix(".txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for title, content in REPORT_SECTIONS:
            f.write(f"\n{'='*60}\n{title}\n{'='*60}\n")
            f.write(content)
    print(f"[EIO] Annual report text fallback generated: {output_path}")


if __name__ == "__main__":
    generate()
