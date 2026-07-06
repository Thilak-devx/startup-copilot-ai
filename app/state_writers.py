"""
State Writer Nodes — thin FunctionNode-compatible functions.

Placed after each JoinNode, these functions extract agent outputs from the join
dict, serialise them into human-readable summary strings, and write them to
ctx.state so that later agents can consume them via dynamic instructions.

Architecture rationale:
  JoinNode aggregates parallel node outputs into a dict keyed by agent name.
  StateWriters transform that raw dict into named ctx.state keys that dynamic
  instruction callables can format into their prompts.  This keeps the
  serialisation concern separate from both the agents and the orchestrator.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from google.adk.agents.context import Context
from google.adk.events.event import Event

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _safe_get(data: Any, key: str, default: Any = None) -> Any:
    """Safely retrieve *key* from a dict or attribute *key* from an object."""
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def _to_readable(obj: Any) -> str:
    """Convert a Pydantic model or dict to a compact, human-readable JSON string."""
    if obj is None:
        return "Not available."
    raw: Any
    if hasattr(obj, "model_dump"):
        raw = obj.model_dump()
    elif isinstance(obj, dict):
        raw = obj
    else:
        return str(obj)
    try:
        return json.dumps(raw, indent=2, default=str)
    except (TypeError, ValueError):
        logger.warning(
            "_to_readable: could not JSON-serialise %s, falling back to str()",
            type(obj),
        )
        return str(raw)


def _extract_confidence(obj: Any, default: int = 75) -> int:
    """Pull the confidence_score from a model or dict, with range-checked fallback."""
    score = _safe_get(obj, "confidence_score", default)
    if isinstance(score, int) and 0 <= score <= 100:
        return score
    return default


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 State Writer — after join1 (research_agent + risk_agent)
# ─────────────────────────────────────────────────────────────────────────────


def state_writer_phase1(ctx: Context, node_input: Any) -> Event:
    """Persist Phase 1 (Research + Risk) outputs to ctx.state.

    Written keys:
      phase1_research_summary, phase1_risk_summary,
      phase1_research_confidence, phase1_risk_confidence,
      phase1_completed_at
    """
    research = _safe_get(node_input, "research_agent")
    risk = _safe_get(node_input, "risk_agent")

    state: dict[str, Any] = {
        "phase1_research_summary": _to_readable(research),
        "phase1_risk_summary": _to_readable(risk),
        "phase1_research_confidence": _extract_confidence(research),
        "phase1_risk_confidence": _extract_confidence(risk),
        "phase1_completed_at": datetime.now(UTC).isoformat(),
    }
    logger.debug("state_writer_phase1: wrote keys %s", list(state))
    return Event(output=node_input, state=state)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 State Writer — after join2 (product_agent + finance_agent)
# ─────────────────────────────────────────────────────────────────────────────


def state_writer_phase2(ctx: Context, node_input: Any) -> Event:
    """Persist Phase 2 (Product + Finance) outputs to ctx.state.

    Written keys:
      phase2_product_summary, phase2_finance_summary,
      phase2_product_confidence, phase2_finance_confidence,
      phase2_completed_at
    """
    product = _safe_get(node_input, "product_agent")
    finance = _safe_get(node_input, "finance_agent")

    state: dict[str, Any] = {
        "phase2_product_summary": _to_readable(product),
        "phase2_finance_summary": _to_readable(finance),
        "phase2_product_confidence": _extract_confidence(product),
        "phase2_finance_confidence": _extract_confidence(finance),
        "phase2_completed_at": datetime.now(UTC).isoformat(),
    }
    logger.debug("state_writer_phase2: wrote keys %s", list(state))
    return Event(output=node_input, state=state)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 State Writer — after join3 (advocate_agent + investor_agent)
# ─────────────────────────────────────────────────────────────────────────────


def state_writer_phase3(ctx: Context, node_input: Any) -> Event:
    """Persist Phase 3 (Advocate + Investor) outputs to ctx.state.

    Written keys:
      phase3_advocate_summary, phase3_investor_summary,
      phase3_advocate_confidence, phase3_investor_confidence,
      investment_readiness_score, investor_recommendation,
      phase3_completed_at
    """
    advocate = _safe_get(node_input, "advocate_agent")
    investor = _safe_get(node_input, "investor_agent")

    inv_score = _safe_get(investor, "investment_readiness_score", 0)
    inv_reco = _safe_get(investor, "investment_recommendation", "Not yet determined.")

    state: dict[str, Any] = {
        "phase3_advocate_summary": _to_readable(advocate),
        "phase3_investor_summary": _to_readable(investor),
        "phase3_advocate_confidence": _extract_confidence(advocate),
        "phase3_investor_confidence": _extract_confidence(investor),
        "investment_readiness_score": inv_score,
        "investor_recommendation": inv_reco,
        "phase3_completed_at": datetime.now(UTC).isoformat(),
    }
    logger.debug("state_writer_phase3: wrote keys %s", list(state))
    return Event(output=node_input, state=state)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 State Writer — after join4 (growth + simulator + pitchdeck)
# ─────────────────────────────────────────────────────────────────────────────


def state_writer_phase4(ctx: Context, node_input: Any) -> Event:
    """Persist Phase 4 (Growth + Simulator + PitchDeck) outputs to ctx.state.

    Written keys:
      phase4_growth_summary, phase4_simulator_summary, phase4_pitchdeck_summary,
      phase4_growth_confidence, phase4_simulator_confidence, phase4_pitchdeck_confidence,
      startup_score, phase4_completed_at
    """
    growth = _safe_get(node_input, "growth_agent")
    simulator = _safe_get(node_input, "simulator_agent")
    pitchdeck = _safe_get(node_input, "pitchdeck_agent")

    startup_score = _safe_get(growth, "startup_score", 0)

    state: dict[str, Any] = {
        "phase4_growth_summary": _to_readable(growth),
        "phase4_simulator_summary": _to_readable(simulator),
        "phase4_pitchdeck_summary": _to_readable(pitchdeck),
        "phase4_growth_confidence": _extract_confidence(growth),
        "phase4_simulator_confidence": _extract_confidence(simulator),
        "phase4_pitchdeck_confidence": _extract_confidence(pitchdeck),
        "startup_score": startup_score,
        "phase4_completed_at": datetime.now(UTC).isoformat(),
    }
    logger.debug("state_writer_phase4: wrote keys %s", list(state))
    return Event(output=node_input, state=state)


# ─────────────────────────────────────────────────────────────────────────────
# Security State Writer — after security_agent
# ─────────────────────────────────────────────────────────────────────────────


def state_writer_security(ctx: Context, node_input: Any) -> Event:
    """Persist the Security checkpoint output to ctx.state.

    Written keys:
      phase4_security_summary, phase4_security_confidence, is_safe, sanitized_report
    """
    is_safe = _safe_get(node_input, "is_safe", True)
    san_report = _safe_get(node_input, "sanitized_report", "")

    state: dict[str, Any] = {
        "phase4_security_summary": _to_readable(node_input),
        "phase4_security_confidence": _extract_confidence(node_input),
        "is_safe": is_safe,
        "sanitized_report": san_report,
    }
    logger.debug("state_writer_security: is_safe=%s", is_safe)
    return Event(output=node_input, state=state)
