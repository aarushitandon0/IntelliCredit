# Intelli-Credit

**AI-Powered Corporate Credit Appraisal Engine**

India's corporate lending ecosystem is trapped in a data paradox. Credit managers have access to more information than ever -- GST filings, bank statements, annual reports, MCA records, court databases -- yet a single mid-sized loan appraisal takes 3 to 6 weeks. Intelli-Credit eliminates that gap by ingesting every data source simultaneously and producing a fully cited, auditable credit decision in under 5 minutes.

---

## The Problem

Manual credit appraisal has three critical failure modes:

- **Slow.** Weeks pass while competitors approve faster. Markets move before decisions are made.
- **Biased.** One analyst's experience and attention span determines a Rs. 40 Cr outcome.
- **Blind.** The most dangerous signals -- a director's NPA history, a GST evasion notice filed last month, circular trading buried in bank statements -- are missed entirely because no human can process every data source simultaneously.

---

## What Intelli-Credit Does

The system is built around three pillars that map directly to the end-to-end appraisal workflow.

### Pillar 1 -- Data Ingestor

Parses messy Indian financial documents (digital and scanned PDFs, CSV bank statements, and GST returns) to extract financial ratios and risk signals without manual data entry. Cross-leverages GST returns against bank statements using pure Pandas logic to automatically detect circular trading and revenue inflation -- no LLM is involved in the detection itself, making results fully deterministic and auditable.

Supported inputs:

- **Annual Reports (PDF):** Extracts P&L, balance sheets, key ratios, director DIN information, and auditor going-concern qualifications.
- **Bank Statements (CSV/Excel):** Detects transaction velocity, hidden EMI patterns, cheque bounces, and circular money movement.
- **GST Data (GSTR-3B / GSTR-2A):** Evaluates input tax credits and monthly revenue to compute a GST-verified maximum exposure limit.

### Pillar 2 -- Autonomous Research Agent

A multi-tool LangChain agent powered by Groq (LLaMA 3.3 70B) and Tavily that crawls the live web for real-time compliance and risk data. Every finding is sourced with an exact URL, assigned a severity level (HIGH / MEDIUM / LOW), and directly adjusts the final score.

Agent tools:

- **News Tool:** Searches for adverse media, DGGI/GST notices, and fraud allegations against the company and its promoters.
- **MCA Tool:** Cross-checks company status and Director Identification Numbers (DIN) against past defaults or struck-off entities.
- **eCourts Tool:** Searches for NCLT/IBC insolvency petitions and criminal FIRs against promoters.
- **Sector Tool:** Analyzes RBI regulations and macroeconomic headwinds for the specific industry.

The pillar also includes a **Credit Officer Portal** where qualitative due diligence observations (e.g., "factory found operating at 40% capacity during site visit") are entered and directly adjust the Five Cs score in real time, with a full audit trail of every override.

### Pillar 3 -- Recommendation Engine

Produces a professional Credit Appraisal Memo (CAM) in Word format using the Five Cs framework. Every score line contains three pieces of information: the sub-factor that drove it, the exact data point observed, and the source document or URL. No black box. No unexplained number.

---

## The Five Cs Scoring Model

The scoring engine is deterministic and fully transparent. It computes a composite score from 0 to 100 based on the classic Five Cs of Credit.

| Pillar | Weight | Primary Signals |
|---|---|---|
| Character | 20% | Director NPA links, adverse news, cheque bounces, management honesty, auditor qualifications |
| Capacity | 25% | DSCR, circular trading detection, GST vs. bank mismatch, hidden EMIs |
| Capital | 20% | Debt-to-equity ratio, net worth, promoter financial commitment |
| Collateral | 20% | Security cover ratio, MCA charge registry, physical verification overrides |
| Conditions | 15% | Sector headwinds, RBI regulations, external credit ratings, macro environment |

### Decision Thresholds

| Score Range | Decision | Loan Limit | Rate |
|---|---|---|---|
| 75 to 100 | Approved | 25% of GST-verified annual turnover | Base Rate + 1.5% |
| 55 to 74 | Conditional | 20% of GST-verified annual turnover | Base Rate + 3.0% |
| 40 to 54 | Committee Referral | Pending senior review | TBD |
| Below 40 | Rejected | Nil | N/A |

### Loan Limit Formula

```
Base Limit    = GST-Verified Annual Turnover x 25%

Verification Factor:
  Clean (0 flags)               -> 1.00
  Low mismatch (1-2 months)     -> 0.85
  High mismatch (3+ months)     -> 0.65
  Circular trading detected     -> 0.50

Final Limit   = (Base Limit x Verification Factor) - Existing Limits from Other Lenders
```

### Sample CAM Output

```
DECISION: REJECTED

Application for Rs. 40 Cr working capital facility by Rajesh Exports Pvt. Ltd. is
recommended for rejection.

Primary reason: Circular trading detected in bank statements across 3 months (Rs. 7.55 Cr,
June-August 2024), indicating material revenue inflation. GST-verified limit of Rs. 18 Cr
versus requested Rs. 40 Cr.

Secondary reason: High litigation risk identified in secondary research -- DGGI GST evasion
notice of Rs. 12 Cr (Financial Express, August 23 2024) not disclosed by management.
Director NPA link traced via MCA: Amit Shah, DIN 07654321, is co-director at Rajesh Polymers
Pvt. Ltd., declared NPA by SBI March 2022.

Despite adequate collateral cover of 1.5x and stable GST flows, the combination of
operational fraud signals, undisclosed regulatory exposure, and promoter NPA association
renders this application ineligible under standard credit policy.
```

---

## Architecture

```
intelli-credit/
├── backend/
│   ├── src/
│   │   ├── agents/        # LangChain research agent and tool definitions
│   │   ├── ingestion/     # Parsers for bank statements and annual reports
│   │   ├── scoring/       # Five Cs deterministic scoring engine
│   │   └── output/        # Word CAM generation logic (python-docx)
│   ├── main.py            # FastAPI endpoints and routing
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # UploadPortal, ProcessingView, ResultsDashboard
│   │   ├── tabs/          # FraudTab, FiveCsTab, ResearchTab, FinancialsTab
│   │   ├── App.jsx        # Main state management
│   │   └── index.css      # Dark theme CSS variables
│   └── package.json
└── data/                  # Mock GST, ITR, and bank statement samples for testing
```

### Backend: FastAPI + Python

| Endpoint | Purpose |
|---|---|
| `POST /api/analyze` | Accepts all documents, runs parsing and the research agent, computes the Five Cs score, and returns a serialized JSON decision. |
| `POST /api/qualitative` | Accepts Credit Officer portal inputs and recalculates the Five Cs score on the fly. |
| `POST /api/generate-cam` | Generates a formatted Word document Credit Appraisal Memo ready for signatures. |
| `GET /api/health` | System status and API key validation. |

**Tech stack:** FastAPI, Pydantic, Uvicorn, LangChain, Groq, Tavily, pdfplumber, Tesseract OCR, Pandas, python-docx.

### Frontend: React + Vite

A dark-themed (Notion/Linear inspired) dashboard with glassmorphism styling, keyframe animations, and a multi-tab sidebar layout. Drag-and-drop document upload, an animated terminal view showing live agent reasoning steps, and a results portal with dedicated tabs for Fraud signals, Five Cs breakdown, Research findings, and raw Financials.

**Tech stack:** React 19, Vite, vanilla CSS.

---

## Setup

### Prerequisites

- Python 3.9 or higher
- Node.js v18 or higher and npm

### 1. Backend

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv

# Windows
.\venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory with your API keys:

```env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

Start the server:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Swagger UI is at `http://localhost:8000/docs`.

### 2. Frontend

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Access the portal at `http://localhost:5174` (or the port specified in Vite output).

---

## Fraud Detection Logic

The bank statement parser flags the following patterns automatically using Pandas without any LLM involvement:

- **Circular Trading:** Identifies round-tripping or circular money movement designed to artificially inflate turnover. Applies a 0.50 verification factor to the loan limit and heavily penalizes the Capacity score.
- **Hidden EMIs:** Flags recurring undisclosed debit patterns that suggest undisclosed shadow loans.
- **Cheque Bounces:** Automatically flags return transactions. More than 2 bounces is treated as a severe red flag consistent with standard RBI banking policy.
- **GST vs. Bank Mismatches:** Detects variances greater than 20% between reported GST revenues and actual bank credits on a month-by-month basis.

---

## License

This software is released for evaluation and demonstration purposes.

All proprietary scoring models, fraud detection logic, and AI agents within this repository are proof-of-concept software. They must be thoroughly validated by qualified credit professionals before any real-world financial deployment or corporate credit underwriting.
