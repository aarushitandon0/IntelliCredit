"""
test_agent.py
─────────────
Run this from backend/ with:  python test_agent.py
"""

import sys
import json
sys.path.insert(0, ".")

from src.agents.research_agent import run_research_agent

result = run_research_agent(
    company_name = "Videocon Industries",
    sector       = "Consumer Electronics",
    directors    = [{"name": "Venugopal Dhoot", "din": ""}],
)


print("\n\n══ FINAL FLAGS ══")
print(json.dumps(result["risk_flags"], indent=2))

print(f"\n══ SCORE IMPACT ══")
print(f"Total: {result['total_score_impact']:+.1f} pts")
print(f"HIGH:  {result['high_count']}")
print(f"MED:   {result['medium_count']}")