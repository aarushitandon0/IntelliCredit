import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from src.ingestion.pdf_parser import parse_document
import json

BASE = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_docs')

print("=" * 60)
print("  PDF PARSER TEST")
print("=" * 60)

# ── Test 1: Annual Report ────────────────────────────────────
print("\n[1] Parsing 2025 Annual Report...")
ar = parse_document(os.path.join(BASE, "2024_AR.pdf"), "annual_report")

print(f"\n  Company:  {ar.get('company_name')}")
print(f"  FY:       {ar.get('financial_year')}")
print(f"  Business: {ar.get('business_description', '')[:80]}")

fin = ar.get('financials', {}) or {}
print(f"\n  FINANCIALS:")
print(f"    Revenue:    ₹{fin.get('revenue_from_operations_cr')}Cr")
print(f"    PAT:        ₹{fin.get('profit_after_tax_cr')}Cr")
print(f"    PBT:        ₹{fin.get('profit_before_tax_cr')}Cr")
print(f"    EBITDA:     ₹{fin.get('ebitda_cr')}Cr")
print(f"    Total Debt: ₹{fin.get('total_debt_cr')}Cr")
print(f"    Net Worth:  ₹{fin.get('total_equity_cr')}Cr")
print(f"    Curr Assets:₹{fin.get('current_assets_cr')}Cr")
print(f"    Curr Liab:  ₹{fin.get('current_liabilities_cr')}Cr")

directors = ar.get('directors') or []
print(f"\n  DIRECTORS ({len(directors)} found):")
for d in directors:
    din = d.get('din') or 'DIN not found'
    print(f"    → {d.get('name')} | DIN: {din} | {d.get('designation')}")

auditor = ar.get('auditor') or {}
print(f"\n  AUDITOR: {auditor.get('firm_name')}")
if auditor.get('going_concern_flag'):
    print(f"  🚨 GOING CONCERN FLAGGED")
if auditor.get('qualification'):
    print(f"  ⚠️  Qualification: {auditor.get('qualification')[:100]}")

risks = ar.get('key_risks') or []
print(f"\n  KEY RISKS ({len(risks)} found):")
for r in risks[:3]:
    print(f"    → {r[:80]}")

print(f"\n  Window quality score: {ar.get('_financial_window_quality')}/7")

# ── Test 2: Shareholding ─────────────────────────────────────
print("\n" + "="*60)
print("[2] Parsing December 2025 Shareholding...")
sh = parse_document(os.path.join(BASE, "dec_2025_shareholdings.pdf"), "shareholding")

ph = sh.get('promoter_holding') or {}
inst = sh.get('institutional_holding') or {}
print(f"\n  Quarter:          {sh.get('quarter')}")
print(f"  Promoter holding: {ph.get('total_pct')}%")
print(f"  Pledged shares:   {ph.get('pledged_pct') or 0}%")
print(f"  FII/FPI:          {inst.get('fii_fpi_pct')}%")
print(f"  DII:              {inst.get('dii_pct')}%")
print(f"  Public:           {sh.get('public_holding_pct')}%")

flags = sh.get('risk_flags') or []
if flags:
    print(f"\n  RISK FLAGS:")
    for f in flags:
        icon = "🚨" if f['severity'] == "HIGH" else "⚠️"
        print(f"  {icon} {f['description']} | Impact: {f['score_impact']}")
else:
    print(f"\n  ✅ No shareholding red flags")

# ── Test 3: CRISIL ───────────────────────────────────────────
print("\n" + "="*60)
print("[3] Parsing CRISIL 2026 Rating Report...")
rr = parse_document(os.path.join(BASE, "crisil_2026.pdf"), "rating_report")

print(f"\n  Agency:       {rr.get('agency')}")
print(f"  Rating:       {rr.get('rating')}")
print(f"  Outlook:      {rr.get('outlook')}")
print(f"  Score:        {rr.get('rating_score')}/10")
print(f"  Liquidity:    {rr.get('liquidity')}")

strengths = rr.get('key_strengths') or []
concerns  = rr.get('key_concerns')  or []
print(f"\n  KEY STRENGTHS ({len(strengths)}):")
for s in strengths[:3]:
    print(f"    ✅ {s[:80]}")
print(f"\n  KEY CONCERNS ({len(concerns)}):")
for c in concerns[:3]:
    print(f"    ⚠️  {c[:80]}")

print("\n" + "="*60)
print("  ALL TESTS COMPLETE")
print("="*60)