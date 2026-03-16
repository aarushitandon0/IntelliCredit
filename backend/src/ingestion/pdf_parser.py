import os
import sys
import pdfplumber

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.utils.llm_client import extract_structured_data

# ══════════════════════════════════════════════════════════════
# SWITCHED FROM PyMuPDF (fitz) TO pdfplumber
# Reason: fitz misreads certain pages in Skipper's PDF.
# pdfplumber correctly extracts all pages including P&L page 220.
#
# KEY CONSTRAINTS BAKED IN:
# - Standalone section: pages 207-294
# - Consolidated section: pages 295-365 → IGNORED
# - Page 248 has reversed text (PDF artifact) → auto-skipped
# - Risk content: MD&A pages 93-130
# - Bank limits: Notes pages 224-260
# ══════════════════════════════════════════════════════════════


def open_pdf(pdf_path: str):
    pdf = pdfplumber.open(pdf_path)
    return pdf, len(pdf.pages)


def get_page_text(pdf, page_num: int) -> str:
    if page_num < 0 or page_num >= len(pdf.pages):
        return ""
    text = pdf.pages[page_num].extract_text() or ""

    # Skip reversed/mirrored pages (PDF printing artifact)
    if "tnetatS" in text or "laicnaniF" in text or "enoladnatS ot setoN" in text:
        return ""

    # Strip logo watermark lines — the "SKIPPER Limited" logo gets OCR'd as
    # "9KIPPER", "@KIPPER", "L4fnited" etc. on every page of some annual reports
    WATERMARK_JUNK = {'9KIPPER', '@KIPPER', 'L4fnited', 'L4ff', 'L4fie.ti',
                      '-Limited', '----Limited----', '--- Limited---', '4it'}
    clean = [
        line for line in text.split('\n')
        if line.strip() not in WATERMARK_JUNK
        and not any(w in line for w in ('9KIPPER', '@KIPPER', 'L4fnited', 'L4ff'))
    ]
    return '\n'.join(clean)


def get_pages_text(pdf, start: int, end: int, max_page: int = 9999) -> str:
    end = min(end, len(pdf.pages), max_page)
    start = max(0, start)
    return "\n".join(
        t for i in range(start, end)
        if (t := get_page_text(pdf, i))
    )


def find_section_page(pdf, keywords: list, search_from: int = 0,
                      search_before: int = 9999, heading_only: bool = False) -> int:
    """
    Pass 1: keyword in first 200 chars (heading match — most reliable)
    Pass 2: keyword anywhere on page (fallback, only if heading_only=False)
    search_before: hard ceiling — never return page index >= this value
    """
    limit = min(len(pdf.pages), search_before)

    # Pass 1: heading
    for i in range(search_from, limit):
        text = get_page_text(pdf, i)
        if not text:
            continue
        if any(kw.lower() in text[:200].lower() for kw in keywords):
            return i

    if heading_only:
        return -1

    # Pass 2: anywhere
    for i in range(search_from, limit):
        text = get_page_text(pdf, i)
        if not text:
            continue
        if any(kw.lower() in text.lower() for kw in keywords):
            return i

    return -1


def extract_text_from_pdf(pdf_path: str, max_pages: int = 40) -> str:
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= max_pages:
                    break
                text += (page.extract_text() or "") + "\n"
    except Exception as e:
        print(f"  Extraction error: {e}")
    return text.strip()


# ─────────────────────────────────────────────────────────────
# LLM EXTRACTORS — pure Groq, zero regex
# ─────────────────────────────────────────────────────────────

def llm_extract_financials(text: str) -> dict:
    prompt = """
You are a senior Indian CA reading a Profit and Loss Statement.

UNIT RULE — read the declaration at the very top of the text:
  "(C in million)" or "(Rs. in million)" → DIVIDE ALL NUMBERS BY 10 → Crores
  "(C in lakhs)"   or "(Rs. in lakhs)"   → DIVIDE ALL NUMBERS BY 100 → Crores
  "(C in crores)"  or "(Rs. in crores)"  → use numbers as-is

Current year = LEFT column of numbers. Ignore right column (previous year).

Example: unit=millions, Revenue shows "46,244.80" → revenue_cr = 46244.80/10 = 4624.48
Example: unit=millions, Finance Costs "2,127.49"  → finance_costs_cr = 212.749

Return ONLY valid JSON, no markdown:
{
    "unit_in_document": "millions or lakhs or crores",
    "revenue_from_operations_cr": number,
    "other_income_cr": number,
    "total_income_cr": number,
    "cost_of_materials_cr": number,
    "employee_benefit_expense_cr": number,
    "finance_costs_cr": number,
    "depreciation_cr": number,
    "other_expenses_cr": number,
    "profit_before_tax_cr": number,
    "tax_expense_cr": number,
    "profit_after_tax_cr": number,
    "eps_basic": number
}
Use null for missing values. Do NOT guess.
"""
    return extract_structured_data(text, prompt)


def llm_extract_balance_sheet(text: str) -> dict:
    prompt = """
You are a senior Indian CA reading a Standalone Balance Sheet.

UNIT RULE:
  "(C in million)" → DIVIDE BY 10 for Crores
  "(C in lakhs)"   → DIVIDE BY 100 for Crores
  "(C in crores)"  → use as-is

Current year = LEFT column. Ignore right column.
Total debt = long_term_borrowings + short_term_borrowings.

Return ONLY valid JSON:
{
    "total_assets_cr": number,
    "fixed_assets_net_cr": number,
    "total_equity_cr": number,
    "paid_up_capital_cr": number,
    "long_term_borrowings_cr": number,
    "short_term_borrowings_cr": number,
    "total_debt_cr": number,
    "current_assets_cr": number,
    "current_liabilities_cr": number,
    "inventories_cr": number,
    "trade_receivables_cr": number,
    "cash_equivalents_cr": number
}
"""
    return extract_structured_data(text, prompt)


def llm_extract_directors(text: str) -> dict:
    prompt = """
You are reading the Board of Directors section of an Indian annual report.
DIN = 8-digit Director Identification Number e.g. "DIN: 00063555"

Return ONLY valid JSON:
{
    "company_name": "string",
    "cin": "string",
    "financial_year": "string",
    "registered_office": "string",
    "business_description": "one sentence",
    "directors": [
        {
            "name": "full name, no Mr/Ms prefix",
            "din": "8-digit string",
            "designation": "string",
            "independent": true or false,
            "executive": true or false
        }
    ],
    "company_secretary": "string or null",
    "cfo": "string or null"
}
Include ALL directors. Indian boards have 6-12 members.
"""
    return extract_structured_data(text, prompt)


def llm_extract_auditor(text: str) -> dict:
    prompt = """
You are reading an Indian Auditor's Report.
Look for: firm name, registration number, going concern language, qualifications.

IMPORTANT: Only set going_concern_flag=true if you find EXPLICIT phrases like:
"material uncertainty related to going concern" or "significant doubt about ability to continue"
A clean audit opinion is NOT going concern. Auditor signing is NOT going concern.

Return ONLY valid JSON:
{
    "auditor": {
        "firm_name": "string",
        "registration_number": "string or null",
        "qualification": "string or null",
        "emphasis_of_matter": "string or null",
        "going_concern_flag": true or false,
        "going_concern_text": "string or null"
    },
    "dividend_per_share": number or null,
    "dividend_declared": true or false
}
"""
    return extract_structured_data(text, prompt)


def llm_extract_notes(text: str) -> dict:
    prompt = """
You are reading Notes to Standalone Financial Statements from an Indian annual report.
Unit is likely millions — divide by 10 for Crores.

Look for:
1. Borrowings from banks: Cash Credit, Working Capital Demand Loans, Packing Credit, Term Loans
2. Contingent liabilities: tax demands, guarantees, court claims
3. Related party transactions with group entities
4. Key business risks

Return ONLY valid JSON:
{
    "contingent_liabilities_cr": number,
    "contingent_liability_details": ["string"],
    "existing_bank_limits": [
        {
            "bank_name": "string",
            "limit_cr": number,
            "type": "Cash Credit / Term Loan / Working Capital",
            "secured_by": "string"
        }
    ],
    "related_party_transactions": ["string with amount"],
    "key_risks": ["one sentence per risk"],
    "total_secured_borrowings_cr": number,
    "total_unsecured_borrowings_cr": number
}
"""
    return extract_structured_data(text, prompt)


def llm_extract_risks(text: str) -> dict:
    prompt = """
You are reading the Management Discussion and Analysis section of an Indian annual report.
Extract all key risks, business challenges, and management concerns.

Return ONLY valid JSON:
{
    "key_risks": ["one sentence per risk"],
    "industry_outlook": "one sentence",
    "management_concerns": ["one sentence per concern"]
}
"""
    return extract_structured_data(text, prompt)


# ─────────────────────────────────────────────────────────────
# COMPUTED RATIOS
# ─────────────────────────────────────────────────────────────

def compute_ratios(financials: dict) -> dict:
    ratios = {}
    try:
        rev    = financials.get("revenue_from_operations_cr") or 0
        pat    = financials.get("profit_after_tax_cr") or 0
        pbt    = financials.get("profit_before_tax_cr") or 0
        fin    = financials.get("finance_costs_cr") or 0
        dep    = financials.get("depreciation_cr") or 0
        curr_a = financials.get("current_assets_cr") or 0
        curr_l = financials.get("current_liabilities_cr") or 0
        debt   = financials.get("total_debt_cr") or 0
        equity = financials.get("total_equity_cr") or 0

        if pbt and fin and dep:
            ratios["ebitda_cr"] = round(pbt + fin + dep, 2)
        ebitda = ratios.get("ebitda_cr") or 0

        if ebitda and fin and fin > 0:
            ratios["dscr_approximate"] = round(ebitda / fin, 2)
        if pbt and fin and fin > 0:
            ratios["interest_coverage"] = round((pbt + fin) / fin, 2)
        if curr_a and curr_l and curr_l > 0:
            ratios["current_ratio"] = round(curr_a / curr_l, 2)
        if debt and equity and equity > 0:
            ratios["debt_equity"] = round(debt / equity, 2)
        if pat and rev and rev > 0:
            ratios["net_profit_margin_pct"] = round(pat / rev * 100, 2)
        if pat and equity and equity > 0:
            ratios["return_on_equity_pct"] = round(pat / equity * 100, 2)

    except Exception as e:
        ratios["computation_error"] = str(e)
    return ratios


# ─────────────────────────────────────────────────────────────
# MASTER ANNUAL REPORT PARSER
# ─────────────────────────────────────────────────────────────

def parse_annual_report(pdf_path: str) -> dict:
    print(f"  Opening PDF (pdfplumber)...")
    pdf, total_pages = open_pdf(pdf_path)
    print(f"  Total pages: {total_pages}")
    result = {"_total_pages": total_pages}

    # Find where consolidated section starts — never search past this
    consolidated_start = find_section_page(pdf, [
        "consolidated balance sheet",
        "consolidated statement of profit",
    ], search_from=250, heading_only=True)

    STANDALONE_MAX = consolidated_start if consolidated_start != -1 else total_pages
    if consolidated_start != -1:
        print(f"  Consolidated starts page {consolidated_start+1} → standalone bounded to 1-{STANDALONE_MAX}")

    print(f"  Locating sections...")

    pl_page = find_section_page(pdf, [
        "standalone statement of profit & loss",
        "standalone statement of profit and loss",
    ], search_from=150, search_before=STANDALONE_MAX, heading_only=True)
    if pl_page == -1:
        pl_page = find_section_page(pdf, [
            "statement of profit & loss",
            "statement of profit and loss",
        ], search_from=150, search_before=STANDALONE_MAX, heading_only=True)

    bs_page = find_section_page(pdf, [
        "standalone balance sheet",
        "balance sheet\nas at",
    ], search_from=150, search_before=STANDALONE_MAX, heading_only=True)

    board_page = find_section_page(pdf, [
        "directors & key managerial",
        "directors and key managerial",
        "board consisted of",
        "(din: 002",    # catches inline "Mr. X (DIN: 00226775)" format
        "(din: 000",    # catches any 8-digit DIN in body text
        "din - 000",    # catches "DIN - 00063555" format on BS/PL signature line
    ], search_from=55, search_before=180)

    auditor_page = find_section_page(pdf, [
        "firm registration no.",
        "firm's regn no.",
        "udin:",
    ], search_from=150, search_before=STANDALONE_MAX)

    notes_page = find_section_page(pdf, [
        "notes to standalone financial",
        "notes forming part of standalone",
        "notes to the standalone",
    ], search_from=200, search_before=STANDALONE_MAX, heading_only=True)

    contingent_page = find_section_page(pdf, [
        "contingent liabilities not provided",
        "contingent liabilities and commitments",
    ], search_from=200, search_before=STANDALONE_MAX)

    mda_page = find_section_page(pdf, [
        "management discussion and analysis",
        "management's discussion and analysis",
    ], search_from=85, search_before=150, heading_only=True)

    print(f"  P&L:          page {pl_page+1 if pl_page!=-1 else 'NOT FOUND'}")
    print(f"  Balance Sheet: page {bs_page+1 if bs_page!=-1 else 'NOT FOUND'}")
    print(f"  Directors:    page {board_page+1 if board_page!=-1 else 'NOT FOUND'}")
    print(f"  Auditor:      page {auditor_page+1 if auditor_page!=-1 else 'NOT FOUND'}")
    print(f"  Notes:        page {notes_page+1 if notes_page!=-1 else 'NOT FOUND'}")
    print(f"  Contingent:   page {contingent_page+1 if contingent_page!=-1 else 'NOT FOUND'}")
    print(f"  MD&A:         page {mda_page+1 if mda_page!=-1 else 'NOT FOUND'}")

    # P&L
    if pl_page != -1:
        print(f"  Extracting P&L (pages {pl_page+1}-{pl_page+3})...")
        pl_text = get_pages_text(pdf, pl_page, pl_page + 3, max_page=STANDALONE_MAX)
        r = llm_extract_financials(pl_text)
        if isinstance(r, dict) and "error" not in r:
            result["financials"] = r
            print(f"    ✅ Revenue:  ₹{r.get('revenue_from_operations_cr')}Cr")
            print(f"    ✅ PAT:      ₹{r.get('profit_after_tax_cr')}Cr")
            print(f"    ✅ PBT:      ₹{r.get('profit_before_tax_cr')}Cr")
            print(f"    ✅ Finance:  ₹{r.get('finance_costs_cr')}Cr")
            print(f"    ✅ Depr:     ₹{r.get('depreciation_cr')}Cr")
            print(f"    ✅ Unit:     {r.get('unit_in_document')}")
        else:
            print(f"    ❌ Error: {r}")

    # Balance Sheet
    if bs_page != -1:
        print(f"  Extracting Balance Sheet (pages {bs_page+1}-{bs_page+3})...")
        bs_text = get_pages_text(pdf, bs_page, bs_page + 3, max_page=STANDALONE_MAX)
        r = llm_extract_balance_sheet(bs_text)
        if isinstance(r, dict) and "error" not in r:
            if "financials" not in result:
                result["financials"] = {}
            result["financials"].update(r)
            print(f"    ✅ Total Assets: ₹{r.get('total_assets_cr')}Cr")
            print(f"    ✅ Total Debt:   ₹{r.get('total_debt_cr')}Cr")
            print(f"    ✅ Net Worth:    ₹{r.get('total_equity_cr')}Cr")
            print(f"    ✅ Curr Assets:  ₹{r.get('current_assets_cr')}Cr")
            print(f"    ✅ Curr Liab:    ₹{r.get('current_liabilities_cr')}Cr")

    # Ratios
    if "financials" in result:
        ratios = compute_ratios(result["financials"])
        result["ratios"] = ratios
        result["financials"].update({k: v for k, v in ratios.items() if v})
        print(f"  Ratios: EBITDA=₹{ratios.get('ebitda_cr')}Cr | DSCR={ratios.get('dscr_approximate')} | ICR={ratios.get('interest_coverage')} | CR={ratios.get('current_ratio')} | D/E={ratios.get('debt_equity')}")

    # Directors
    if board_page != -1:
        print(f"  Extracting directors (pages {board_page+1}-{board_page+5})...")
        board_text = get_pages_text(pdf, board_page, board_page + 5)
        r = llm_extract_directors(board_text)
        if isinstance(r, dict) and "error" not in r:
            result.update({k: v for k, v in r.items() if v is not None})
            directors = r.get("directors") or []
            print(f"    ✅ {len(directors)} directors found")
            for d in directors:
                print(f"       → {d.get('name')} | DIN: {d.get('din')} | {d.get('designation')}")

    # Auditor
    if auditor_page != -1:
        print(f"  Extracting auditor (around page {auditor_page+1})...")
        audit_text = get_pages_text(pdf, max(0, auditor_page-1), auditor_page + 2)
        r = llm_extract_auditor(audit_text)
        if isinstance(r, dict) and "error" not in r:
            result.update(r)
            aud = r.get("auditor") or {}
            print(f"    ✅ Firm: {aud.get('firm_name')} | Reg: {aud.get('registration_number')}")
            if aud.get("going_concern_flag"):
                print(f"    🚨 GOING CONCERN")
            elif aud.get("emphasis_of_matter"):
                print(f"    ⚠️  Emphasis of Matter")
            else:
                print(f"    ✅ Clean opinion")

    # Notes
    notes_start = notes_page if notes_page != -1 else (
        contingent_page - 15 if contingent_page != -1 else -1
    )
    if notes_start != -1:
        print(f"  Extracting notes (pages {notes_start+1}-{notes_start+30})...")
        notes_text = get_pages_text(pdf, notes_start, notes_start + 30, max_page=STANDALONE_MAX)
        r = llm_extract_notes(notes_text)
        if isinstance(r, dict) and "error" not in r:
            result.update(r)
            limits = r.get("existing_bank_limits") or []
            rpt    = r.get("related_party_transactions") or []
            print(f"    ✅ Bank limits: {len(limits)} | RPT: {len(rpt)} | Contingent: ₹{r.get('contingent_liabilities_cr')}Cr")
            for lim in limits[:3]:
                print(f"       🏦 {lim.get('bank_name')} ₹{lim.get('limit_cr')}Cr ({lim.get('type')})")

    # MD&A Risks
    risk_start = mda_page if mda_page != -1 else 92
    print(f"  Extracting MD&A risks (pages {risk_start+1}-{risk_start+20})...")
    mda_text = get_pages_text(pdf, risk_start, risk_start + 20)
    r = llm_extract_risks(mda_text)
    if isinstance(r, dict) and "error" not in r:
        new_risks = r.get("key_risks") or []
        result["key_risks"] = (result.get("key_risks") or []) + new_risks
        result["industry_outlook"] = r.get("industry_outlook")
        result["management_concerns"] = r.get("management_concerns") or []
        print(f"    ✅ {len(new_risks)} risks from MD&A")
        for risk in new_risks[:3]:
            print(f"       → {str(risk)[:80]}")

    pdf.close()
    result["_source_file"] = os.path.basename(pdf_path)
    return result


# ─────────────────────────────────────────────────────────────
# OTHER PARSERS
# ─────────────────────────────────────────────────────────────

def parse_shareholding(pdf_path: str) -> dict:
    print(f"  Extracting shareholding pattern...")
    text = extract_text_from_pdf(pdf_path, max_pages=15)
    prompt = """
You are analyzing an Indian BSE shareholding pattern.
Percentages are plain numbers e.g. 45.23

Return ONLY valid JSON:
{
    "quarter": "string",
    "company_name": "string",
    "total_shares": number,
    "promoter_holding": {"total_pct": number, "pledged_shares": number, "pledged_pct": number},
    "institutional_holding": {"fii_fpi_pct": number, "dii_pct": number, "mutual_funds_pct": number},
    "public_holding_pct": number,
    "top_shareholders": [{"name": "string", "holding_pct": number, "category": "string"}]
}
"""
    result = extract_structured_data(text, prompt)
    if isinstance(result, dict):
        ph = result.get("promoter_holding") or {}
        total, pledged = ph.get("total_pct") or 0, ph.get("pledged_pct") or 0
        flags = []
        if total and total < 40:
            flags.append({"type": "LOW_PROMOTER_HOLDING", "severity": "HIGH",
                          "value": total, "description": f"Promoter {total}% < 40% threshold",
                          "score_impact": -1.5})
        if pledged and pledged > 30:
            flags.append({"type": "HIGH_PLEDGE", "severity": "HIGH",
                          "value": pledged, "description": f"{pledged}% pledged — margin call risk",
                          "score_impact": -2.0})
        elif pledged and pledged > 10:
            flags.append({"type": "MODERATE_PLEDGE", "severity": "MEDIUM",
                          "value": pledged, "description": f"{pledged}% pledged — monitor",
                          "score_impact": -1.0})
        result["risk_flags"] = flags
    result["_source_file"] = os.path.basename(pdf_path)
    return result


def parse_rating_report(pdf_path: str) -> dict:
    print(f"  Extracting rating report...")
    text = extract_text_from_pdf(pdf_path, max_pages=15)
    prompt = """
You are reading an Indian credit rating report (CRISIL/ICRA/CARE).
Return ONLY valid JSON:
{
    "agency": "string", "company_name": "string", "instrument": "string",
    "amount_rated_cr": number, "rating": "string", "rating_action": "string",
    "outlook": "Stable/Positive/Negative/Watch", "rating_date": "string",
    "key_strengths": ["string"], "key_concerns": ["string"],
    "liquidity": "Adequate/Stretched/Poor/Superior",
    "financial_risk_profile": "string", "business_risk_profile": "string",
    "rating_history": [{"date": "string", "rating": "string", "action": "string"}]
}
"""
    result = extract_structured_data(text, prompt)
    rating_map = {"AAA":10,"AA+":9.5,"AA":9,"AA-":8.5,"A+":8,"A":7.5,"A-":7,
                  "BBB+":6.5,"BBB":6,"BBB-":5.5,"BB+":5,"BB":4.5,"BB-":4,"B":3,"C":2,"D":1}
    if isinstance(result, dict):
        rs = str(result.get("rating") or "").upper()
        for k, v in rating_map.items():
            if k in rs:
                result["rating_score"] = v - (1.0 if "negative" in str(result.get("outlook") or "").lower() else 0)
                break
        concerns = result.get("key_concerns") or []
        result["risk_flags"] = [
            {"type": "RATING_CONCERN", "severity": "MEDIUM", "description": str(c),
             "source": f"{result.get('agency')} {result.get('rating_date','')}", "score_impact": -0.5}
            for c in concerns
        ]
    result["_source_file"] = os.path.basename(pdf_path)
    return result


def parse_legal_notice(pdf_path: str) -> dict:
    print(f"  Extracting legal notice...")
    text = extract_text_from_pdf(pdf_path, max_pages=20)
    prompt = """
Return ONLY valid JSON:
{
    "document_type": "GST_NOTICE/TAX_NOTICE/COURT_NOTICE/SANCTION_LETTER/OTHER",
    "issuing_authority": "string", "company_name": "string", "date": "string",
    "demand_amount_cr": number, "subject": "string", "compliance_deadline": "string or null",
    "sanction_details": {
        "bank_name": "string or null", "sanctioned_amount_cr": number,
        "tenor_months": number, "interest_rate_pct": number,
        "security_offered": "string or null", "conditions": ["string"]
    },
    "severity": "HIGH/MEDIUM/LOW", "score_impact": number
}
"""
    result = extract_structured_data(text, prompt)
    result["_source_file"] = os.path.basename(pdf_path)
    return result


# ─────────────────────────────────────────────────────────────
# MASTER ROUTER
# ─────────────────────────────────────────────────────────────

def parse_document(pdf_path: str, doc_type: str) -> dict:
    """doc_type: annual_report | shareholding | rating_report | legal_notice"""
    print(f"\nParsing: {os.path.basename(pdf_path)} as [{doc_type}]")
    parsers = {
        "annual_report": parse_annual_report,
        "shareholding":  parse_shareholding,
        "rating_report": parse_rating_report,
        "legal_notice":  parse_legal_notice,
    }
    if doc_type not in parsers:
        return {"error": f"Unknown doc_type: {doc_type}"}
    try:
        return parsers[doc_type](pdf_path)
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}