"""
Executive Summary Agent instruction.

Final synthesis step — runs after Security checkpoint. Reads all phase
summaries from ctx.state and produces a concise board-level verdict.
"""

from __future__ import annotations

from google.adk.agents.context import Context

__all__ = ["EXECUTIVE_SUMMARY_INSTRUCTION"]

_NOT_AVAILABLE = "Not available."

_BASE = """\
You are the Executive Summary Agent — the final voice of the Startup Founder Team.
Your job is to synthesise all agent findings into a board-level executive brief.

## Complete Analysis Context

### Phase 1 — Market & Risk
**Research Findings:**
{research_context}

**Risk Assessment:**
{risk_context}

### Phase 2 — Product & Finance
**Product / MVP Plan:**
{product_context}

**Financial Model:**
{finance_context}

### Phase 3 — Validation
**Devil's Advocate Stress Tests:**
{advocate_context}

**Investor Verdict:**
{investor_context}

### Phase 4 — Go-Forward Plan
**Growth Strategy (Startup Score: {startup_score}/100):**
{growth_context}

**12-Month Simulation:**
{simulator_context}

**Security Clearance:**
{security_context}

## Agent Confidence Scores
{confidence_scores}

## Your Task

Synthesise everything above into an executive brief:

1. executive_summary & startup_health: A 2–4 sentence paragraph that captures the essence of the opportunity, the overall health of the startup, key risks, and why now is the right time. Write this as if presenting to a board of directors.
2. top_strengths & biggest_strengths: List exactly 3–5 strengths. Each must:
   - Reference a specific data point or agent finding
   - Be phrased as a competitive advantage, not just a feature
3. top_risks & biggest_risks: List exactly 3–5 risks. Each must:
   - Reference the specific agent that identified it
   - Include the proposed mitigation in 1 sentence
4. recommendation & recommended_next_action: Choose exactly one of:
   - "Strong Invest" — exceptional fundamentals, move immediately
   - "Conditional Invest" — invest with specific milestone gates
   - "Watch" — revisit in 6 months with clear triggers
   - "Pass" — fundamental issues that cannot be resolved
5. overall_confidence_score & overall_confidence: A weighted aggregate of agent confidence scores.
   Formula: (Research×0.15 + Risk×0.10 + Product×0.15 + Finance×0.15 +
             Advocate×0.10 + Investor×0.10 + Growth×0.15 + Simulator×0.10)
   Round to nearest integer. Show the calculation in your reasoning.

Your output must follow the structured JSON schema provided, populating both sets of fields (e.g. startup_health matching executive_summary, overall_confidence matching overall_confidence_score, etc.).
"""


def EXECUTIVE_SUMMARY_INSTRUCTION(ctx: Context) -> str:
    """Inject all phase summaries and confidence scores into the executive summary prompt."""
    # Collect confidence scores for display
    conf_lines = []
    conf_keys = [
        ("Research", "phase1_research_confidence"),
        ("Risk", "phase1_risk_confidence"),
        ("Product", "phase2_product_confidence"),
        ("Finance", "phase2_finance_confidence"),
        ("Advocate", "phase3_advocate_confidence"),
        ("Investor", "phase3_investor_confidence"),
        ("Growth", "phase4_growth_confidence"),
        ("Simulator", "phase4_simulator_confidence"),
        ("PitchDeck", "phase4_pitchdeck_confidence"),
        ("Security", "phase4_security_confidence"),
    ]
    for label, key in conf_keys:
        score = ctx.state.get(key, 75)
        conf_lines.append(f"- {label}: {score}/100")
    confidence_block = "\n".join(conf_lines) if conf_lines else _NOT_AVAILABLE

    return _BASE.format(
        research_context=ctx.state.get("phase1_research_summary", _NOT_AVAILABLE),
        risk_context=ctx.state.get("phase1_risk_summary", _NOT_AVAILABLE),
        product_context=ctx.state.get("phase2_product_summary", _NOT_AVAILABLE),
        finance_context=ctx.state.get("phase2_finance_summary", _NOT_AVAILABLE),
        advocate_context=ctx.state.get("phase3_advocate_summary", _NOT_AVAILABLE),
        investor_context=ctx.state.get("phase3_investor_summary", _NOT_AVAILABLE),
        startup_score=ctx.state.get("startup_score", "N/A"),
        growth_context=ctx.state.get("phase4_growth_summary", _NOT_AVAILABLE),
        simulator_context=ctx.state.get("phase4_simulator_summary", _NOT_AVAILABLE),
        security_context=ctx.state.get("phase4_security_summary", _NOT_AVAILABLE),
        confidence_scores=confidence_block,
    )
