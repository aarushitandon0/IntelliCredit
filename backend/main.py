"""
main.py
───────
FastAPI backend for Intelli-Credit.

Endpoints:
  POST /api/analyze          — full credit analysis pipeline
  POST /api/qualitative      — submit credit officer portal inputs
  POST /api/generate-cam     — generate Word CAM document
  GET  /api/health           — system status check
  GET  /api/analysis/{id}    — retrieve stored analysis result

Run with:
  uvicorn main:app --reload --port 8000
"""

import os
import uuid
import json
import traceback
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import tempfile
import shutil

# ─── Module imports ───────────────────────────────────────────
from src.ingestion.bank_parser  import parse_bank_statement
from src.ingestion.pdf_parser   import parse_annual_report
from src.agents.research_agent  import run_research_agent
from src.scoring.five_cs_model  import compute_five_cs, scorecard_to_dict
from src.scoring.risk_adjuster  import process_qualitative_inputs

# CAM generator — will be built next
try:
    from src.output.cam_generator import generate_cam
    CAM_AVAILABLE = True
except ImportError:
    CAM_AVAILABLE = False

# ─── App setup ────────────────────────────────────────────────
app = FastAPI(
    title="Intelli-Credit API",
    description="AI-Powered Corporate Credit Appraisal Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory store (replace with DB in production) ──────────
ANALYSES: dict = {}
QUALITATIVE: dict = {}

# ─────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────

class QualitativeInput(BaseModel):
    analysis_id:              str
    factory_utilization_pct:  Optional[int]   = None
    collateral_verified:      Optional[bool]  = None
    management_responsiveness: Optional[str]  = "adequate"
    machinery_condition:      Optional[str]   = "good"
    inventory_level:          Optional[str]   = "normal"
    factory_activity:         Optional[str]   = "full"
    contradictions_noted:     Optional[bool]  = False
    macro_outlook:            Optional[str]   = "neutral"
    references_checked:       Optional[bool]  = False
    notes:                    Optional[str]   = ""


# ─────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    groq_ok   = bool(os.getenv("GROQ_API_KEY"))
    tavily_ok = bool(os.getenv("TAVILY_API_KEY"))
    return {
        "status":        "operational",
        "groq":          "connected" if groq_ok   else "missing API key",
        "tavily":        "connected" if tavily_ok else "missing API key",
        "cam_generator": "available" if CAM_AVAILABLE else "not built yet",
        "timestamp":     datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# MAIN ANALYSIS ENDPOINT
# ─────────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze(
    company_name:    str          = Form(...),
    cin:             str          = Form(...),
    loan_amount_cr:  float        = Form(...),
    sector:          str          = Form(...),
    annual_report:   Optional[UploadFile] = File(None),
    bank_statement:  Optional[UploadFile] = File(None),
    gstr3b:          Optional[UploadFile] = File(None),
    gstr2a:          Optional[UploadFile] = File(None),
):
    analysis_id = f"IC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    tmp_dir     = tempfile.mkdtemp()
    start_time  = datetime.now()

    print(f"\n{'='*60}")
    print(f"  ANALYSIS: {analysis_id}")
    print(f"  Company : {company_name} | CIN: {cin}")
    print(f"  Loan    : ₹{loan_amount_cr}Cr | Sector: {sector}")
    print(f"{'='*60}")

    result = {
        "analysis_id":    analysis_id,
        "company_name":   company_name,
        "cin":            cin,
        "loan_amount_cr": loan_amount_cr,
        "sector":         sector,
        "status":         "processing",
        "errors":         [],
    }

    try:
        # ── STEP 1: Parse uploaded documents ──────────────────
        pdf_data  = {}
        bank_data = {}
        gst_data  = {}

        if annual_report:
            print("\n  STEP 1a: Parsing Annual Report...")
            pdf_path = os.path.join(tmp_dir, annual_report.filename)
            with open(pdf_path, "wb") as f:
                f.write(await annual_report.read())
            try:
                pdf_data = parse_annual_report(pdf_path)
                print(f"  Annual report parsed: {len(pdf_data)} fields extracted")
            except Exception as e:
                result["errors"].append(f"Annual report parse error: {str(e)}")
                print(f"  WARNING: Annual report parse failed: {e}")

        if bank_statement:
            print("\n  STEP 1b: Parsing Bank Statement...")
            bank_path = os.path.join(tmp_dir, bank_statement.filename)
            with open(bank_path, "wb") as f:
                f.write(await bank_statement.read())
            try:
                bank_data = parse_bank_statement(bank_path)
                print(f"  Bank parsed: {bank_data.get('summary', {}).get('total_transactions')} txns")
            except Exception as e:
                result["errors"].append(f"Bank statement parse error: {str(e)}")
                print(f"  WARNING: Bank parse failed: {e}")

        # ── STEP 2: Research Agent ─────────────────────────────
        print("\n  STEP 2: Running Research Agent...")
        directors = pdf_data.get("directors", []) if pdf_data else []
        try:
            research = run_research_agent(
                company_name   = company_name,
                cin            = cin,
                sector         = sector,
                directors      = directors,
            )
        except Exception as e:
            research = {"risk_flags": [], "sector_flags": [], "total_score_impact": 0}
            result["errors"].append(f"Research agent error: {str(e)}")
            print(f"  WARNING: Research agent failed: {e}")

        # ── STEP 3: Extract financials + compute ratios ────────
        financials = {}
        if pdf_data:
            financials = {k: v for k, v in pdf_data.get("financials", {}).items() if v is not None}
            financials.update({k: v for k, v in pdf_data.get("ratios", {}).items() if v is not None})

        # ── STEP 4: Five Cs Scoring ────────────────────────────
        print("\n  STEP 4: Computing Five Cs Scorecard...")

        # Separate company flags from sector flags
        all_research_flags = research.get("risk_flags", [])
        sector_flags  = research.get("sector_flags", [])
        company_flags = research.get("company_flags", [])

        scorecard = compute_five_cs(
            financials       = financials or None,
            circular_trading = bank_data.get("circular_trading"),
            gst_mismatch     = gst_data.get("gst_bank_mismatch") if gst_data else None,
            hidden_emis      = bank_data.get("hidden_emis"),
            cheque_bounces   = bank_data.get("cheque_bounces"),
            research_flags   = company_flags,
            sector_flags     = sector_flags,
            mca_charges      = [],
            auditor          = pdf_data.get("auditor") if pdf_data else {},
            shareholding     = {},
            bank_limits      = pdf_data.get("existing_bank_limits", []) if pdf_data else [],
            rating           = {},
            qualitative      = None,
            loan_requested_cr= loan_amount_cr,
            gst_limit_cr     = gst_data.get("loan_limit", {}).get("final_recommended_limit_cr", 0) if gst_data else 0,
        )

        scorecard_dict = scorecard_to_dict(scorecard)

        # ── STEP 5: Build final response ───────────────────────
        elapsed = (datetime.now() - start_time).total_seconds()

        result.update({
            "status":               "complete",
            "processing_time_seconds": round(elapsed, 1),
            "date":                 datetime.now().strftime("%d %B %Y"),
            "pdf_extraction":       {
                "directors_found":  len(directors),
                "financials_found": len(financials),
            },
            "bank_analysis":        bank_data.get("summary") if bank_data else None,
            "cross_checks": {
                "circular_trading_instances": bank_data.get("circular_trading", {}).get("instance_count", 0) if bank_data else 0,
                "circular_trading_cr":        bank_data.get("circular_trading", {}).get("total_circular_cr", 0) if bank_data else 0,
                "cheque_bounces":             bank_data.get("cheque_bounces", {}).get("count", 0) if bank_data else 0,
                "hidden_emis":                bank_data.get("hidden_emis", {}).get("count", 0) if bank_data else 0,
            },
            "research": {
                "total_queries":    research.get("total_queries_run", 0),
                "high_flags":       research.get("high_count", 0),
                "medium_flags":     research.get("medium_count", 0),
                "risk_flags":       all_research_flags,
            },
            "scoring":              scorecard_dict,
        })

        # Store for qualitative update and CAM generation
        ANALYSES[analysis_id] = result

        print(f"\n  ── COMPLETE ──")
        print(f"  Score    : {scorecard_dict['composite_score']}")
        print(f"  Decision : {scorecard_dict['decision']}")
        print(f"  Time     : {elapsed:.1f}s")

        return result

    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"\n  FATAL ERROR: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─────────────────────────────────────────────────────────────
# QUALITATIVE INPUT ENDPOINT
# ─────────────────────────────────────────────────────────────

@app.post("/api/qualitative")
def submit_qualitative(inputs: QualitativeInput):
    """
    Submit Credit Officer portal observations.
    Adjusts Five Cs scores and updates the stored analysis.
    """
    analysis_id = inputs.analysis_id
    if analysis_id not in ANALYSES:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

    stored = ANALYSES[analysis_id]
    portal_dict = inputs.dict(exclude={"analysis_id"})

    print(f"\n  Qualitative input received for {analysis_id}")

    # Process qualitative inputs
    qualitative = process_qualitative_inputs(portal_dict)
    QUALITATIVE[analysis_id] = qualitative

    # Recompute Five Cs with qualitative adjustments
    financials = {}
    pdf_data   = stored.get("pdf_extraction", {})

    scorecard = compute_five_cs(
        financials       = stored.get("_financials"),
        circular_trading = stored.get("_bank_data", {}).get("circular_trading"),
        gst_mismatch     = None,
        hidden_emis      = stored.get("_bank_data", {}).get("hidden_emis"),
        cheque_bounces   = stored.get("_bank_data", {}).get("cheque_bounces"),
        research_flags   = stored.get("research", {}).get("risk_flags", []),
        sector_flags     = [],
        mca_charges      = [],
        auditor          = {},
        shareholding     = {},
        bank_limits      = [],
        rating           = {},
        qualitative      = qualitative,
        loan_requested_cr= stored.get("loan_amount_cr", 0),
        gst_limit_cr     = 0,
    )

    scorecard_dict = scorecard_to_dict(scorecard)

    # Update stored analysis
    stored["scoring"]              = scorecard_dict
    stored["qualitative_applied"]  = True
    stored["qualitative_summary"]  = qualitative.get("officer_notes_summary", "")
    ANALYSES[analysis_id]          = stored

    return {
        "analysis_id":         analysis_id,
        "status":              "updated",
        "qualitative_impact":  qualitative.get("total_qualitative_impact", 0),
        "updated_score":       scorecard_dict["composite_score"],
        "updated_decision":    scorecard_dict["decision"],
        "scoring":             scorecard_dict,
    }


# ─────────────────────────────────────────────────────────────
# CAM GENERATION ENDPOINT
# ─────────────────────────────────────────────────────────────

@app.post("/api/generate-cam")
def generate_cam_endpoint(analysis_id: str):
    """Generate and return the Credit Appraisal Memo as a Word document."""
    if analysis_id not in ANALYSES:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

    if not CAM_AVAILABLE:
        raise HTTPException(status_code=501, detail="CAM generator not yet built")

    stored = ANALYSES[analysis_id]
    qualitative = QUALITATIVE.get(analysis_id)

    try:
        output_path = generate_cam(stored, qualitative)
        return FileResponse(
            path        = output_path,
            filename    = f"CAM_{stored['company_name'].replace(' ', '_')}_{analysis_id}.docx",
            media_type  = "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CAM generation failed: {str(e)}")


# ─────────────────────────────────────────────────────────────
# GET ANALYSIS
# ─────────────────────────────────────────────────────────────

@app.get("/api/analysis/{analysis_id}")
def get_analysis(analysis_id: str):
    if analysis_id not in ANALYSES:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
    return ANALYSES[analysis_id]


@app.get("/api/analyses")
def list_analyses():
    return [
        {
            "analysis_id":  k,
            "company_name": v.get("company_name"),
            "decision":     v.get("scoring", {}).get("decision"),
            "score":        v.get("scoring", {}).get("composite_score"),
            "date":         v.get("date"),
        }
        for k, v in ANALYSES.items()
    ]