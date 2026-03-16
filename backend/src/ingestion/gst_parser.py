"""
gst_parser.py
─────────────
Analyses GST filings: GSTR-3B (self-declared) and GSTR-2A (auto-populated).

Three detection algorithms — all deterministic Pandas, zero LLM:
  1. GST–Bank mismatch   — declared turnover vs actual bank credits (>20% variance)
  2. ITC fraud detection — GSTR-2A auto-populated vs GSTR-3B self-declared ITC delta
  3. Turnover spike      — monthly declared turnover vs 6-month rolling average (>40% spike)

Loan limit formula (applied here, used by scoring engine):
  Base limit           = GST-verified annual turnover × 25%
  Verification factor:
    0 mismatch months  → 1.00
    1–2 mismatch months→ 0.85
    3+ mismatch months → 0.65
    Circular trading   → 0.50  (applied by scoring engine, not here)

Expected GSTR-3B columns (case-insensitive):
  month | taxable_turnover | igst | cgst | sgst | itc_claimed
Expected GSTR-2A columns:
  month | supplier_igst | supplier_cgst | supplier_sgst | itc_available
"""

import os
import pandas as pd


# ─────────────────────────────────────────────────────────────
# COLUMN MAP
# ─────────────────────────────────────────────────────────────

GSTR3B_ALIASES = {
    "month":             ["month", "tax period", "period", "filing month"],
    "taxable_turnover":  ["taxable turnover", "taxable_turnover", "turnover", "outward supply", "total turnover"],
    "igst":              ["igst", "igst payable", "integrated tax"],
    "cgst":              ["cgst", "cgst payable", "central tax"],
    "sgst":              ["sgst", "sgst payable", "state tax", "utgst"],
    "itc_claimed":       ["itc claimed", "itc_claimed", "input tax credit", "itc availed", "total itc"],
}

GSTR2A_ALIASES = {
    "month":             ["month", "tax period", "period"],
    "supplier_igst":     ["igst", "supplier igst", "igst available"],
    "supplier_cgst":     ["cgst", "supplier cgst", "cgst available"],
    "supplier_sgst":     ["sgst", "supplier sgst", "sgst available"],
    "itc_available":     ["itc available", "eligible itc", "total itc", "itc_available"],
}


def _map_cols(df: pd.DataFrame, aliases: dict) -> pd.DataFrame:
    lower_map = {c.lower().strip(): c for c in df.columns}
    rename = {}
    for std, opts in aliases.items():
        for opt in opts:
            if opt.lower() in lower_map:
                rename[lower_map[opt.lower()]] = std
                break
    return df.rename(columns=rename)


def _clean_amount(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(r"[₹,$,\s,]", "", regex=True)
        .replace({"": "0", "nan": "0", "-": "0"})
        .astype(float)
        .fillna(0)
    )


def _parse_month(series: pd.Series) -> pd.Series:
    """Handles formats: Apr-2024, April 2024, 04/2024, 2024-04"""
    return pd.to_datetime(series, format="mixed", dayfirst=True, errors="coerce").dt.to_period("M")


# ─────────────────────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────────────────────

def load_gstr3b(file_path: str) -> pd.DataFrame:
    ext = os.path.splitext(file_path)[1].lower()
    df = pd.read_excel(file_path) if ext in (".xlsx", ".xls") else pd.read_csv(file_path)
    df = df.dropna(how="all").reset_index(drop=True)
    df = _map_cols(df, GSTR3B_ALIASES)

    required = ["month", "taxable_turnover"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"GSTR-3B missing columns: {missing}. Available: {list(df.columns)}")

    df["month"]            = _parse_month(df["month"])
    df["taxable_turnover"] = _clean_amount(df["taxable_turnover"])

    for col in ["igst", "cgst", "sgst", "itc_claimed"]:
        if col in df.columns:
            df[col] = _clean_amount(df[col])
        else:
            df[col] = 0.0

    df["total_tax"] = df["igst"] + df["cgst"] + df["sgst"]
    return df.sort_values("month").reset_index(drop=True)


def load_gstr2a(file_path: str) -> pd.DataFrame:
    ext = os.path.splitext(file_path)[1].lower()
    df = pd.read_excel(file_path) if ext in (".xlsx", ".xls") else pd.read_csv(file_path)
    df = df.dropna(how="all").reset_index(drop=True)
    df = _map_cols(df, GSTR2A_ALIASES)

    df["month"] = _parse_month(df["month"])

    for col in ["supplier_igst", "supplier_cgst", "supplier_sgst", "itc_available"]:
        if col in df.columns:
            df[col] = _clean_amount(df[col])
        else:
            df[col] = 0.0

    if "itc_available" not in df.columns or df["itc_available"].sum() == 0:
        df["itc_available"] = df["supplier_igst"] + df["supplier_cgst"] + df["supplier_sgst"]

    return df.sort_values("month").reset_index(drop=True)


# ─────────────────────────────────────────────────────────────
# ALGORITHM 1 — GST vs BANK MISMATCH
# ─────────────────────────────────────────────────────────────

MISMATCH_THRESHOLD_PCT = 20     # >20% variance is a flag
MISMATCH_HIGH_MONTHS   = 3      # 3+ months = HIGH severity

def detect_gst_bank_mismatch(gstr3b: pd.DataFrame, bank_credits: dict) -> dict:
    """
    bank_credits: {Period('2024-06','M'): float_cr, ...}
    Provided by calling code that passes monthly bank summary from bank_parser.
    """
    rows = []
    for _, row in gstr3b.iterrows():
        declared = row["taxable_turnover"]
        actual   = bank_credits.get(row["month"], None)

        if actual is None or actual == 0:
            rows.append({
                "month":           str(row["month"]),
                "gst_declared_cr": round(declared, 2),
                "bank_credits_cr": None,
                "variance_pct":    None,
                "flagged":         False,
                "note":            "Bank data not available for this month",
            })
            continue

        if declared == 0:
            rows.append({
                "month":           str(row["month"]),
                "gst_declared_cr": 0,
                "bank_credits_cr": round(actual, 2),
                "variance_pct":    None,
                "flagged":         False,
                "note":            "No GST declared — possible nil return",
            })
            continue

        variance_pct = ((declared - actual) / actual) * 100
        flagged      = abs(variance_pct) > MISMATCH_THRESHOLD_PCT

        rows.append({
            "month":           str(row["month"]),
            "gst_declared_cr": round(declared, 2),
            "bank_credits_cr": round(actual, 2),
            "variance_pct":    round(variance_pct, 1),
            "flagged":         flagged,
            "direction":       "OVER-DECLARED" if variance_pct > 0 else "UNDER-DECLARED",
        })

    flagged_months = sum(1 for r in rows if r.get("flagged"))
    severity = (
        "HIGH"   if flagged_months >= MISMATCH_HIGH_MONTHS else
        "MEDIUM" if flagged_months >= 1 else
        "CLEAR"
    )

    # Verification factor for loan limit
    verification_factor = (
        1.00 if flagged_months == 0 else
        0.85 if flagged_months <= 2 else
        0.65
    )

    score_impact = (
        -2.5 if severity == "HIGH" else
        -1.0 if severity == "MEDIUM" else 0
    )

    print(f"  GST-Bank mismatch: {flagged_months} month(s) flagged | {severity} | factor={verification_factor}")
    return {
        "monthly_comparison":   rows,
        "flagged_months":       flagged_months,
        "severity":             severity,
        "verification_factor":  verification_factor,
        "score_impact":         score_impact,
        "flag_type":            "GST_BANK_MISMATCH",
        "description":          (
            f"{flagged_months} month(s) show >20% variance between GST-declared "
            f"turnover and actual bank credits. Verification factor reduced to {verification_factor}."
            if flagged_months else
            "GST declared turnover reconciles cleanly with bank credits."
        ),
    }


# ─────────────────────────────────────────────────────────────
# ALGORITHM 2 — ITC FRAUD (GSTR-2A vs GSTR-3B DELTA)
# ─────────────────────────────────────────────────────────────

ITC_DELTA_THRESHOLD_PCT = 15    # >15% more ITC claimed than supplier declared
ITC_FLAG_MONTHS         = 2     # 2+ months = HIGH

def detect_itc_fraud(gstr3b: pd.DataFrame, gstr2a: pd.DataFrame) -> dict:
    """
    GSTR-2A is auto-populated from supplier declarations.
    GSTR-3B is self-declared.
    When claimed ITC > available ITC by >15%, it signals phantom purchases.
    """
    if gstr2a is None or gstr2a.empty:
        return {
            "available": False,
            "flag_type": "ITC_FRAUD",
            "severity":  "UNKNOWN",
            "description": "GSTR-2A not provided — ITC cross-check not possible.",
        }

    merged = pd.merge(
        gstr3b[["month", "itc_claimed"]],
        gstr2a[["month", "itc_available"]],
        on="month", how="inner"
    )

    rows = []
    for _, row in merged.iterrows():
        claimed   = row["itc_claimed"]
        available = row["itc_available"]

        if available == 0:
            rows.append({"month": str(row["month"]), "claimed": claimed, "available": available, "delta_pct": None, "flagged": False})
            continue

        delta_pct = ((claimed - available) / available) * 100
        flagged   = delta_pct > ITC_DELTA_THRESHOLD_PCT

        rows.append({
            "month":     str(row["month"]),
            "itc_claimed_cr":   round(claimed, 2),
            "itc_available_cr": round(available, 2),
            "delta_pct":        round(delta_pct, 1),
            "flagged":          flagged,
        })

    flagged_months = sum(1 for r in rows if r.get("flagged"))
    severity = (
        "HIGH"   if flagged_months >= ITC_FLAG_MONTHS else
        "MEDIUM" if flagged_months == 1 else
        "CLEAR"
    )
    score_impact = -2.0 if severity == "HIGH" else -1.0 if severity == "MEDIUM" else 0

    print(f"  ITC fraud check: {flagged_months} month(s) flagged | {severity}")
    return {
        "monthly_delta":  rows,
        "flagged_months": flagged_months,
        "severity":       severity,
        "score_impact":   score_impact,
        "flag_type":      "ITC_FRAUD",
        "description":    (
            f"{flagged_months} month(s) show ITC claimed materially exceeding "
            f"supplier-declared ITC in GSTR-2A. Possible phantom purchases or circular invoicing."
            if flagged_months else
            "ITC claims reconcile with GSTR-2A supplier declarations."
        ),
    }


# ─────────────────────────────────────────────────────────────
# ALGORITHM 3 — TURNOVER SPIKE
# ─────────────────────────────────────────────────────────────

SPIKE_THRESHOLD_PCT = 40    # >40% above rolling average

def detect_turnover_spike(gstr3b: pd.DataFrame) -> dict:
    """
    Detect abnormal spikes in declared turnover vs 6-month rolling average.
    Common revenue manipulation signal in Indian mid-market companies.
    """
    df = gstr3b.copy()
    df["rolling_avg"] = df["taxable_turnover"].rolling(6, min_periods=3).mean().shift(1)
    df = df.dropna(subset=["rolling_avg"])

    rows = []
    for _, row in df.iterrows():
        if row["rolling_avg"] == 0:
            continue
        spike_pct = ((row["taxable_turnover"] - row["rolling_avg"]) / row["rolling_avg"]) * 100
        flagged   = spike_pct > SPIKE_THRESHOLD_PCT
        rows.append({
            "month":          str(row["month"]),
            "declared_cr":    round(row["taxable_turnover"], 2),
            "rolling_avg_cr": round(row["rolling_avg"], 2),
            "spike_pct":      round(spike_pct, 1),
            "flagged":        flagged,
        })

    flagged_months = sum(1 for r in rows if r.get("flagged"))
    severity = "HIGH" if flagged_months >= 2 else "MEDIUM" if flagged_months == 1 else "CLEAR"

    print(f"  Turnover spike: {flagged_months} month(s) flagged | {severity}")
    return {
        "monthly_analysis": rows,
        "flagged_months":   flagged_months,
        "severity":         severity,
        "score_impact":     -1.0 if severity == "HIGH" else -0.5 if severity == "MEDIUM" else 0,
        "flag_type":        "TURNOVER_SPIKE",
        "description":      (
            f"{flagged_months} month(s) show declared turnover >40% above the 6-month rolling average."
            if flagged_months else "No abnormal turnover spikes detected."
        ),
    }


# ─────────────────────────────────────────────────────────────
# LOAN LIMIT CALCULATOR
# ─────────────────────────────────────────────────────────────

def compute_gst_verified_limit(
    gstr3b: pd.DataFrame,
    verification_factor: float,
    circular_trading: bool = False,
    loan_requested_cr: float = 0,
    existing_limits_cr: float = 0,
) -> dict:
    annual_turnover_cr = gstr3b["taxable_turnover"].sum()
    factor = 0.50 if circular_trading else verification_factor
    base_limit_cr     = annual_turnover_cr * 0.25
    adjusted_limit_cr = base_limit_cr * factor
    final_limit_cr    = max(0, adjusted_limit_cr - existing_limits_cr)
    if loan_requested_cr:
        final_limit_cr = min(final_limit_cr, loan_requested_cr)

    return {
        "annual_gst_turnover_cr":   round(annual_turnover_cr, 2),
        "base_limit_cr":            round(base_limit_cr, 2),
        "verification_factor":      factor,
        "circular_trading_applied": circular_trading,
        "adjusted_limit_cr":        round(adjusted_limit_cr, 2),
        "existing_limits_deducted_cr": existing_limits_cr,
        "final_recommended_limit_cr": round(final_limit_cr, 2),
        "loan_requested_cr":        loan_requested_cr,
        "shortfall_cr":             round(max(0, loan_requested_cr - final_limit_cr), 2),
    }


# ─────────────────────────────────────────────────────────────
# MASTER PARSER
# ─────────────────────────────────────────────────────────────

def parse_gst(
    gstr3b_path: str,
    gstr2a_path: str = None,
    bank_monthly_credits: dict = None,
    loan_requested_cr: float = 0,
    existing_limits_cr: float = 0,
    circular_trading_detected: bool = False,
) -> dict:
    """
    bank_monthly_credits: optional dict {Period: float} from bank_parser summary.
    If not provided, GST-Bank mismatch check is skipped.
    """
    print(f"\nParsing GST filings: {os.path.basename(gstr3b_path)}")

    gstr3b = load_gstr3b(gstr3b_path)
    print(f"  GSTR-3B: {len(gstr3b)} months | {gstr3b['month'].min()} → {gstr3b['month'].max()}")
    print(f"  Total declared turnover: ₹{gstr3b['taxable_turnover'].sum():.2f}Cr")

    gstr2a = None
    if gstr2a_path and os.path.exists(gstr2a_path):
        gstr2a = load_gstr2a(gstr2a_path)
        print(f"  GSTR-2A: {len(gstr2a)} months loaded")

    # Run algorithms
    mismatch = detect_gst_bank_mismatch(gstr3b, bank_monthly_credits or {})
    itc      = detect_itc_fraud(gstr3b, gstr2a)
    spike    = detect_turnover_spike(gstr3b)

    # Loan limit
    limit = compute_gst_verified_limit(
        gstr3b,
        verification_factor=mismatch["verification_factor"],
        circular_trading=circular_trading_detected,
        loan_requested_cr=loan_requested_cr,
        existing_limits_cr=existing_limits_cr,
    )

    # Aggregate flags
    all_flags = []
    for result in [mismatch, itc, spike]:
        if result.get("severity") not in ("CLEAR", "UNKNOWN", None):
            all_flags.append({
                "type":         result["flag_type"],
                "severity":     result["severity"],
                "description":  result["description"],
                "score_impact": result.get("score_impact", 0),
            })

    total_score_impact = sum(f["score_impact"] for f in all_flags)

    print(f"\n  ─── GST Analysis Summary ───")
    print(f"  GST-verified limit : ₹{limit['final_recommended_limit_cr']}Cr")
    print(f"  Verification factor: {limit['verification_factor']}")
    print(f"  Score impact       : {total_score_impact} pts")
    print(f"  Active flags       : {len(all_flags)}")

    return {
        "_source_file":          os.path.basename(gstr3b_path),
        "gst_bank_mismatch":     mismatch,
        "itc_fraud":             itc,
        "turnover_spike":        spike,
        "loan_limit":            limit,
        "risk_flags":            all_flags,
        "total_score_impact":    total_score_impact,
    }