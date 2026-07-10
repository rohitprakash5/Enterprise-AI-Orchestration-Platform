"""
Generate all sample documents for the EIO local document repository.
Creates a realistic enterprise document set for RAG demonstration.

Documents generated:
  annual_report_2023.pdf       — already created by generate_annual_report.py
  q4_2023_earnings_release.txt — press release with Q4 earnings highlights
  investment_thesis_2024.txt   — analyst note on growth strategy
  risk_management_policy.txt   — enterprise risk policy document
  data_governance_policy.txt   — data governance and AI policy
  company_overview.txt         — corporate factsheet

Run: python eio/data/demo/generate_sample_documents.py
"""
from __future__ import annotations

import os
from pathlib import Path

DOCS_DIR = Path(os.getenv("EIO_LOCAL_STORAGE_PATH", "eio/data/demo/documents"))


def write(filename: str, content: str) -> None:
    path = DOCS_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip(), encoding="utf-8")
    print(f"  [EIO] Created: {path}")


def generate_all() -> None:
    print("[EIO] Generating sample enterprise documents...")

    # ── Q4 2023 Earnings Press Release ─────────────────────────────────────
    write("q4_2023_earnings_release.txt", """
APEX ANALYTICS CORP — Q4 2023 EARNINGS PRESS RELEASE
=====================================================
FOR IMMEDIATE RELEASE — February 8, 2024

SAN FRANCISCO — Apex Analytics Corp (NASDAQ: APEX) today reported financial results
for the fourth quarter and full year ended December 31, 2023.

Q4 2023 HIGHLIGHTS
-------------------
Total Revenue:    $58.2 million   (+25% year-over-year)
EBITDA:           $22.1 million   (38.0% margin)
Net Income:       $16.4 million   (+31% year-over-year)
Free Cash Flow:   $19.8 million   (+28% year-over-year)
ARR:              $164.8 million  (+35% year-over-year)

"Q4 2023 was our strongest quarter ever," said CEO Jonathan Caldwell.
"We added 47 new Fortune 500 customers and saw record expansion revenue
from our existing base. The momentum we have built in AI-powered analytics
positions us exceptionally well heading into 2024."

FULL YEAR 2023 HIGHLIGHTS
--------------------------
Full Year Revenue: $185.4 million (+22% year-over-year)
Full Year EBITDA:  $70.7 million  (38.1% margin)
Customer Count:    2,847          (+31% year-over-year)
Net Revenue Retention: 118%

REVENUE BY SEGMENT (Q4 2023)
------------------------------
Cloud Platform:       $23.1M  (+41% YoY)
Analytics Suite:      $15.4M  (+22% YoY)
Professional Services: $12.8M (+18% YoY)
Licensing:             $6.9M  (-5% YoY, planned wind-down)

2024 FULL YEAR GUIDANCE
------------------------
Revenue:        $218M — $230M   (+18% to +24% YoY)
EBITDA Margin:  38% — 41%
Free Cash Flow: $72M — $80M

CONFERENCE CALL
---------------
Apex Analytics will host a conference call on February 9, 2024 at 2:00 PM PT.
Dial-in: +1 (888) 555-0171  |  Webcast: investors.apexanalytics.com

About Apex Analytics Corp
Apex Analytics Corp provides cloud-native enterprise analytics software to
Fortune 2000 companies across financial services, healthcare, and manufacturing.
Founded in 2010, headquartered in San Francisco. Ticker: APEX (NASDAQ).
""")

    # ── Analyst Investment Thesis ──────────────────────────────────────────
    write("investment_thesis_2024.txt", """
APEX ANALYTICS CORP — INVESTMENT THESIS AND PRICE TARGET
=========================================================
Meridian Capital Research | Published: March 2024 | Rating: BUY | Target: $142

EXECUTIVE SUMMARY
-----------------
We initiate coverage of Apex Analytics Corp (APEX) with a BUY rating and
12-month price target of $142, implying 34% upside from current levels.

KEY INVESTMENT THESIS POINTS

1. AI Tailwind — Early Mover Advantage
   Apex is among the first enterprise analytics vendors to embed generative AI
   capabilities at the platform layer. Their AI orchestration roadmap, announced
   at their February 2024 Investor Day, positions them to capture the estimated
   $28B enterprise AI analytics market by 2027. The $45M committed R&D investment
   over 18 months gives them an 18-month lead over primary competitors.

2. Exceptional Unit Economics
   Net Revenue Retention of 118% means the company grows revenue from existing
   customers faster than churn. Dollar-based net expansion has been above 110%
   for 11 consecutive quarters. With a blended CAC payback of 14 months, the
   LTV:CAC ratio of approximately 8x is best-in-class for enterprise SaaS.

3. Durable Revenue Growth
   The shift from perpetual licensing to cloud subscription (ARR now $164.8M,
   +35% YoY) dramatically improves revenue predictability. We model 22% CAGR
   in ARR through 2026, supported by strong pipeline indicators and a TAM
   expansion into emerging markets (APAC, LatAm).

4. Operating Leverage
   EBITDA margins expanded from 29% in 2021 to 38% in 2023, with a clear path
   to 43%+ by 2026 as the cloud gross margin (currently 76%) scales on a fixed
   infrastructure base. We project $130M+ in free cash flow by 2026.

FINANCIAL PROJECTIONS (Meridian Estimates)
-------------------------------------------
               2023A    2024E    2025E    2026E
Revenue        $185M    $224M    $271M    $325M
YoY Growth      22%      21%      21%      20%
EBITDA          $71M     $90M    $116M    $146M
EBITDA Margin   38%      40%      43%      45%
EPS             $1.24    $1.61    $2.08    $2.67

RISKS TO THESIS
---------------
- Competitive pressure from Microsoft (Power BI) and Salesforce (Tableau)
- Macro slowdown reducing enterprise IT spend
- AI regulation (EU AI Act) requiring product modifications
- Key-person dependency on CEO Caldwell and CTO Patel

VALUATION
---------
At our $142 target, APEX trades at 16x 2025E EBITDA, a modest premium to
software peers (median 13x) justified by above-market growth and NRR.

Meridian Capital Research. For institutional clients only. See full disclosures.
""")

    # ── Risk Management Policy ─────────────────────────────────────────────
    write("risk_management_policy.txt", """
APEX ANALYTICS CORP — ENTERPRISE RISK MANAGEMENT POLICY
=========================================================
Document ID: ERM-2024-001 | Effective: January 1, 2024 | Owner: CFO Office

1. PURPOSE AND SCOPE
--------------------
This policy establishes the enterprise risk management (ERM) framework for
Apex Analytics Corp and all subsidiaries. It applies to all business units,
functional areas, and third-party relationships that could materially affect
the company's financial position, operations, or reputation.

2. RISK CATEGORIES
------------------

2.1 Strategic Risk
    Definition: Risks affecting the company's ability to execute its strategic plan.
    Key risks: AI regulation, competitive disruption, M&A integration.
    Tolerance: Low. Board-level oversight required for strategic risk acceptance.

2.2 Financial Risk
    Definition: Risks affecting revenue, cost structure, or capital position.
    Key risks: Customer concentration (top 50 customers = 28% of revenue),
    FX exposure (28% international revenue), liquidity risk.
    Tolerance: Medium. CFO approval required. Hedging policy in place for FX >$5M.

2.3 Technology and Cybersecurity Risk
    Definition: Risks from system failures, data breaches, or AI model failures.
    Key risks: Cloud infrastructure outage, data breach, AI model hallucination.
    Tolerance: Very Low. Zero tolerance for customer data exposure.
    Controls: SOC 2 Type II, ISO 27001, annual penetration testing, bug bounty.

2.4 AI Governance Risk
    Definition: Risks from AI model outputs causing incorrect business decisions.
    Key risks: Model hallucination in financial analytics, biased model outputs.
    Controls: Human review required for AI outputs in regulated industries.
    Policy: All AI-generated financial recommendations require analyst validation.

2.5 Compliance Risk
    Definition: Risks from non-compliance with laws and regulations.
    Key risks: GDPR, CCPA, SOX (as customers of financial institutions),
    EU AI Act, US Executive Order on AI.
    Tolerance: Zero. Legal team reviews all new product features.

3. RISK GOVERNANCE
------------------
Board Risk Committee: Quarterly reviews of top-10 enterprise risks.
Executive Risk Committee: Monthly reviews. Chaired by CEO.
Business Unit Risk Owners: Monthly reporting to CRO.

4. KEY RISK INDICATORS
----------------------
- Customer churn rate > 5% quarterly: Triggers escalation to Board
- Cybersecurity incident response time > 4 hours: SLA breach
- AI model accuracy degradation > 10%: Immediate product halt
- Revenue concentration (top 10 customers) > 35%: Diversification required

This policy is reviewed annually and updated as the risk landscape evolves.
""")

    # ── Data Governance Policy ─────────────────────────────────────────────
    write("data_governance_policy.txt", """
APEX ANALYTICS CORP — DATA GOVERNANCE AND AI POLICY
====================================================
Document ID: DG-AI-2024-003 | Version: 2.1 | Owner: Chief Data Officer

1. DATA CLASSIFICATION
----------------------
All data processed by Apex Analytics platforms must be classified as follows:

  Class 1 — Public:     Marketing materials, press releases, published reports.
  Class 2 — Internal:   Operational data, non-sensitive employee records.
  Class 3 — Confidential: Customer data, financial projections, IP.
  Class 4 — Restricted: PII, payment data, security credentials, trade secrets.

Class 3 and Class 4 data must be encrypted at rest (AES-256) and in transit (TLS 1.3).

2. AI MODEL GOVERNANCE
----------------------
All AI models deployed in Apex Analytics products must comply with:

2.1 Model Approval Process
    - All new AI models require Security, Legal, and Product review
    - Financial analytics models require additional accuracy validation
    - Models must achieve >95% accuracy on benchmark datasets before GA release
    - Model cards must be published for all production models

2.2 Explainability Requirements
    - All AI-generated insights must include confidence scores
    - Reasoning paths must be auditable and logged
    - Users must be informed when AI-generated content is presented
    - PII must be detected and redacted before AI model processing

2.3 Prohibited Uses
    - AI models must not make autonomous financial decisions without human review
    - AI outputs must not be presented as guaranteed facts
    - Customer data must not be used to train external AI models without consent

3. DATA RETENTION
-----------------
  Financial records:  7 years (SOX requirement)
  Customer data:      Duration of contract + 2 years
  AI inference logs:  1 year
  Audit logs:         5 years (tamper-evident storage required)

4. BREACH NOTIFICATION
----------------------
  Customer data breach: Notification within 72 hours (GDPR) / 30 days (CCPA)
  Financial data breach: Immediate Board notification + SEC disclosure if material

5. EMPLOYEE OBLIGATIONS
-----------------------
All employees must complete annual data governance training.
Violations of this policy may result in disciplinary action up to termination.

Approved by: Dr. Sarah Chen, Board Chairwoman | Jonathan Caldwell, CEO
""")

    # ── Company Overview ───────────────────────────────────────────────────
    write("company_overview.txt", """
APEX ANALYTICS CORP — CORPORATE FACT SHEET 2024
================================================

COMPANY PROFILE
---------------
Full Name:     Apex Analytics Corp
Ticker:        APEX (NASDAQ)
Founded:       2010, San Francisco, California
CEO:           Jonathan R. Caldwell
Employees:     1,240 (as of December 31, 2023)
Headquarters:  San Francisco, CA (HQ), New York, London, Singapore

BUSINESS DESCRIPTION
--------------------
Apex Analytics Corp provides cloud-native enterprise analytics software
and AI-powered data intelligence platforms to Fortune 2000 companies.

PRIMARY PRODUCTS
- Cloud Platform:       Multi-tenant SaaS analytics infrastructure ($82M ARR, 2023)
- Analytics Suite:      Business intelligence and reporting ($54M ARR, 2023)
- Professional Services: Implementation and consulting ($32M revenue, 2023)

PRIMARY MARKETS
- Financial Services (42% of revenue): Investment banks, asset managers, insurers
- Healthcare (16% of revenue): Hospital systems, pharma, payers
- Manufacturing (10% of revenue): Automotive, aerospace, industrial

GEOGRAPHIC SPLIT (2023)
- North America: 72% of revenue
- EMEA:          18% of revenue
- APAC:           8% of revenue
- LatAm:          2% of revenue

KEY METRICS (Full Year 2023)
-----------------------------
Total Revenue:             $185.4M  (+22% YoY)
Annual Recurring Revenue:  $164.8M  (+35% YoY)
EBITDA:                    $70.7M   (38.1% margin)
Net Income:                $52.8M
Free Cash Flow:            $61.3M
Net Revenue Retention:     118%
Customer Count:            2,847    (+31% YoY)
Gross Margin:              76% (Cloud); 58% (blended)

CERTIFICATIONS AND COMPLIANCE
- SOC 2 Type II (annual audit by Deloitte)
- ISO 27001 certified
- FedRAMP Moderate authorized
- GDPR and CCPA compliant
- Carbon-neutral operations (achieved Q3 2023)

INVESTOR RELATIONS
Quarterly earnings: February, May, August, November
Annual meeting: April
IR contact: investors@apexanalytics.com
""")

    print(f"[EIO] {len(list(DOCS_DIR.glob('*')))} documents in {DOCS_DIR}")
    print("[EIO] Sample document generation complete.")


if __name__ == "__main__":
    generate_all()
