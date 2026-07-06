"""
Human-in-the-Loop (HITL) Review Node.

Halts the workflow execution to solicit founder feedback/review of the generated
analysis and plans before proceeding to Phase 4.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput

__all__ = ["hitl_review_node"]


async def hitl_review_node(
    ctx: Context, node_input: dict
) -> AsyncGenerator[RequestInput | Event, None]:
    """Halt the workflow to request founder review of the generated plans.

    Routes to:
      - 'approved' to proceed to Growth, Simulation, and Pitch Deck.
      - 'minor_revision' to route back to the Product Agent.
      - 'major_revision' to route back to the Research Agent.
    """
    # Check if we have received the human input yet
    if not ctx.resume_inputs or "founder_review" not in ctx.resume_inputs:
        summary = (
            "=== STARTUP COPILOT REVIEW COMPONENT ===\n"
            f"MVP Scope: {node_input.get('product', {}).get('mvp_scope', [])}\n\n"
            f"Finance Projections: {node_input.get('finance', {}).get('three_year_projections', {})}\n\n"
            f"Devil's Advocate Critique: {node_input.get('advocate', {}).get('brutal_truth', '')}\n\n"
            f"Investor Score: {node_input.get('investor', {}).get('investment_readiness_score', 0)}/100\n"
            "=========================================\n\n"
            "Please review the startup summary. Enter your response in format:\n"
            "status: <approved/minor_revision/major_revision>\n"
            "comments: <your feedback>"
        )
        yield RequestInput(interrupt_id="founder_review", message=summary)
        return

    # Process response
    response_text = ctx.resume_inputs["founder_review"]
    status = "approved"
    comments = response_text

    # Simple parsing logic
    lower_text = response_text.lower()
    if "major_revision" in lower_text:
        status = "major_revision"
    elif "minor_revision" in lower_text:
        status = "minor_revision"

    yield Event(
        output={"status": status, "comments": comments},
        route=status,
        state={"founder_feedback": comments},
    )
