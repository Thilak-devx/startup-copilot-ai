"""
Orchestrator Node — tracks workflow state, handles retries, routes decisions,
and logs execution telemetry to ctx.state.

Architecture rationale:
  The orchestrator is a plain FunctionNode placed at two natural decision gates:
    1. After Phase 3 state_writer (before HITL) — gate for revision routing.
    2. After Phase 4 state_writer (before Security) — gate for completion.

  It does NOT block the graph or add extra edges — it runs synchronously,
  writes telemetry to ctx.state, and passes the input downstream unchanged.

  By keeping orchestration as a FunctionNode (not a separate agent), we avoid
  LLM latency at gate checkpoints and keep the logic fully deterministic.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from google.adk.agents.context import Context
from google.adk.events.event import Event

logger = logging.getLogger(__name__)

# Maximum retries before the orchestrator raises (prevents infinite loops)
MAX_RETRIES: int = 3

# Confidence threshold: below this, the orchestrator logs a warning
LOW_CONFIDENCE_THRESHOLD: int = 60


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _avg(*scores: int | float | None) -> float:
    """Compute the mean of numeric scores, silently skipping None values."""
    vals = [s for s in scores if isinstance(s, (int, float))]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 Gate — called before HITL
# ─────────────────────────────────────────────────────────────────────────────


def orchestrator_phase3_gate(ctx: Context, node_input: Any) -> Event:
    """Orchestrator checkpoint after Phase 3 (Advocate + Investor).

    Responsibilities:
    - Increment phase3_retry_count if this is a re-run (HITL loopback).
    - Raise if retry count exceeds MAX_RETRIES.
    - Compute average confidence for Phase 1–3 and flag if below threshold.
    - Log the HITL routing decision rationale.
    - Write orchestrator_gate3_log to ctx.state.
    """
    retry_count: int = ctx.state.get("phase3_retry_count", 0)

    if ctx.state.get("hitl_revision_requested", False):
        retry_count += 1
        if retry_count > MAX_RETRIES:
            raise RuntimeError(
                f"Orchestrator: Phase 3 gate exceeded {MAX_RETRIES} retries. "
                "Workflow halted to prevent an infinite revision loop."
            )

    p1_research = ctx.state.get("phase1_research_confidence", 75)
    p1_risk = ctx.state.get("phase1_risk_confidence", 75)
    p2_product = ctx.state.get("phase2_product_confidence", 75)
    p2_finance = ctx.state.get("phase2_finance_confidence", 75)
    p3_advocate = ctx.state.get("phase3_advocate_confidence", 75)
    p3_investor = ctx.state.get("phase3_investor_confidence", 75)

    avg_confidence = _avg(
        p1_research, p1_risk, p2_product, p2_finance, p3_advocate, p3_investor
    )
    inv_score = ctx.state.get("investment_readiness_score", 0)
    inv_reco = ctx.state.get("investor_recommendation", "Unknown")

    warnings: list[str] = []
    if avg_confidence < LOW_CONFIDENCE_THRESHOLD:
        warnings.append(
            f"Low average confidence ({avg_confidence}/100) — founder review recommended."
        )
    if inv_score < 50:
        warnings.append(
            f"Investment readiness score is low ({inv_score}/100) — "
            "consider major_revision before HITL approval."
        )

    warning_str = (
        " WARNINGS: " + " | ".join(warnings) if warnings else "All signals nominal."
    )
    decision = (
        f"Routing to HITL. Investor verdict: '{inv_reco}'. "
        f"Average confidence: {avg_confidence}/100." + warning_str
    )

    gate_log = {
        "gate": "phase3",
        "timestamp": _now(),
        "retry_count": retry_count,
        "avg_confidence": avg_confidence,
        "inv_score": inv_score,
        "inv_reco": inv_reco,
        "warnings": warnings,
        "decision": decision,
    }

    logger.info("[Orchestrator Gate 3] %s", decision)

    return Event(
        output=node_input,
        state={
            "phase3_retry_count": retry_count,
            "hitl_revision_requested": False,  # reset after read
            "orchestrator_gate3_log": json.dumps(gate_log, default=str),
            "orchestrator_avg_confidence_p1_p3": avg_confidence,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 Gate — called before Security (after join4)
# ─────────────────────────────────────────────────────────────────────────────


def orchestrator_phase4_gate(ctx: Context, node_input: Any) -> Event:
    """Orchestrator checkpoint after Phase 4 (Growth + Simulator + PitchDeck).

    Responsibilities:
    - Aggregate all phase confidence scores into a preliminary overall score.
    - Flag anomalies (e.g. growth score diverges sharply from investor score).
    - Log completion telemetry before the security checkpoint.
    - Write orchestrator_gate4_log to ctx.state.
    """
    p1_research = ctx.state.get("phase1_research_confidence", 75)
    p1_risk = ctx.state.get("phase1_risk_confidence", 75)
    p2_product = ctx.state.get("phase2_product_confidence", 75)
    p2_finance = ctx.state.get("phase2_finance_confidence", 75)
    p3_advocate = ctx.state.get("phase3_advocate_confidence", 75)
    p3_investor = ctx.state.get("phase3_investor_confidence", 75)
    p4_growth = ctx.state.get("phase4_growth_confidence", 75)
    p4_simulator = ctx.state.get("phase4_simulator_confidence", 75)
    p4_pitchdeck = ctx.state.get("phase4_pitchdeck_confidence", 75)

    avg_all = _avg(
        p1_research,
        p1_risk,
        p2_product,
        p2_finance,
        p3_advocate,
        p3_investor,
        p4_growth,
        p4_simulator,
        p4_pitchdeck,
    )

    startup_score = ctx.state.get("startup_score", 0)
    inv_score = ctx.state.get("investment_readiness_score", 0)

    anomalies: list[str] = []
    if abs(startup_score - inv_score) > 25:
        anomalies.append(
            f"Score divergence: startup_score={startup_score} vs "
            f"investment_readiness={inv_score}. Agents may have disagreed on fundamentals."
        )
    if p4_growth < LOW_CONFIDENCE_THRESHOLD:
        anomalies.append(
            f"Growth agent confidence is low ({p4_growth}/100). "
            "GTM strategy may need founder validation."
        )

    anomaly_str = (
        "ANOMALIES: " + " | ".join(anomalies) if anomalies else "No anomalies detected."
    )
    decision = (
        f"Phase 4 complete. Preliminary overall confidence: {avg_all}/100. "
        f"Startup score: {startup_score}/100. " + anomaly_str
    )

    gate_log = {
        "gate": "phase4",
        "timestamp": _now(),
        "avg_confidence": avg_all,
        "startup_score": startup_score,
        "inv_score": inv_score,
        "anomalies": anomalies,
        "decision": decision,
        "confidence_breakdown": {
            "research": p1_research,
            "risk": p1_risk,
            "product": p2_product,
            "finance": p2_finance,
            "advocate": p3_advocate,
            "investor": p3_investor,
            "growth": p4_growth,
            "simulator": p4_simulator,
            "pitchdeck": p4_pitchdeck,
        },
    }

    logger.info("[Orchestrator Gate 4] %s", decision)

    return Event(
        output=node_input,
        state={
            "orchestrator_gate4_log": json.dumps(gate_log, default=str),
            "orchestrator_avg_confidence_all": avg_all,
        },
    )
