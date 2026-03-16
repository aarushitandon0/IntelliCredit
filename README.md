# Intelli-Credit 🚀

**Intelli-Credit** is an AI-Powered Corporate Credit Appraisal Engine designed to automate and deeply enhance the complex process of corporate credit risk assessment. By combining document extraction, multi-agent live web research, and a highly transparent deterministic scoring model, Intelli-Credit drastically reduces manual underwriting hours while surfacing hidden financial risks.

---

## 🌟 Comprehensive Features

### 1. **Automated Financial Ingestion**
Intelli-Credit bypasses manual data entry by extracting structural data directly from corporate documentation:
- **Annual Reports (PDFs)**: Parses P&L, balance sheets, and key ratios. Extracts management and director DIN information, and detects critical red flags such as "Auditor going concern qualifications".
- **Bank Statements (CSV/Excel)**: Detects transaction velocity and specific patterns.
- **GST Data (GSTR-3B / GSTR-2A)**: Evaluates input tax credits and monthly revenue to compute a GST-verified maximum exposure limit.

### 2. **Advanced Risk & Fraud Detection Engine**
The backend parses bank statements structurally to find obscured risks:
- **Circular Trading Detection:** Identifies instances of round-tripping or circular money movement designed to artificially inflate turnover. This heavily penalizes the AI credit score.
- **Hidden EMIs:** Flags recurring undisclosed debit patterns that suggest shadow loans.
- **Cheque Bounces:** Automatically flags return transactions (more than 2 bounces is a severe red flag under standard RBI banking policy).
- **GST vs. Bank Mismatches:** Detects variances > 20% between reported GST revenues and actual bank credits.

### 3. **Autonomous Research Agent (LangChain + LLaMA 3.3 70B)**
A multi-tool research agent powered by Groq (LLaMA 3.3 70B) and Tavily searches the live web for real-time compliance and risk data:
- **News Tool:** Searches for adverse media, DGGI/GST notices, and fraud allegations.
- **MCA Tool:** Cross-checks company status and Director Identification Numbers (DIN) against past defaults or struck-off companies.
- **eCourts Tool:** Searches for NCLT/IBC insolvency petitions and criminal FIRs against promoters.
- **Sector Tool:** Analyzes RBI regulations and macroeconomic headwinds for the specific industry.
> *Every finding is strictly sourced with an exact URL, assigned a severity (HIGH/MEDIUM/LOW), and directly impacts the final score. No hallucinations.*

### 4. **The Five Cs Scorecard Engine**
Unlike black-box AI models, the Intelli-Credit scoring engine is deterministic and highly transparent. It computes a composite score (0-100) based on the classic **Five Cs of Credit**:
- **Character (20%)**: Promoter pledging, cheque bounces, auditor notes, and adverse MCA/News research flags.
- **Capacity (25%)**: DSCR (Debt Service Coverage Ratio), hidden EMIs, circular trading penalties, and net profit margins.
- **Capital (20%)**: Debt-to-Equity ratio, current ratio, absolute net worth, and promoter shareholding percentage.
- **Collateral (20%)**: Security cover ratio, immovable property bonuses, MCA double-pledging charge registry checks, and physical verification overrides.
- **Conditions (15%)**: Sector headwinds, external credit ratings (CRISIL/ICRA), and macroeconomic outlooks.

**Decision Thresholds:**
- **`75–100` → APPROVED**: Auto-approves up to 100% of the GST-verified limit at Base Rate + 1.5%.
- **`55–74` → CONDITIONAL**: Conditionally approves 80% of the limit at Base Rate + 3.0% with strict collateral covenants.
- **`40–54` → COMMITTEE REFERRAL**: Sends the file to a senior credit committee for manual review.
- **`< 40` → REJECTED**: Immediate zero-limit rejection.

### 5. **Credit Officer Portal & Qualitative Overrides**
The modern React dashboard allows Credit Officers to inject human due diligence (e.g., site visits, factory utilization observed, management responsiveness). These inputs dynamically recalculate the Five Cs score in real-time, allowing the AI to balance hard data with human "boots-on-the-ground" qualitative assessments.

---

## 🏗️ Project Architecture

A completely decoupled, modern client-server architecture.

### **Frontend: React + Vite**
- **Tech Stack:** React 19, Vite, vanilla CSS.
- **Design:** A premium, dark-themed (Notion/Linear inspired) UI featuring glassmorphism, smooth keyframe animations, and a multi-tab sidebar layout for seamless data review.
- **Core Components:**
  - `UploadPortal.jsx`: Drag-and-drop document ingestion.
  - `ProcessingView.jsx`: Animated, technical terminal output showcasing the AI agent's live reasoning steps.
  - `ResultsDashboard.jsx`: The main viewing portal featuring tabs for specific insights (Fraud, Five Cs, Research, Financials).

### **Backend: FastAPI + Python**
- **Tech Stack:** FastAPI, Pydantic, Uvicorn, LangChain, Groq, Tavily.
- **Core Endpoints:**
  - `POST /api/analyze`: The heavy-lifter. Takes in the structural documents, runs parsing, executes the multi-tool web agent, calculates the Five Cs scorecard, and returns the serialized JSON decision.
  - `POST /api/qualitative`: Accepts Credit Officer portal inputs and recalculates the Five Cs score on the fly.
  - `POST /api/generate-cam`: Generates a fully-formatted Word document (Credit Appraisal Memo) for final bank signatures.
  - `GET /api/health`: System status and API key validation.

---

## 🛠️ Requirements & Setup

### Prerequisites
- Python 3.9 or higher
- Node.js (v18+) and npm

### 1. Backend Setup
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Set up a Python virtual environment (recommended):
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```
3. Install all required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure Environment Variables:
   Create a `.env` file in the `backend/` directory and add your API keys for the LLM and search agents:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   *The API will be available at `http://localhost:8000` (Swagger UI at `/docs`).*

### 2. Frontend Setup
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Access the portal in your browser at `http://localhost:5174/` (or the port specified in your Vite output).

---

## 📂 Repository Structure

```
intelli-credit/
├── backend/                  # Python FastAPI Backend
│   ├── src/                  
│   │   ├── agents/           # LLM logic (Live Web Research Agent)
│   │   ├── ingestion/        # Parsers (Bank Statements, Annual Reports)
│   │   ├── scoring/          # Core Five Cs deterministic algorithmic engine
│   │   └── output/           # Word CAM generation logic
│   ├── main.py               # REST API endpoints and routing
│   └── requirements.txt      # Python dependencies block
├── frontend/                 # React Frontend
│   ├── src/
│   │   ├── components/       # Interface components (UploadPortal, ResultsDashboard)
│   │   ├── tabs/             # Dashboard sub-views (FraudTab, FiveCsTab, etc.)
│   │   ├── App.jsx           # Main React component & state management
│   │   └── index.css         # Global modern dark-theme styling variables
│   └── package.json          # Node dependencies and build scripts
└── data/                     # Mock data, GST/ITR samples, and testing banks
```

---

## 🛡️ License & Acknowledgements

*Disclaimer: All proprietary scoring models, fraud detection logic, and AI agents within this repository are proof-of-concept software. They should be thoroughly validated manually before any real-world financial deployment or corporate credit underwriting.*
