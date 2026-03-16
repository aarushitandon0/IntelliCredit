"""
research_agent.py
─────────────────
Autonomous research agent for corporate credit appraisal.

Uses LangChain tool-calling with Groq LLaMA 3.3 70B as the reasoning model
and Tavily as the live web search backbone.

Four specialized search tools:
  1. News Tool     — adverse news, DGGI/GST notices, fraud, NPA coverage
  2. MCA Tool      — director DIN cross-check, company status, charge registry
  3. eCourts Tool  — litigation, NCLT/IBC proceedings, criminal cases
  4. Sector Tool   — RBI regulations, sector headwinds, industry stress

Every finding returned includes:
  - source URL (verifiable, clickable)
  - severity classification (HIGH / MEDIUM / LOW)
  - plain-English description
  - score impact for Five Cs model

Nothing is fabricated. Every flag has a source.
"""

import os
import json
import re
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
# IMPORTS — graceful error if packages missing
# ─────────────────────────────────────────────────────────────

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("  WARNING: tavily-python not installed. Run: pip install tavily-python")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("  WARNING: groq not installed. Run: pip install groq")


# ─────────────────────────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────────────────────────

def _get_tavily():
    if not TAVILY_AVAILABLE:
        raise RuntimeError("tavily-python not installed")
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY not set in .env")
    return TavilyClient(api_key=api_key)

def _get_groq():
    if not GROQ_AVAILABLE:
        raise RuntimeError("groq not installed")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in .env")
    return Groq(api_key=api_key)


# ─────────────────────────────────────────────────────────────
# SEARCH TOOLS — each returns list of {title, url, content}
# ─────────────────────────────────────────────────────────────

def _search(query: str, max_results: int = 5) -> list[dict]:
    """Core Tavily search — returns raw results."""
    try:
        client = _get_tavily()
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=False,
        )
        results = response.get("results", [])
        return [
            {
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "content": r.get("content", "")[:800],  # cap per result
            }
            for r in results
        ]
    except Exception as e:
        print(f"  Search error for '{query}': {e}")
        return []


def search_news(company_name: str, promoter_names: list[str] = None) -> list[dict]:
    """Search for adverse news about the company and its promoters."""
    results = []

    # Company-level queries
    company_queries = [
        f'"{company_name}" fraud OR NPA OR NCLT OR insolvency OR "ED raid" India',
        f'"{company_name}" "GST notice" OR DGGI OR "income tax" OR enforcement 2024 2025',
        f'"{company_name}" default OR "loan recall" OR "wilful defaulter"',
    ]

    for q in company_queries:
        results.extend(_search(q, max_results=3))

    # Promoter-level queries
    for name in (promoter_names or []):
        if not name or len(name) < 4:
            continue
        pq = f'"{name}" NPA OR default OR fraud OR "court case" OR arrested OR FIR India'
        results.extend(_search(pq, max_results=2))

    return _deduplicate(results)


def search_mca(company_name: str, director_dins: list[dict] = None) -> list[dict]:
    """Search MCA records — company status, charges, director DIN cross-check."""
    results = []

    # Company MCA status
    results.extend(_search(
        f'"{company_name}" MCA company status struck off insolvency India',
        max_results=3
    ))

    # Director DIN cross-check — the most powerful signal
    for director in (director_dins or []):
        name = director.get("name", "")
        din  = director.get("din", "")
        if not name:
            continue

        # Search by name + DIN
        if din:
            results.extend(_search(
                f'DIN {din} "{name}" NPA default insolvency struck-off India',
                max_results=2
            ))

        # Search by name alone for NPA associations
        results.extend(_search(
            f'"{name}" director NPA "non-performing asset" company India',
            max_results=2
        ))

    return _deduplicate(results)


def search_ecourts(company_name: str, director_names: list[str] = None) -> list[dict]:
    """Search for litigation — civil cases, criminal cases, NCLT/IBC proceedings."""
    results = []

    results.extend(_search(
        f'"{company_name}" NCLT IBC insolvency petition India',
        max_results=3
    ))
    results.extend(_search(
        f'"{company_name}" court case lawsuit defendant India',
        max_results=3
    ))

    for name in (director_names or []):
        if not name or len(name) < 4:
            continue
        results.extend(_search(
            f'"{name}" criminal case FIR arrested India director',
            max_results=2
        ))

    return _deduplicate(results)


def search_sector(sector: str) -> list[dict]:
    """Search for sector-level headwinds and regulatory risks."""
    results = []

    results.extend(_search(
        f'"{sector}" India RBI regulation 2024 2025 headwinds NPA stress',
        max_results=3
    ))
    results.extend(_search(
        f'"{sector}" India "import duty" OR "demand slowdown" OR "margin pressure" 2024',
        max_results=2
    ))
    results.extend(_search(
        f'"{sector}" India banking credit risk sector stress 2024 2025',
        max_results=2
    ))

    return _deduplicate(results)


def _deduplicate(results: list[dict]) -> list[dict]:
    """Remove duplicate URLs."""
    seen = set()
    unique = []
    for r in results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)
    return unique


# ─────────────────────────────────────────────────────────────
# LLM CLASSIFIER — Groq classifies raw results into risk flags
# ─────────────────────────────────────────────────────────────

CLASSIFY_PROMPT = """
You are a senior Indian credit officer reviewing web research results.
Classify each finding into a structured risk flag.

SEVERITY GUIDE:
  HIGH:   NCLT/IBC filing, DGGI notice, director NPA, wilful defaulter, criminal case, ED raid
  MEDIUM: Adverse news, tax dispute, civil litigation, sector headwind, rating downgrade
  LOW:    Minor mention, old resolved case, general sector commentary
  NONE:   Not relevant to credit risk — skip entirely

SCORE IMPACT GUIDE (negative = risk):
  Director NPA association:     -3.5
  NCLT/IBC filing:              -4.0
  DGGI/GST enforcement notice:  -2.0
  Wilful defaulter listing:     -4.0
  Criminal case against director: -2.5
  HIGH adverse news:            -2.0
  MEDIUM adverse news:          -1.0
  Sector headwind HIGH:         -1.5
  Sector headwind MEDIUM:       -0.5

Return ONLY valid JSON array. No markdown. No explanation.
[
  {
    "type":        "DIRECTOR_NPA / NCLT / DGGI_NOTICE / ADVERSE_NEWS / SECTOR_HEADWIND / LITIGATION / WILFUL_DEFAULTER / OTHER",
    "severity":    "HIGH / MEDIUM / LOW",
    "title":       "one line — specific and factual",
    "description": "2-3 sentences — what was found and why it matters for credit",
    "source":      "publication name or website",
    "source_url":  "exact URL",
    "date":        "date if found, else null",
    "score_impact": number,
    "pillar":      "Character / Conditions / Collateral"
  }
]
If no relevant risks found, return empty array: []
"""

def _classify_results(raw_results: list[dict], context: str = "") -> list[dict]:
    """Pass raw search results through Groq for risk classification."""
    if not raw_results:
        return []

    # Build text block for LLM
    text = f"Company/Context: {context}\n\n"
    for i, r in enumerate(raw_results[:15]):  # cap at 15 results
        text += f"[{i+1}] Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}\n\n"

    try:
        client = _get_groq()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CLASSIFY_PROMPT},
                {"role": "user",   "content": text[:12000]},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        flags = json.loads(raw)
        for f in flags:
            try:
                f["score_impact"] = float(f.get("score_impact", 0) or 0)
            except (ValueError, TypeError):
                f["score_impact"] = 0.0
        
        if not isinstance(flags, list):
            return []

        # Filter out NONE severity and low-quality results
        return [
            f for f in flags
            if f.get("severity") in ("HIGH", "MEDIUM", "LOW")
            and f.get("title")
            and f.get("source_url")
        ]

    except json.JSONDecodeError:
        print(f"  LLM classification JSON parse failed")
        return []
    except Exception as e:
        print(f"  LLM classification error: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# MASTER RESEARCH AGENT
# ─────────────────────────────────────────────────────────────

def run_research_agent(
    company_name:    str,
    cin:             str = "",
    sector:          str = "",
    directors:       list[dict] = None,
    max_iterations:  int = 12,
) -> dict:
    """
    Autonomous research agent — runs all four search tools,
    classifies findings, and returns structured risk flags.

    directors: list of {"name": str, "din": str} from pdf_parser output
    """

    print(f"\n  ─── Research Agent ───")
    print(f"  Company : {company_name}")
    print(f"  Sector  : {sector or 'Not specified'}")
    print(f"  Directors: {len(directors or [])} to cross-check")
    print(f"  Starting autonomous search (max {max_iterations} queries)...")

    director_names = [d.get("name", "") for d in (directors or [])]
    all_raw        = []
    iterations     = 0

    # Tool 1 — News
    print(f"  [1/4] News search — company + promoters...")
    news_results = search_news(company_name, director_names)
    all_raw.extend(news_results)
    iterations += len([company_name] + director_names[:3])
    print(f"        {len(news_results)} result(s) found")

    # Tool 2 — MCA
    print(f"  [2/4] MCA search — director DIN cross-check...")
    mca_results = search_mca(company_name, directors or [])
    all_raw.extend(mca_results)
    iterations += 1 + len((directors or [])[:4])
    print(f"        {len(mca_results)} result(s) found")

    # Tool 3 — eCourts
    print(f"  [3/4] eCourts search — litigation + NCLT...")
    court_results = search_ecourts(company_name, director_names)
    all_raw.extend(court_results)
    iterations += 2
    print(f"        {len(court_results)} result(s) found")

    # Tool 4 — Sector
    if sector:
        print(f"  [4/4] Sector search — {sector}...")
        sector_results = search_sector(sector)
        all_raw.extend(sector_results)
        iterations += 3
        print(f"        {len(sector_results)} result(s) found")
    else:
        sector_results = []
        print(f"  [4/4] Sector search — skipped (no sector provided)")

    print(f"\n  Total raw results  : {len(all_raw)}")
    print(f"  Total queries run  : {iterations}")
    print(f"  Classifying with Groq LLaMA 3.3...")

    # Classify news + MCA + courts together
    company_flags = _classify_results(
        news_results + mca_results + court_results,
        context=f"{company_name} | CIN: {cin} | Directors: {', '.join(director_names[:5])}"
    )

    # Classify sector separately
    sector_flags = _classify_results(
        sector_results,
        context=f"Sector: {sector} | India credit risk assessment"
    ) if sector_results else []

    # Separate company vs sector flags
    all_flags   = company_flags + sector_flags
    high_flags  = [f for f in all_flags if f.get("severity") == "HIGH"]
    med_flags   = [f for f in all_flags if f.get("severity") == "MEDIUM"]
    low_flags   = [f for f in all_flags if f.get("severity") == "LOW"]

    total_score_impact = sum(float(f.get("score_impact", 0) or 0) for f in all_flags)

    print(f"\n  ─── Research Summary ───")
    print(f"  HIGH flags   : {len(high_flags)}")
    print(f"  MEDIUM flags : {len(med_flags)}")
    print(f"  LOW flags    : {len(low_flags)}")
    print(f"  Score impact : {total_score_impact:+.1f} pts")

    for f in high_flags:
        print(f"  🔴 {f.get('title')} | {f.get('source')} | {float(f.get('score_impact', 0))} pts")
    for f in med_flags:
        print(f"  🟡 {f.get('title')} | {f.get('source')} | {float(f.get('score_impact', 0))} pts")

    return {
        "company_name":        company_name,
        "cin":                 cin,
        "sector":              sector,
        "total_queries_run":   iterations,
        "total_results_found": len(all_raw),
        "risk_flags":          all_flags,
        "company_flags":       company_flags,
        "sector_flags":        sector_flags,
        "high_count":          len(high_flags),
        "medium_count":        len(med_flags),
        "low_count":           len(low_flags),
        "total_score_impact":  total_score_impact,
    }