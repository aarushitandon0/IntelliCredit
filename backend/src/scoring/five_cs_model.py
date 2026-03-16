"""
five_cs_model.py
────────────────
Transparent Five Cs scoring engine.

Every score line has three things attached:
  - the data point that drove it
  - the source document or URL it came from
  - the exact score adjustment applied

Weights:
  Character   20%
  Capacity    25%
  Capital     20%
  Collateral  20%
  Conditions  15%

Decision thresholds:
  75–100  →  APPROVED       — 25% of GST-verified turnover, Base + 1.5%
  55–74   →  CONDITIONAL    — 20% of GST-verified turnover, Base + 3.0%
  40–54   →  COMMITTEE      — Pending review
  < 40    →  REJECTED       — Nil limit
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math


# ─────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────

@dataclass
class ScoreLine:
    """A single scored sub-factor with full transparency."""
    pillar:      str
    sub_factor:  str
    data_point:  str          # exact value observed
    source:      str          # document name or URL
    base_score:  float        # 0–10 raw score
    adjustment:  float = 0.0  # any additional deduction/addition
    notes:       str = ""

    @property
    def final_score(self) -> float:
        return max(0.0, min(10.0, self.base_score + self.adjustment))


@dataclass
class PillarResult:
    name:       str
    weight:     float         # 0.0–1.0
    lines:      list[ScoreLine] = field(default_factory=list)

    @property
    def raw_score(self) -> float:
        # Only average lines with a non-zero base_score — adjustment lines
        # modify the base lines, they shouldn't be averaged as independent scores
        base_lines = [ln for ln in self.lines if ln.base_score > 0]
        if not base_lines:
            return 5.0
        total = sum(ln.final_score for ln in base_lines)
        # Apply all adjustment lines as flat deductions on top
        adjustments = sum(ln.adjustment for ln in self.lines if ln.base_score == 0)
        raw = (total / len(base_lines)) + adjustments
        return max(0.0, min(10.0, raw))
    
    @property
    def weighted_contribution(self) -> float:
        """Contribution to 0–100 composite."""
        return self.raw_score * self.weight * 10

    def add(self, sub_factor: str, data_point: str, source: str,
            base_score: float, adjustment: float = 0.0, notes: str = "") -> None:
        self.lines.append(ScoreLine(
            pillar=self.name, sub_factor=sub_factor,
            data_point=data_point, source=source,
            base_score=base_score, adjustment=adjustment, notes=notes,
        ))


@dataclass
class ScorecardResult:
    pillars:         list[PillarResult] = field(default_factory=list)
    decision:        str = ""
    composite_score: float = 0.0
    rationale:       str = ""
    recommended_limit_cr:  float = 0.0
    rate_premium_pct:      float = 0.0
    conditions_precedent:  list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# SCORING TABLES
# ─────────────────────────────────────────────────────────────

def _dscr_base(dscr: Optional[float]) -> float:
    if dscr is None: return 5.0
    if dscr >= 2.0:  return 9.0
    if dscr >= 1.5:  return 7.5
    if dscr >= 1.2:  return 6.0
    if dscr >= 1.0:  return 4.5
    return 2.0

def _de_base(de: Optional[float]) -> float:
    if de is None: return 5.0
    if de <= 1.0:  return 9.0
    if de <= 2.0:  return 7.5
    if de <= 3.0:  return 6.0
    if de <= 4.0:  return 4.0
    return 2.0

def _security_cover_base(cover: Optional[float]) -> float:
    if cover is None: return 5.0
    if cover >= 2.0:  return 9.0
    if cover >= 1.5:  return 7.5
    if cover >= 1.25: return 6.0
    if cover >= 1.0:  return 4.5
    return 2.0

def _rating_base(rating_score: Optional[float]) -> float:
    return rating_score if rating_score is not None else 5.0


# ─────────────────────────────────────────────────────────────
# PILLAR BUILDERS
# ─────────────────────────────────────────────────────────────

def build_character(
    research_flags:    list[dict],
    cheque_bounces:    dict,
    auditor:           dict,
    shareholding:      dict,
    qualitative:       dict,
) -> PillarResult:
    """
    research_flags: from research_agent output
    cheque_bounces: from bank_parser
    auditor:        from pdf_parser auditor section
    shareholding:   from pdf_parser parse_shareholding
    qualitative:    from risk_adjuster (officer portal)
    """
    p = PillarResult(name="Character", weight=0.20)

    # Base: clean slate 8.0, deductions applied below
    p.add("Base reputation", "No adverse history assumed until evidence found",
          "Prior assessment", base_score=8.0)

    # Research agent flags
    for flag in (research_flags or []):
        sev   = flag.get("severity", "LOW")
        title = flag.get("title") or flag.get("description", "Adverse finding")
        src   = flag.get("source_url") or flag.get("source", "Web research")
        adj   = flag.get("score_impact", 0)
        ftype = flag.get("type", "")

        # Map severity to score impact if not provided
        if adj == 0:
            adj = -3.5 if "NPA" in ftype or "NCLT" in ftype else -2.0 if sev == "HIGH" else -1.0

        p.add(
            sub_factor=f"Research flag: {ftype}",
            data_point=title,
            source=src,
            base_score=0,
            adjustment=adj,
            notes=f"Severity: {sev}",
        )

    # Cheque bounces
    bounce_count = cheque_bounces.get("count", 0) if cheque_bounces else 0
    if bounce_count > 2:
        p.add("Cheque dishonours", f"{bounce_count} bounces in 12 months",
              "Bank statement analysis", base_score=0, adjustment=-2.5,
              notes="RBI policy: >2 bounces is disqualifying under most bank credit policies")
    elif bounce_count > 0:
        p.add("Cheque dishonours", f"{bounce_count} bounce(s) in 12 months",
              "Bank statement analysis", base_score=0, adjustment=-1.0)

    # Going concern
    aud = (auditor or {}).get("auditor") or {}
    if aud.get("going_concern_flag"):
        p.add("Auditor qualification",
              aud.get("going_concern_text", "Going concern note in auditor report"),
              f"Auditor report — {aud.get('firm_name', 'Unknown firm')}",
              base_score=0, adjustment=-2.0,
              notes="Going concern qualification is a severe credit signal")

    # Promoter pledge
    sh = shareholding or {}
    ph = sh.get("promoter_holding") or {}
    pledge_pct = ph.get("pledged_pct") or 0
    if pledge_pct > 30:
        p.add("Promoter pledge", f"{pledge_pct}% shares pledged — margin call risk",
              "Shareholding pattern", base_score=0, adjustment=-2.0)
    elif pledge_pct > 10:
        p.add("Promoter pledge", f"{pledge_pct}% shares pledged",
              "Shareholding pattern", base_score=0, adjustment=-1.0)

    # Qualitative — management interview
    mgmt = (qualitative or {}).get("management_responsiveness", "cooperative").lower()
    if mgmt == "hostile":
        p.add("Management responsiveness", "Hostile during due diligence interview",
              "Credit officer site visit", base_score=0, adjustment=-3.0)
    elif mgmt == "evasive":
        p.add("Management responsiveness", "Evasive during due diligence interview",
              "Credit officer site visit", base_score=0, adjustment=-1.5)

    if (qualitative or {}).get("contradictions_noted"):
        p.add("Interview contradictions", "Material contradictions noted by credit officer",
              "Credit officer site visit", base_score=0, adjustment=-2.0)

    return p


def build_capacity(
    financials:        dict,
    circular_trading:  dict,
    gst_mismatch:      dict,
    hidden_emis:       dict,
    qualitative:       dict,
) -> PillarResult:
    p = PillarResult(name="Capacity", weight=0.25)

    fin   = financials or {}
    dscr  = fin.get("dscr_approximate")
    base  = _dscr_base(dscr)

    p.add("DSCR",
          f"DSCR = {dscr}" if dscr else "DSCR not computable — finance costs missing",
          "Annual report — P&L and balance sheet",
          base_score=base)

    # Circular trading
    ct = circular_trading or {}
    if ct.get("severity") == "HIGH":
        p.add("Circular trading",
              f"{ct.get('instance_count')} instances, ₹{ct.get('total_circular_cr')}Cr",
              "Bank statement analysis",
              base_score=0, adjustment=-3.0,
              notes="Revenue inflation without economic substance — GST-verified limit reduced to 50% factor")
    elif ct.get("severity") == "MEDIUM":
        p.add("Circular trading",
              f"{ct.get('instance_count')} instance(s) detected",
              "Bank statement analysis",
              base_score=0, adjustment=-1.5)

    # GST mismatch
    gm = gst_mismatch or {}
    if gm.get("severity") == "HIGH":
        p.add("GST–Bank mismatch",
              f"{gm.get('flagged_months')} months with >20% variance",
              "GST vs bank statement cross-check",
              base_score=0, adjustment=-2.5)
    elif gm.get("severity") == "MEDIUM":
        p.add("GST–Bank mismatch",
              f"{gm.get('flagged_months')} month(s) flagged",
              "GST vs bank statement cross-check",
              base_score=0, adjustment=-1.0)

    # Hidden EMIs
    emi = hidden_emis or {}
    emi_impact = emi.get("score_impact", 0)
    if emi_impact < 0:
        p.add("Undisclosed EMIs",
              f"{emi.get('count')} recurring debit pattern(s)",
              "Bank statement analysis",
              base_score=0, adjustment=emi_impact)

    # Factory utilization
    util = (qualitative or {}).get("factory_utilization_pct")
    if util is not None:
        if util < 50:
            p.add("Factory utilization", f"{util}% observed utilization",
                  "Credit officer site visit", base_score=0, adjustment=-1.5)
        elif util < 70:
            p.add("Factory utilization", f"{util}% observed utilization",
                  "Credit officer site visit", base_score=0, adjustment=-0.5)

    # Net profit margin
    npm = fin.get("net_profit_margin_pct")
    if npm is not None:
        if npm < 0:
            p.add("Net profit margin", f"{npm}% — loss-making",
                  "Annual report — P&L", base_score=0, adjustment=-1.5)
        elif npm < 3:
            p.add("Net profit margin", f"{npm}% — thin margins",
                  "Annual report — P&L", base_score=0, adjustment=-0.5)

    return p


def build_capital(
    financials:   dict,
    shareholding: dict,
) -> PillarResult:
    p = PillarResult(name="Capital", weight=0.20)

    fin = financials or {}
    de  = fin.get("debt_equity")
    p.add("Debt-to-equity",
          f"D/E = {de}" if de else "D/E not computable",
          "Annual report — balance sheet",
          base_score=_de_base(de))

    # Net worth trend
    nw = fin.get("total_equity_cr")
    if nw is not None:
        if nw < 0:
            p.add("Net worth", f"Negative net worth: ₹{nw}Cr",
                  "Annual report — balance sheet", base_score=0, adjustment=-3.0)
        elif nw < 10:
            p.add("Net worth", f"Low net worth: ₹{nw}Cr",
                  "Annual report — balance sheet", base_score=0, adjustment=-1.0)

    # Current ratio
    cr = fin.get("current_ratio")
    if cr is not None and cr < 1.0:
        p.add("Current ratio",
              f"Current ratio {cr} — cannot meet short-term obligations",
              "Annual report — balance sheet", base_score=0, adjustment=-1.5)

    # Promoter holding
    sh = shareholding or {}
    ph = (sh.get("promoter_holding") or {})
    pct = ph.get("total_pct")
    if pct is not None:
        if pct < 40:
            p.add("Promoter holding", f"{pct}% — low skin in the game",
                  "Shareholding pattern", base_score=0, adjustment=-1.5)
        elif pct >= 60:
            p.add("Promoter holding", f"{pct}% — strong promoter commitment",
                  "Shareholding pattern", base_score=0, adjustment=0.5)

    return p


def build_collateral(
    financials:     dict,
    bank_limits:    list[dict],
    mca_charges:    list[dict],
    qualitative:    dict,
) -> PillarResult:
    p = PillarResult(name="Collateral", weight=0.20)

    fin          = financials or {}
    total_assets = fin.get("total_assets_cr") or 0
    total_debt   = fin.get("total_debt_cr") or 1
    cover        = round(total_assets / total_debt, 2) if total_debt else None

    p.add("Security cover ratio",
          f"Cover = {cover}x" if cover else "Cover not computable",
          "Annual report — balance sheet",
          base_score=_security_cover_base(cover))

    # Immovable property bonus
    fixed = fin.get("fixed_assets_net_cr")
    if fixed and fixed > 0:
        p.add("Fixed assets", f"Net fixed assets ₹{fixed}Cr — includes immovable property",
              "Annual report — balance sheet", base_score=0, adjustment=0.5)

    # MCA charge registry — double pledging
    for charge in (mca_charges or []):
        p.add("Existing charge",
              charge.get("description", "Asset already pledged to another lender"),
              "MCA charge registry",
              base_score=0, adjustment=-4.0,
              notes="Double pledging — same asset offered as collateral elsewhere")

    # Physical verification
    qual = qualitative or {}
    if qual.get("collateral_verified") is False:
        p.add("Physical verification", "Collateral not found at stated location",
              "Credit officer site visit", base_score=0, adjustment=-3.0)
    elif qual.get("collateral_verified") is True:
        p.add("Physical verification", "Collateral verified at site",
              "Credit officer site visit", base_score=0, adjustment=0.0)

    # Machinery condition
    machinery = qual.get("machinery_condition", "").lower()
    if machinery == "defunct":
        p.add("Asset condition", "Machinery found defunct during site visit",
              "Credit officer site visit", base_score=0, adjustment=-1.5)
    elif machinery == "aged":
        p.add("Asset condition", "Machinery in aged/poor condition",
              "Credit officer site visit", base_score=0, adjustment=-1.0)

    return p


def build_conditions(
    sector_flags:  list[dict],
    rating:        dict,
    qualitative:   dict,
) -> PillarResult:
    p = PillarResult(name="Conditions", weight=0.15)

    # Base: neutral external environment
    p.add("Macro baseline", "External environment assessed as neutral",
          "Sector research", base_score=6.0)

    # Sector flags from research agent
    for flag in (sector_flags or []):
        adj = flag.get("score_impact", -1.0)
        p.add(
            sub_factor="Sector headwind",
            data_point=flag.get("title") or flag.get("description", "Sector risk"),
            source=flag.get("source_url") or flag.get("source", "Sector research"),
            base_score=0, adjustment=adj,
            notes=flag.get("severity", "MEDIUM"),
        )

    # External credit rating
    rt = rating or {}
    rs = rt.get("rating_score")
    if rs is not None:
        p.add("External credit rating",
              f"{rt.get('rating', 'Rated')} by {rt.get('agency', 'Rating agency')} — {rt.get('outlook', '')}",
              f"{rt.get('agency', 'Rating report')} {rt.get('rating_date', '')}",
              base_score=0, adjustment=rs - 6.0)   # neutral is 6.0

    # Officer macro assessment
    macro = (qualitative or {}).get("macro_outlook", "").lower()
    if macro == "negative":
        p.add("Macro outlook", "Credit officer assessment: negative macro environment",
              "Credit officer assessment", base_score=0, adjustment=-1.5)
    elif macro == "positive":
        p.add("Macro outlook", "Credit officer assessment: positive macro outlook",
              "Credit officer assessment", base_score=0, adjustment=0.5)

    return p


# ─────────────────────────────────────────────────────────────
# DECISION ENGINE
# ─────────────────────────────────────────────────────────────

def make_decision(
    composite: float,
    gst_limit_cr: float,
    loan_requested_cr: float,
    primary_reason: str,
    mitigating_factor: str,
) -> dict:
    if composite >= 75:
        decision = "APPROVED"
        limit    = gst_limit_cr * 1.0
        rate_premium = 1.5
        conditions = ["Maintain DSCR above 1.2x — quarterly reporting required",
                      "No additional borrowings without prior bank consent"]
    elif composite >= 55:
        decision = "CONDITIONAL"
        limit    = gst_limit_cr * 0.80
        rate_premium = 3.0
        conditions = ["Audited quarterly financials to be submitted",
                      "Additional collateral to be provided within 30 days",
                      "Promoter personal guarantee required"]
    elif composite >= 40:
        decision = "COMMITTEE REFERRAL"
        limit    = 0
        rate_premium = 0
        conditions = ["Matter referred to Credit Committee — pending review",
                      "Additional due diligence required"]
    else:
        decision = "REJECTED"
        limit    = 0
        rate_premium = 0
        conditions = []

    limit = min(limit, loan_requested_cr) if loan_requested_cr else limit

    # Plain-English rationale — the exact format from the problem statement
    if decision == "REJECTED":
        rationale = (
            f"Rejected due to {primary_reason}, "
            f"despite {mitigating_factor}."
        )
    elif decision == "CONDITIONAL":
        rationale = (
            f"Conditional approval recommended at ₹{limit:.1f}Cr — {primary_reason} noted, "
            f"partially offset by {mitigating_factor}. Additional conditions apply."
        )
    elif decision == "APPROVED":
        rationale = (
            f"Approved at ₹{limit:.1f}Cr. {mitigating_factor}. "
            f"Standard monitoring conditions apply."
        )
    else:
        rationale = (
            f"Referred to Credit Committee. {primary_reason} requires "
            f"senior review before decision."
        )

    return {
        "decision":              decision,
        "recommended_limit_cr":  round(limit, 2),
        "rate_premium_pct":      rate_premium,
        "rationale":             rationale,
        "conditions_precedent":  conditions,
    }


# ─────────────────────────────────────────────────────────────
# MASTER SCORER
# ─────────────────────────────────────────────────────────────

def compute_five_cs(
    financials:        dict = None,
    circular_trading:  dict = None,
    gst_mismatch:      dict = None,
    hidden_emis:       dict = None,
    cheque_bounces:    dict = None,
    research_flags:    list = None,
    sector_flags:      list = None,
    mca_charges:       list = None,
    auditor:           dict = None,
    shareholding:      dict = None,
    bank_limits:       list = None,
    rating:            dict = None,
    qualitative:       dict = None,
    loan_requested_cr: float = 0,
    gst_limit_cr:      float = 0,
) -> ScorecardResult:

    print("\n  ─── Five Cs Scoring ───")

    character  = build_character(research_flags, cheque_bounces, auditor, shareholding, qualitative)
    capacity   = build_capacity(financials, circular_trading, gst_mismatch, hidden_emis, qualitative)
    capital    = build_capital(financials, shareholding)
    collateral = build_collateral(financials, bank_limits, mca_charges, qualitative)
    conditions = build_conditions(sector_flags, rating, qualitative)

    pillars   = [character, capacity, capital, collateral, conditions]
    composite = sum(p.weighted_contribution for p in pillars)
    composite = round(min(100.0, max(0.0, composite)), 1)

    for p in pillars:
        print(f"  {p.name:<12} raw={p.raw_score:.1f}  contrib={p.weighted_contribution:.1f}  lines={len(p.lines)}")
    print(f"  COMPOSITE: {composite}")

    # Build rationale strings from top risk and top positive
    all_negatives = [
        ln for p in pillars for ln in p.lines if ln.adjustment < 0
    ]
    all_negatives.sort(key=lambda x: x.adjustment)
    top_risk = all_negatives[0].data_point if all_negatives else "identified risk factors"

    fin = financials or {}
    cover = None
    td = fin.get("total_debt_cr") or 1
    ta = fin.get("total_assets_cr")
    if ta:
        cover = round(ta / td, 2)

    mitigating = (
        f"adequate collateral cover of {cover}x" if cover and cover >= 1.5
        else f"stable GST flows of ₹{gst_limit_cr:.1f}Cr annually" if gst_limit_cr
        else "partial mitigating factors"
    )

    dec = make_decision(composite, gst_limit_cr, loan_requested_cr, top_risk, mitigating)

    result              = ScorecardResult()
    result.pillars      = pillars
    result.composite_score = composite
    result.decision     = dec["decision"]
    result.rationale    = dec["rationale"]
    result.recommended_limit_cr = dec["recommended_limit_cr"]
    result.rate_premium_pct     = dec["rate_premium_pct"]
    result.conditions_precedent = dec["conditions_precedent"]

    print(f"  Decision: {result.decision} | Limit: ₹{result.recommended_limit_cr}Cr | Rate: Base+{result.rate_premium_pct}%")
    print(f"  Rationale: {result.rationale}")

    return result


# ─────────────────────────────────────────────────────────────
# SERIALIZER — for API response / JSON output
# ─────────────────────────────────────────────────────────────

def scorecard_to_dict(result: ScorecardResult) -> dict:
    return {
        "composite_score":       result.composite_score,
        "decision":              result.decision,
        "recommended_limit_cr":  result.recommended_limit_cr,
        "rate_premium_pct":      result.rate_premium_pct,
        "rationale":             result.rationale,
        "conditions_precedent":  result.conditions_precedent,
        "pillars": {
            p.name: {
                "raw_score":             round(p.raw_score, 2),
                "weighted_contribution": round(p.weighted_contribution, 2),
                "weight_pct":            int(p.weight * 100),
                "score_lines": [
                    {
                        "sub_factor":  ln.sub_factor,
                        "data_point":  ln.data_point,
                        "source":      ln.source,
                        "base_score":  ln.base_score,
                        "adjustment":  ln.adjustment,
                        "final_score": ln.final_score,
                        "notes":       ln.notes,
                    }
                    for ln in p.lines
                ],
            }
            for p in result.pillars
        },
    }