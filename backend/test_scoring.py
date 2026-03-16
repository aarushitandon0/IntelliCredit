import sys
sys.path.insert(0, ".")

from src.ingestion.bank_parser import parse_bank_statement
from src.scoring.five_cs_model import compute_five_cs, scorecard_to_dict
from src.scoring.risk_adjuster import process_qualitative_inputs

# Step 1 — parse bank statement
bank = parse_bank_statement("../data/mock_bank/bank_statement_5yr.csv")

# Step 2 — simulate qualitative portal inputs
portal_inputs = {
    "factory_utilization_pct":    65,
    "collateral_verified":        True,
    "management_responsiveness":  "evasive",
    "machinery_condition":        "aged",
    "inventory_level":            "normal",
    "factory_activity":           "partial",
    "contradictions_noted":       True,
    "macro_outlook":              "negative",
    "references_checked":         False,
    "notes": "Factory found operating at 40% capacity. Several sections locked. Manager refused to explain circular transactions."
}

# Step 3 — process qualitative inputs
qualitative = process_qualitative_inputs(portal_inputs)

# Step 4 — mock financials (until pdf_parser runs on real doc)
mock_financials = {
    "revenue_from_operations_cr":  420.0,
    "profit_after_tax_cr":         12.5,
    "profit_before_tax_cr":        18.0,
    "finance_costs_cr":            22.0,
    "depreciation_cr":             14.0,
    "total_assets_cr":             180.0,
    "total_debt_cr":               120.0,
    "total_equity_cr":             60.0,
    "current_assets_cr":           95.0,
    "current_liabilities_cr":      88.0,
    "dscr_approximate":            0.92,
    "debt_equity":                 2.0,
    "current_ratio":               1.08,
    "net_profit_margin_pct":       2.9,
}

# Step 5 — mock research flags (until agent is built)
mock_research_flags = [
    {
        "type":        "DGGI_NOTICE",
        "severity":    "HIGH",
        "title":       "DGGI GST Evasion Notice — ₹12 Crore",
        "source":      "Financial Express, Aug 2024",
        "source_url":  "https://financialexpress.com/example",
        "score_impact": -2.0,
    },
    {
        "type":        "DIRECTOR_NPA",
        "severity":    "HIGH",
        "title":       "Director NPA — Rajesh Polymers Pvt Ltd, SBI 2022",
        "source":      "MCA Public Records",
        "source_url":  "https://mca.gov.in",
        "score_impact": -3.5,
    },
]

mock_sector_flags = [
    {
        "type":        "SECTOR_HEADWIND",
        "severity":    "MEDIUM",
        "title":       "Textile export sector under RBI stress watch",
        "source":      "Economic Times, Sep 2024",
        "score_impact": -1.5,
    }
]

# Step 6 — run Five Cs scoring
result = compute_five_cs(
    financials        = mock_financials,
    circular_trading  = bank["circular_trading"],
    gst_mismatch      = None,   # will add after gst_parser tested
    hidden_emis       = bank["hidden_emis"],
    cheque_bounces    = bank["cheque_bounces"],
    research_flags    = mock_research_flags,
    sector_flags      = mock_sector_flags,
    mca_charges       = [],
    auditor           = {},
    shareholding      = {},
    bank_limits       = [],
    rating            = {},
    qualitative       = qualitative,
    loan_requested_cr = 40.0,
    gst_limit_cr      = 105.0,
)

# Step 7 — print output
import json
print(json.dumps(scorecard_to_dict(result), indent=2))