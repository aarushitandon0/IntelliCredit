"""
risk_adjuster.py
────────────────
Parses Credit Officer portal inputs and converts them into structured
score adjustments fed directly into the Five Cs scoring engine.

Two layers:
  1. Structured inputs  — dropdowns, sliders, toggles with predefined adjustments
  2. Free-text parsing  — Groq extracts risk signals from officer prose notes

The human layer makes the system defensible in an Indian banking regulatory
context. The AI recommends; the officer confirms; the memo is co-signed.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.utils.llm_client import extract_structured_data


# ─────────────────────────────────────────────────────────────
# ADJUSTMENT TABLES — deterministic rules, no ambiguity
# ─────────────────────────────────────────────────────────────

UTILIZATION_ADJUSTMENTS = [
    (0,  50,  "Capacity", -1.5, "Factory utilization < 50% — severe under-utilisation"),
    (50, 70,  "Capacity", -0.5, "Factory utilization 50–70% — below optimal"),
    (70, 101, "Capacity",  0.0, "Factory utilization ≥ 70% — acceptable"),
]

MANAGEMENT_ADJUSTMENTS = {
    "cooperative": ("Character",  0.0, "Management cooperative and transparent"),
    "adequate":    ("Character",  0.0, "Management adequate"),
    "evasive":     ("Character", -1.5, "Management evasive during due diligence interview"),
    "hostile":     ("Character", -3.0, "Management hostile — refused to answer key questions"),
}

MACHINERY_ADJUSTMENTS = {
    "new":     ("Collateral",  0.0,  "Machinery in new condition"),
    "good":    ("Collateral",  0.0,  "Machinery in good condition"),
    "aged":    ("Collateral", -1.0,  "Machinery aged or in poor condition"),
    "defunct": ("Collateral", -1.5,  "Machinery found defunct during site visit"),
}

INVENTORY_ADJUSTMENTS = {
    "normal":       ("Capacity",  0.0,  "Inventory levels as expected"),
    "low":          ("Capacity",  0.0,  "Low inventory — possible demand strength"),
    "high":         ("Capacity", -0.5,  "Inventory higher than stated — possible demand slowdown"),
    "very high":    ("Capacity", -1.0,  "Inventory piling up — demand problem or sales slowdown"),
}

ACTIVITY_ADJUSTMENTS = {
    "full":    ("Capacity",  0.0,  "Factory fully operational"),
    "partial": ("Capacity", -0.5,  "Factory partially operational"),
    "minimal": ("Capacity", -2.0,  "Minimal factory activity observed"),
    "shut":    ("Capacity", -3.0,  "Factory found shut or non-operational during site visit"),
}

BUSINESS_PLAN_ADJUSTMENTS = {
    "clear":       ("Capacity",  0.0,  "Business plan credible and clearly articulated"),
    "vague":       ("Capacity", -0.5,  "Business plan vague — insufficient detail"),
    "unrealistic": ("Capacity", -1.0,  "Business plan projections appear unrealistic"),
}


# ─────────────────────────────────────────────────────────────
# STRUCTURED INPUT PROCESSOR
# ─────────────────────────────────────────────────────────────

def process_structured_inputs(inputs: dict) -> dict:
    """
    inputs dict keys (all optional):
      factory_utilization_pct     int 0–100
      management_responsiveness   str: cooperative / adequate / evasive / hostile
      collateral_verified         bool
      machinery_condition         str: new / good / aged / defunct
      inventory_level             str: normal / low / high / very high
      factory_activity            str: full / partial / minimal / shut
      business_plan_credibility   str: clear / vague / unrealistic
      contradictions_noted        bool
      macro_outlook               str: positive / neutral / negative
      references_checked          bool
    """
    adjustments = []

    # Factory utilization
    util = inputs.get("factory_utilization_pct")
    if util is not None:
        for low, high, pillar, adj, reason in UTILIZATION_ADJUSTMENTS:
            if low <= util < high:
                if adj != 0:
                    adjustments.append({
                        "pillar":      pillar,
                        "sub_factor":  "Factory utilization",
                        "data_point":  f"{util}% observed utilization",
                        "source":      "Credit officer site visit",
                        "adjustment":  adj,
                        "reason":      reason,
                    })
                break

    # Management responsiveness
    mgmt = (inputs.get("management_responsiveness") or "").lower().strip()
    if mgmt and mgmt in MANAGEMENT_ADJUSTMENTS:
        pillar, adj, reason = MANAGEMENT_ADJUSTMENTS[mgmt]
        if adj != 0:
            adjustments.append({
                "pillar":     pillar,
                "sub_factor": "Management responsiveness",
                "data_point": f"Management assessed as: {mgmt}",
                "source":     "Credit officer management interview",
                "adjustment": adj,
                "reason":     reason,
            })

    # Collateral physical verification
    verified = inputs.get("collateral_verified")
    if verified is False:
        adjustments.append({
            "pillar":     "Collateral",
            "sub_factor": "Physical verification",
            "data_point": "Collateral not found at stated location during site visit",
            "source":     "Credit officer site visit",
            "adjustment": -3.0,
            "reason":     "Collateral not at site — security basis for facility eliminated",
        })
    elif verified is True:
        adjustments.append({
            "pillar":     "Collateral",
            "sub_factor": "Physical verification",
            "data_point": "Collateral verified at stated location",
            "source":     "Credit officer site visit",
            "adjustment": 0.0,
            "reason":     "No adjustment — collateral confirmed",
        })

    # Machinery condition
    machinery = (inputs.get("machinery_condition") or "").lower().strip()
    if machinery and machinery in MACHINERY_ADJUSTMENTS:
        pillar, adj, reason = MACHINERY_ADJUSTMENTS[machinery]
        if adj != 0:
            adjustments.append({
                "pillar":     pillar,
                "sub_factor": "Machinery condition",
                "data_point": f"Machinery condition: {machinery}",
                "source":     "Credit officer site visit",
                "adjustment": adj,
                "reason":     reason,
            })

    # Inventory level
    inventory = (inputs.get("inventory_level") or "").lower().strip()
    if inventory and inventory in INVENTORY_ADJUSTMENTS:
        pillar, adj, reason = INVENTORY_ADJUSTMENTS[inventory]
        if adj != 0:
            adjustments.append({
                "pillar":     pillar,
                "sub_factor": "Inventory level",
                "data_point": f"Inventory assessed as: {inventory}",
                "source":     "Credit officer site visit",
                "adjustment": adj,
                "reason":     reason,
            })

    # Factory activity
    activity = (inputs.get("factory_activity") or "").lower().strip()
    if activity and activity in ACTIVITY_ADJUSTMENTS:
        pillar, adj, reason = ACTIVITY_ADJUSTMENTS[activity]
        if adj != 0:
            adjustments.append({
                "pillar":     pillar,
                "sub_factor": "Factory activity level",
                "data_point": f"Factory observed as: {activity}",
                "source":     "Credit officer site visit",
                "adjustment": adj,
                "reason":     reason,
            })

    # Business plan credibility
    plan = (inputs.get("business_plan_credibility") or "").lower().strip()
    if plan and plan in BUSINESS_PLAN_ADJUSTMENTS:
        pillar, adj, reason = BUSINESS_PLAN_ADJUSTMENTS[plan]
        if adj != 0:
            adjustments.append({
                "pillar":     pillar,
                "sub_factor": "Business plan credibility",
                "data_point": f"Business plan assessed as: {plan}",
                "source":     "Credit officer management interview",
                "adjustment": adj,
                "reason":     reason,
            })

    # Contradictions
    if inputs.get("contradictions_noted"):
        adjustments.append({
            "pillar":     "Character",
            "sub_factor": "Interview contradictions",
            "data_point": "Material contradictions noted during management interview",
            "source":     "Credit officer management interview",
            "adjustment": -2.0,
            "reason":     "Contradictions in management responses — credibility concern",
        })

    # Macro outlook
    macro = (inputs.get("macro_outlook") or "").lower().strip()
    if macro == "negative":
        adjustments.append({
            "pillar":     "Conditions",
            "sub_factor": "Macro outlook",
            "data_point": "Credit officer assessed macro environment as negative",
            "source":     "Credit officer assessment",
            "adjustment": -1.5,
            "reason":     "Negative macro outlook — sector/economy headwinds",
        })
    elif macro == "positive":
        adjustments.append({
            "pillar":     "Conditions",
            "sub_factor": "Macro outlook",
            "data_point": "Credit officer assessed macro environment as positive",
            "source":     "Credit officer assessment",
            "adjustment": 0.5,
            "reason":     "Positive macro outlook",
        })

    # References
    if inputs.get("references_checked") is True:
        adjustments.append({
            "pillar":     "Character",
            "sub_factor": "Trade references",
            "data_point": "Trade and bank references checked and positive",
            "source":     "Credit officer reference check",
            "adjustment": 0.5,
            "reason":     "Positive reference check",
        })

    return {
        "structured_adjustments": adjustments,
        "total_structured_impact": sum(a["adjustment"] for a in adjustments),
    }


# ─────────────────────────────────────────────────────────────
# FREE-TEXT PARSER — Groq extracts risk signals from prose
# ─────────────────────────────────────────────────────────────

FREE_TEXT_PROMPT = """
You are a senior Indian credit officer reading field notes from a site visit and management interview.

Extract ALL risk signals. Be precise and conservative — only flag what is explicitly stated.

Return ONLY valid JSON:
{
    "signals": [
        {
            "signal":     "one sentence description of the risk",
            "pillar":     "Character / Capacity / Capital / Collateral / Conditions",
            "severity":   "HIGH / MEDIUM / LOW",
            "score_impact": number (negative for risk, positive for strength),
            "source":     "Site visit / Management interview / Officer observation"
        }
    ],
    "summary": "one sentence overall assessment from the notes"
}

Score impact guide:
  Major risk  (factory shut, fraud suspected)     → -2.0 to -3.0
  Moderate    (capacity low, evasion suspected)   → -1.0 to -1.5
  Minor       (minor anomaly)                     → -0.5
  Positive    (strong management, clean factory)  → +0.5
"""

def parse_free_text_notes(notes: str) -> dict:
    if not notes or not notes.strip():
        return {"signals": [], "summary": "No officer notes provided.", "total_text_impact": 0}

    print(f"  Parsing free-text notes ({len(notes)} chars)...")
    result = extract_structured_data(notes, FREE_TEXT_PROMPT)

    if not isinstance(result, dict) or "error" in result:
        print(f"  Free-text parse failed: {result}")
        return {"signals": [], "summary": "Parse failed.", "total_text_impact": 0}

    signals = result.get("signals") or []
    total   = sum(s.get("score_impact", 0) for s in signals)
    result["total_text_impact"] = total

    print(f"  Free-text: {len(signals)} signal(s) | total impact = {total}")
    for s in signals:
        print(f"    [{s.get('severity')}] {s.get('pillar')} {s.get('score_impact'):+.1f} — {s.get('signal')}")

    return result


# ─────────────────────────────────────────────────────────────
# MASTER ADJUSTER
# ─────────────────────────────────────────────────────────────

def process_qualitative_inputs(portal_inputs: dict) -> dict:
    """
    portal_inputs: full dict from the Credit Officer portal form.
    Includes both structured fields and free-text 'notes' field.

    Returns a unified qualitative dict consumed by five_cs_model.py.
    """
    print("\n  ─── Qualitative Adjustment ───")

    structured = process_structured_inputs(portal_inputs)
    notes_text = portal_inputs.get("notes", "") or portal_inputs.get("officer_notes", "")
    free_text  = parse_free_text_notes(notes_text)

    all_adjustments = structured["structured_adjustments"] + [
        {
            "pillar":     s["pillar"],
            "sub_factor": s["signal"],
            "data_point": s["signal"],
            "source":     s.get("source", "Officer notes"),
            "adjustment": s.get("score_impact", 0),
            "reason":     f"Extracted from officer notes — {s.get('severity', 'MEDIUM')} severity",
        }
        for s in free_text.get("signals", [])
    ]

    total_impact = sum(a["adjustment"] for a in all_adjustments)

    print(f"  Structured adjustments : {len(structured['structured_adjustments'])}")
    print(f"  Free-text signals      : {len(free_text.get('signals', []))}")
    print(f"  Total qualitative impact: {total_impact:+.1f} pts")

    # Build the qualitative dict passed to five_cs_model
    return {
        "factory_utilization_pct":   portal_inputs.get("factory_utilization_pct"),
        "collateral_verified":        portal_inputs.get("collateral_verified"),
        "management_responsiveness":  portal_inputs.get("management_responsiveness", "adequate"),
        "machinery_condition":        portal_inputs.get("machinery_condition", "good"),
        "inventory_level":            portal_inputs.get("inventory_level", "normal"),
        "factory_activity":           portal_inputs.get("factory_activity", "full"),
        "contradictions_noted":       portal_inputs.get("contradictions_noted", False),
        "macro_outlook":              portal_inputs.get("macro_outlook", "neutral"),
        "references_checked":         portal_inputs.get("references_checked", False),
        "officer_notes_summary":      free_text.get("summary", ""),
        "all_adjustments":            all_adjustments,
        "total_qualitative_impact":   total_impact,
        "structured_impact":          structured["total_structured_impact"],
        "free_text_impact":           free_text.get("total_text_impact", 0),
    }