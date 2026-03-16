"""
bank_parser.py
──────────────
Analyses 12-month bank statements (CSV / Excel).

Five detection algorithms — all deterministic Pandas, zero LLM:
  1. Circular trading    — credit ≥ ₹50L matched by debit ±5% within 72 hrs
  2. Hidden EMIs         — fixed recurring debits ≥ ₹10L appearing 3+ months
  3. Cheque bounces      — dishonour keywords in transaction descriptions
  4. Excess cash         — single cash deposit > ₹10L (PMLA / FEMA flag)
  5. Related-party debits— large outflows to promoter / group entities

Unit assumption: CSV amounts are in RAW RUPEES.
All amounts are divided by 10,000,000 on load → converted to Crores.
"""

import os
import pandas as pd
from datetime import timedelta


# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────

RUPEES_TO_CR = 10_000_000   # 1 Crore = 10,000,000 rupees

COLUMN_ALIASES = {
    "date":        ["date", "txn date", "transaction date", "value date", "posting date"],
    "description": ["description", "narration", "particulars", "remarks", "details"],
    "credit":      ["credit", "credit amount", "deposits", "cr", "cr amount"],
    "debit":       ["debit", "debit amount", "withdrawals", "dr", "dr amount"],
    "balance":     ["balance", "closing balance", "running balance"],
}

# Legitimate debits excluded from circular trading
EXCLUDE_FROM_CIRCULAR = [
    "salary", "payroll", "staff", "wages",
    "rent", "lease",
    "tds", "gst payment", "gstin", "advance tax", "income tax",
    "electricity", "msedcl", "bescom", "tata power",
    "insurance", "lic premium",
    "loan emi", "nach debit", "emi", "repayment",
    "promoter capital", "capital infusion",
    "eclgs",
]

BOUNCE_KEYWORDS = [
    "return", "dishonour", "dishonor", "bounce", "bounced",
    "insufficient", "inward return", "outward return",
    "chq ret", "ecs ret", "nach ret", "mandate return",
    "cheque return", "ecs return", "dishonoured",
]

CASH_KEYWORDS = [
    "cash deposit", "cash cr", "cash credit", "cdm", "branch counter",
]

RELATED_PARTY_KEYWORDS = [
    "intercorp", "intercorporate", "intercompany",
    "promoter", "holdings pvt", "holding pvt", "group company",
    "director loan", "related party",
]

KNOWN_EMI_LENDERS = [
    "punjab national bank", "pnb", "eclgs",
]


# ─────────────────────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────────────────────

def _map_columns(df: pd.DataFrame) -> pd.DataFrame:
    lower_map = {c.lower().strip(): c for c in df.columns}
    rename = {}
    for std, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_map:
                rename[lower_map[alias]] = std
                break
    df = df.rename(columns=rename)
    missing = [c for c in ["date", "description", "credit", "debit"] if c not in df.columns]
    if missing:
        raise ValueError(f"Could not find columns: {missing}. Available: {list(df.columns)}")
    return df


def _clean_amount(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(r"[₹,$,\s,]", "", regex=True)
        .str.replace(r"[()]", "", regex=True)
        .replace({"": "0", "nan": "0", "-": "0", "--": "0"})
        .astype(float)
        .fillna(0)
    )

def _detect_unit(df: pd.DataFrame) -> float:
    """Auto-detect unit from balance column magnitude."""
    sample = df["balance"].replace(0, pd.NA).dropna()
    if sample.empty:
        return 1 / 1_00_00_000   # default: assume rupees
    median_bal = sample.median()
    if median_bal > 1_00_00_000:
        return 1 / 1_00_00_000   # raw rupees → crores
    elif median_bal > 1_00_000:
        return 1 / 100            # lakhs → crores
    else:
        return 1.0                # already in crores


def load_bank_statement(file_path: str) -> pd.DataFrame:
    ext = os.path.splitext(file_path)[1].lower()
    df  = pd.read_excel(file_path) if ext in (".xlsx", ".xls") else pd.read_csv(file_path)
    df  = df.dropna(how="all").reset_index(drop=True)

    if df.iloc[0].astype(str).str.contains("date|narration|amount", case=False).any():
        df = df.iloc[1:].reset_index(drop=True)

    df = _map_columns(df)

    # ── UNIT CONVERSION: raw rupees → crores ──────────────────
    df["credit"]  = _clean_amount(df["credit"])
    df["debit"]   = _clean_amount(df["debit"])
    df["balance"] = _clean_amount(df["balance"]) if "balance" in df.columns else 0

    factor = _detect_unit(df)
    df["credit"]  = df["credit"]  * factor
    df["debit"]   = df["debit"]   * factor
    df["balance"] = df["balance"] * factor
    print(f"  Unit auto-detected: factor={factor}")

    df["date"]        = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df["description"] = df["description"].astype(str).str.strip().str.lower()
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────
# 1. CIRCULAR TRADING
# ─────────────────────────────────────────────────────────────

CIRCULAR_THRESHOLD_CR  = 0.50   # ₹50L
CIRCULAR_MATCH_PCT     = 0.05
CIRCULAR_WINDOW_HOURS  = 72
CIRCULAR_MIN_INSTANCES = 3


def detect_circular_trading(df: pd.DataFrame) -> dict:
    credits = df[df["credit"] >= CIRCULAR_THRESHOLD_CR].copy()

    debits = df[df["debit"] >= CIRCULAR_THRESHOLD_CR].copy()
    debits = debits[~debits["description"].apply(
        lambda x: any(kw in x for kw in EXCLUDE_FROM_CIRCULAR)
    )].copy()

    instances        = []
    used_debit_idx   = set()

    for _, cr in credits.iterrows():
        window_end = cr["date"] + timedelta(hours=CIRCULAR_WINDOW_HOURS)
        lo, hi     = cr["credit"] * (1 - CIRCULAR_MATCH_PCT), cr["credit"] * (1 + CIRCULAR_MATCH_PCT)

        matched = debits[
            (debits["date"] > cr["date"]) &
            (debits["date"] <= window_end) &
            (debits["debit"] >= lo) &
            (debits["debit"] <= hi) &
            (~debits.index.isin(used_debit_idx))
        ]

        for idx, dr in matched.iterrows():
            gap_hrs   = (dr["date"] - cr["date"]).total_seconds() / 3600
            match_pct = (1 - abs(cr["credit"] - dr["debit"]) / cr["credit"]) * 100
            instances.append({
                "credit_date":      str(cr["date"].date()),
                "credit_amount_cr": round(cr["credit"], 2),
                "credit_desc":      cr["description"],
                "debit_date":       str(dr["date"].date()),
                "debit_amount_cr":  round(dr["debit"], 2),
                "debit_desc":       dr["description"],
                "gap_hours":        round(gap_hrs, 1),
                "match_pct":        round(match_pct, 1),
            })
            used_debit_idx.add(idx)
            break

    total_cr     = sum(i["credit_amount_cr"] for i in instances)
    severity     = "HIGH" if len(instances) >= CIRCULAR_MIN_INSTANCES else "MEDIUM" if instances else "CLEAR"
    score_impact = -3.0 if severity == "HIGH" else -1.5 if severity == "MEDIUM" else 0

    print(f"  Circular trading: {len(instances)} instance(s) | ₹{total_cr:.2f}Cr | {severity}")
    return {
        "instances":         instances,
        "instance_count":    len(instances),
        "total_circular_cr": round(total_cr, 2),
        "severity":          severity,
        "score_impact":      score_impact,
        "flag_type":         "CIRCULAR_TRADING",
        "description": (
            f"{len(instances)} circular trading instance(s). ₹{total_cr:.2f}Cr apparent "
            f"revenue cycling in and out within {CIRCULAR_WINDOW_HOURS} hours."
            if instances else "No circular trading detected."
        ),
    }


# ─────────────────────────────────────────────────────────────
# 2. HIDDEN EMIs
# ─────────────────────────────────────────────────────────────

EMI_THRESHOLD_CR   = 0.10   # ₹10L
EMI_MIN_RECURRENCE = 3
EMI_SCORE_CAP      = -3.0


def detect_hidden_emis(df: pd.DataFrame) -> dict:
    debits = df[df["debit"] >= EMI_THRESHOLD_CR].copy()
    debits["month"] = debits["date"].dt.to_period("M")

    # Only look at EMI-like descriptions
    emi_mask = debits["description"].apply(
        lambda x: (
            any(kw in x for kw in ["nach debit", "loan emi", "emi", "repayment", "loan a/c"])
            and not any(kw in x for kw in KNOWN_EMI_LENDERS)
        )
    )
    emi_debits = debits[emi_mask].copy()

    emi_debits["bucket"] = (emi_debits["debit"] / 0.05).round() * 0.05

    grouped = emi_debits.groupby("bucket").agg(
        count=("debit", "count"),
        months=("month", lambda x: x.nunique()),
        avg_amount=("debit", "mean"),
        sample_desc=("description", "first"),
        first_seen=("date", "min"),
    ).reset_index()

    hidden = grouped[grouped["months"] >= EMI_MIN_RECURRENCE].sort_values("avg_amount", ascending=False)

    emis = []
    for _, row in hidden.iterrows():
        sev = "HIGH" if row["months"] >= 6 else "MEDIUM"
        emis.append({
            "avg_amount_cr":    round(row["avg_amount"], 2),
            "months_seen":      int(row["months"]),
            "occurrence_count": int(row["count"]),
            "severity":         sev,
            "first_seen":       str(row["first_seen"].date()),
            "sample_desc":      row["sample_desc"],
            "score_impact":     -1.0 if sev == "HIGH" else -0.5,
        })

    raw_impact   = sum(e["score_impact"] for e in emis)
    total_impact = max(EMI_SCORE_CAP, raw_impact)

    print(f"  Hidden EMIs: {len(emis)} undisclosed pattern(s) | impact = {total_impact}")
    return {
        "patterns":    emis,
        "count":       len(emis),
        "flag_type":   "HIDDEN_EMI",
        "severity":    "HIGH" if any(e["severity"] == "HIGH" for e in emis) else
                       "MEDIUM" if emis else "CLEAR",
        "score_impact": total_impact,
        "description": (
            f"{len(emis)} undisclosed recurring EMI pattern(s) detected."
            if emis else "No undisclosed EMI patterns detected."
        ),
    }


# ─────────────────────────────────────────────────────────────
# 3. CHEQUE BOUNCES
# ─────────────────────────────────────────────────────────────

BOUNCE_HIGH_VALUE_CR = 1.0   # ₹1Cr+


def detect_cheque_bounces(df: pd.DataFrame) -> dict:
    mask    = df["description"].apply(lambda x: any(kw in x for kw in BOUNCE_KEYWORDS))
    bounces = df[mask].copy()

    records = []
    for _, row in bounces.iterrows():
        amount = max(row["credit"], row["debit"])
        sev    = "HIGH" if amount >= BOUNCE_HIGH_VALUE_CR else "MEDIUM"
        records.append({
            "date":        str(row["date"].date()),
            "description": row["description"],
            "amount_cr":   round(amount, 2),
            "severity":    sev,
        })

    count    = len(records)
    severity = (
        "HIGH"   if count > 2 or any(r["severity"] == "HIGH" for r in records) else
        "MEDIUM" if count > 0 else "CLEAR"
    )
    score_impact = -2.5 if severity == "HIGH" else -1.0 if severity == "MEDIUM" else 0

    print(f"  Cheque bounces: {count} detected | {severity}")
    return {
        "records":      records,
        "count":        count,
        "flag_type":    "CHEQUE_BOUNCE",
        "severity":     severity,
        "score_impact": score_impact,
        "description": (
            f"{count} cheque/instrument dishonour(s) detected. "
            f">2 bounces in 12 months is disqualifying per RBI policy."
            if records else "No cheque dishonours detected."
        ),
    }


# ─────────────────────────────────────────────────────────────
# 4. EXCESS CASH DEPOSITS
# ─────────────────────────────────────────────────────────────

CASH_THRESHOLD_CR  = 0.10   # ₹10L
CASH_HIGH_TOTAL_CR = 0.50   # ₹50L total


def detect_excess_cash(df: pd.DataFrame) -> dict:
    mask      = df["description"].apply(lambda x: any(kw in x for kw in CASH_KEYWORDS)) \
                & (df["credit"] >= CASH_THRESHOLD_CR)
    cash_rows = df[mask].copy()
    total     = cash_rows["credit"].sum()

    records = [{
        "date":        str(r["date"].date()),
        "amount_cr":   round(r["credit"], 2),
        "description": r["description"],
    } for _, r in cash_rows.iterrows()]

    severity     = "HIGH" if total >= CASH_HIGH_TOTAL_CR else "MEDIUM" if records else "CLEAR"
    score_impact = -1.0 if severity == "HIGH" else -0.5 if severity == "MEDIUM" else 0

    print(f"  Excess cash: {len(records)} transaction(s) | ₹{total:.2f}Cr | {severity}")
    return {
        "transactions":  records,
        "count":         len(records),
        "total_cash_cr": round(total, 2),
        "flag_type":     "EXCESS_CASH",
        "severity":      severity,
        "score_impact":  score_impact,
        "description": (
            f"₹{total:.2f}Cr in large cash deposits ({len(records)} transactions). "
            f"PMLA/FEMA compliance risk for lending institution."
            if records else "No large cash deposits detected."
        ),
    }


# ─────────────────────────────────────────────────────────────
# 5. RELATED PARTY / INTERCORPORATE TRANSACTIONS
# ─────────────────────────────────────────────────────────────

RELATED_PARTY_MIN_CR = 1.0   # ₹1Cr+


def detect_related_party(df: pd.DataFrame, 
                          director_names: list[str] = None,
                          company_name: str = "") -> dict:
    """
    director_names: passed from pdf_parser output e.g. ["Amit Shah", "Rajesh Gupta"]
    Works on any dataset — no hardcoded names.
    """
    RELATED_KEYWORDS = [
        "intercorp", "holdings pvt", "family trust",
        "promoter", "related party", "group company",
        "director loan", "personal a/c", "proprietor"
    ]
    
    dynamic_keywords = []
    if director_names:
        for name in director_names:
            parts = name.lower().split()
            dynamic_keywords += parts   # "Amit Shah" → ["amit", "shah"]
    if company_name:
        word = company_name.lower().split()[0]  # "Rajesh Exports" → "rajesh"
        dynamic_keywords.append(word)

    all_keywords = RELATED_KEYWORDS + dynamic_keywords
    
    mask = df["description"].apply(
        lambda x: any(kw in str(x).lower() for kw in all_keywords)
    ) & (df["debit"] > 0)


# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────

def compute_bank_summary(df: pd.DataFrame) -> dict:
    monthly = df.groupby(df["date"].dt.to_period("M")).agg(
        total_credits_cr=("credit", "sum"),
        total_debits_cr=("debit",  "sum"),
        txn_count=("date",         "count"),
    ).reset_index()
    monthly["month"] = monthly["date"].astype(str)

    return {
        "total_credits_cr":      round(df["credit"].sum(), 2),
        "total_debits_cr":       round(df["debit"].sum(), 2),
        "total_transactions":    len(df),
        "months_covered":        df["date"].dt.to_period("M").nunique(),
        "avg_monthly_credit_cr": round(
            df["credit"].sum() / max(df["date"].dt.to_period("M").nunique(), 1), 2
        ),
        "monthly_breakdown": monthly[
            ["month", "total_credits_cr", "total_debits_cr", "txn_count"]
        ].to_dict("records"),
    }


# ─────────────────────────────────────────────────────────────
# MASTER PARSER
# ─────────────────────────────────────────────────────────────

def parse_bank_statement(file_path: str) -> dict:
    print(f"\nParsing bank statement: {os.path.basename(file_path)}")

    df = load_bank_statement(file_path)
    print(f"  Loaded {len(df)} transactions | "
          f"{df['date'].min().date()} → {df['date'].max().date()}")
    print(f"  Unit conversion: raw rupees ÷ {RUPEES_TO_CR:,} → Crores applied")

    circular = detect_circular_trading(df)
    emis     = detect_hidden_emis(df)
    bounces  = detect_cheque_bounces(df)
    cash     = detect_excess_cash(df)
    related  = detect_related_party(df)
    summary  = compute_bank_summary(df)

    # REPLACE your all_flags block with this safe version:
    all_flags = []
    for result in [circular, emis, bounces, cash, related]:
        if result is None:
            continue
        sev = result.get("severity")
        if sev and sev != "CLEAR":
            all_flags.append({
                "type":         result.get("flag_type", "UNKNOWN"),
                "severity":     sev,
                "description":  result.get("description", ""),
                "score_impact": result.get("score_impact", 0),
            })

    total_score_impact = sum(f["score_impact"] for f in all_flags)

    print(f"\n  ─── Summary ───")
    print(f"  Credits  : ₹{summary['total_credits_cr']}Cr")
    print(f"  Debits   : ₹{summary['total_debits_cr']}Cr")
    print(f"  Score    : {total_score_impact} pts")
    print(f"  Flags    : {len(all_flags)}")

    return {
        "_source_file":       os.path.basename(file_path),
        "summary":            summary,
        "circular_trading":   circular,
        "hidden_emis":        emis,
        "cheque_bounces":     bounces,
        "excess_cash":        cash,
        "related_party":      related,
        "risk_flags":         all_flags,
        "total_score_impact": total_score_impact,
    }