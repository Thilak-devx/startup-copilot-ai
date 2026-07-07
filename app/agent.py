# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Startup Copilot AI — main agent wiring.

Collaborative multi-agent architecture:
  - Every Phase 2+ agent receives prior-phase context via dynamic instructions
    (callable `instruction` that reads from ctx.state at runtime).
  - StateWriter FunctionNodes after each JoinNode persist structured summaries
    to ctx.state, making cross-agent communication explicit and auditable.
  - Two Orchestrator gates (at Phase 3 and Phase 4 boundaries) provide retry
    detection, confidence aggregation, and anomaly flagging.
  - ExecutiveSummary agent synthesises all outputs into a board-level verdict
    with an overall confidence score.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

import google.auth
import nest_asyncio
from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps import App
from google.adk.events.event import Event
from google.adk.models import Gemini
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.workflow import JoinNode, Workflow
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.nodes.advocate import ADVOCATE_INSTRUCTION
from app.nodes.executive_summary import EXECUTIVE_SUMMARY_INSTRUCTION
from app.nodes.finance import FINANCE_INSTRUCTION
from app.nodes.growth import GROWTH_INSTRUCTION
from app.nodes.investor import INVESTOR_INSTRUCTION
from app.nodes.pitchdeck import PITCHDECK_INSTRUCTION
from app.nodes.product import PRODUCT_INSTRUCTION
from app.nodes.research import RESEARCH_INSTRUCTION
from app.nodes.review import hitl_review_node
from app.nodes.risk import RISK_INSTRUCTION
from app.nodes.security import SECURITY_INSTRUCTION
from app.nodes.simulator import SIMULATOR_INSTRUCTION
from app.orchestrator import orchestrator_phase3_gate, orchestrator_phase4_gate
from app.schemas import (
    AdvocateOutput,
    ExecutiveSummaryOutput,
    FinanceOutput,
    GrowthOutput,
    InvestorOutput,
    PitchDeckOutput,
    ProductOutput,
    ResearchOutput,
    RiskOutput,
    SecurityCheckpointOutput,
    SimulatorOutput,
    StartupIdea,
)
from app.skill_loader import build_skill_toolset
from app.state_writers import (
    state_writer_phase1,
    state_writer_phase2,
    state_writer_phase3,
    state_writer_phase4,
    state_writer_security,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Credential detection
# ─────────────────────────────────────────────────────────────────────────────
_vertex_available = False
try:
    _credentials, _project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = _project_id or ""
    _vertex_available = True
except Exception:
    pass

if _vertex_available:
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    logger.info("[agent] Auth mode: Vertex AI (Application Default Credentials)")
elif os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
    logger.info("[agent] Auth mode: Gemini API (GOOGLE_API_KEY)")
else:
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    logger.warning(
        "[agent] No credentials found. "
        "Option 1 (Vertex AI): run `gcloud auth application-default login`. "
        "Option 2 (Gemini API): set GOOGLE_API_KEY environment variable."
    )
    # Also emit to stdout so the credential warning is visible in non-logging contexts
    print(
        "[agent] WARNING: No credentials found.\n"
        "  Option 1 (Vertex AI): run `gcloud auth application-default login`\n"
        "  Option 2 (Gemini API): set GOOGLE_API_KEY environment variable"
    )

# ─────────────────────────────────────────────────────────────────────────────
# Model config
# ─────────────────────────────────────────────────────────────────────────────
DEVELOPMENT_MODE = True
MODEL_NAME = "gemini-2.5-flash" if DEVELOPMENT_MODE else "gemini-2.5-pro"


def get_model() -> Gemini:
    return Gemini(model=MODEL_NAME, retry_options=types.HttpRetryOptions(attempts=3))


# ─────────────────────────────────────────────────────────────────────────────
# Name extractor (FunctionNode — no LLM call needed)
# ─────────────────────────────────────────────────────────────────────────────
def extract_name_node(ctx: Context, node_input: StartupIdea) -> Event:
    """Extract the startup name into ctx.state so all downstream nodes can reference it."""
    return Event(output=node_input, state={"startup_name": node_input.name})


# ─────────────────────────────────────────────────────────────────────────────
# MCP Toolsets
# ─────────────────────────────────────────────────────────────────────────────
_MCP_SERVER_ARGS = [sys.executable, "app/mcp_server.py"]

search_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command=_MCP_SERVER_ARGS[0], args=_MCP_SERVER_ARGS[1:]
    ),
    tool_filter=["search_market"],
)

sqlite_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command=_MCP_SERVER_ARGS[0], args=_MCP_SERVER_ARGS[1:]
    ),
    tool_filter=["query_runs_db"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Skill Toolset — auto-discovers all SKILL.md files in app/skills/
# ─────────────────────────────────────────────────────────────────────────────
skill_toolset = build_skill_toolset()


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Research & Risk (parallel, no prior context needed)
# ─────────────────────────────────────────────────────────────────────────────
research_agent = LlmAgent(
    name="research_agent",
    model=get_model(),
    instruction=RESEARCH_INSTRUCTION,
    output_schema=ResearchOutput,
    tools=[search_toolset, skill_toolset],
)

risk_agent = LlmAgent(
    name="risk_agent",
    model=get_model(),
    instruction=RISK_INSTRUCTION,
    output_schema=RiskOutput,
)

# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Product & Finance (consumes phase1_* from ctx.state)
# ─────────────────────────────────────────────────────────────────────────────
product_agent = LlmAgent(
    name="product_agent",
    model=get_model(),
    instruction=PRODUCT_INSTRUCTION,
    output_schema=ProductOutput,
)

finance_agent = LlmAgent(
    name="finance_agent",
    model=get_model(),
    instruction=FINANCE_INSTRUCTION,
    output_schema=FinanceOutput,
    tools=[skill_toolset],
)

# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Advocate & Investor (consumes phase1+2 from ctx.state)
# ─────────────────────────────────────────────────────────────────────────────
advocate_agent = LlmAgent(
    name="advocate_agent",
    model=get_model(),
    instruction=ADVOCATE_INSTRUCTION,
    output_schema=AdvocateOutput,
    tools=[skill_toolset],
)

investor_agent = LlmAgent(
    name="investor_agent",
    model=get_model(),
    instruction=INVESTOR_INSTRUCTION,
    output_schema=InvestorOutput,
    tools=[sqlite_toolset, skill_toolset],
)

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Growth, Simulator, PitchDeck (consumes all prior phases)
# ─────────────────────────────────────────────────────────────────────────────
growth_agent = LlmAgent(
    name="growth_agent",
    model=get_model(),
    instruction=GROWTH_INSTRUCTION,
    output_schema=GrowthOutput,
    tools=[skill_toolset],
)

simulator_agent = LlmAgent(
    name="simulator_agent",
    model=get_model(),
    instruction=SIMULATOR_INSTRUCTION,
    output_schema=SimulatorOutput,
)

pitchdeck_agent = LlmAgent(
    name="pitchdeck_agent",
    model=get_model(),
    instruction=PITCHDECK_INSTRUCTION,
    output_schema=PitchDeckOutput,
    tools=[skill_toolset],
)

# ─────────────────────────────────────────────────────────────────────────────
# Security
# ─────────────────────────────────────────────────────────────────────────────
security_agent = LlmAgent(
    name="security_agent",
    model=get_model(),
    instruction=SECURITY_INSTRUCTION,
    output_schema=SecurityCheckpointOutput,
)

# ─────────────────────────────────────────────────────────────────────────────
# Executive Summary (reads all phase summaries + confidence scores from state)
# ─────────────────────────────────────────────────────────────────────────────
executive_summary_agent = LlmAgent(
    name="executive_summary_agent",
    model=get_model(),
    instruction=EXECUTIVE_SUMMARY_INSTRUCTION,
    output_schema=ExecutiveSummaryOutput,
)


# ─────────────────────────────────────────────────────────────────────────────
# Pre-Executive-Summary Bridge Node
# ─────────────────────────────────────────────────────────────────────────────
def pre_exec_summary_node(ctx: Context, node_input: Any) -> Event:
    """Type-bridge between state_writer_security and executive_summary_agent.

    state_writer_security returns Event(output=SecurityCheckpointOutput(...)).
    When that Pydantic object lands as the LLM user message the model cannot
    interpret it and returns empty output.  This node emits a plain string
    trigger so the executive summary agent receives unambiguous natural-language
    input, while all analysis data is already in ctx.state.
    """
    is_safe = ctx.state.get("is_safe", True)
    safety_status = "PASSED" if is_safe else "FAILED — issues detected"
    trigger = (
        f"Security checkpoint {safety_status}. "
        "All phase summaries and confidence scores are available in context. "
        "Please produce the executive summary now."
    )
    return Event(output=trigger, state={})


# ─────────────────────────────────────────────────────────────────────────────
# Report builder helpers
# ─────────────────────────────────────────────────────────────────────────────
def _get(obj: Any, attr: str, fallback: Any = None) -> Any:
    """Retrieve *attr* from a Pydantic model or dict, falling back to *fallback*."""
    if hasattr(obj, attr):
        return getattr(obj, attr)
    if isinstance(obj, dict):
        return obj.get(attr, fallback)
    return fallback


def _build_markdown_report(ctx: Context, node_input: Any) -> tuple[str, dict[str, Any]]:
    """Construct the Markdown report string and return it alongside a flat fields dict."""
    startup_name = ctx.state.get("startup_name", "Unknown Startup")
    startup_score = ctx.state.get("startup_score", 0)
    inv_score = ctx.state.get("investment_readiness_score", 0)

    # Resolve all ExecutiveSummaryOutput fields with safe fallback logic
    exec_summary_text = _get(node_input, "executive_summary", "")
    top_strengths = _get(node_input, "top_strengths", [])
    top_risks = _get(node_input, "top_risks", [])
    recommendation = _get(node_input, "recommendation", "Unknown")
    overall_confidence_score = _get(node_input, "overall_confidence_score", 0)
    startup_health = _get(node_input, "startup_health", exec_summary_text)
    biggest_strengths = _get(node_input, "biggest_strengths", top_strengths)
    biggest_risks = _get(node_input, "biggest_risks", top_risks)
    recommended_next_action = _get(
        node_input, "recommended_next_action", recommendation
    )
    overall_confidence = _get(
        node_input, "overall_confidence", overall_confidence_score
    )

    strengths_to_show = biggest_strengths or top_strengths
    risks_to_show = biggest_risks or top_risks

    lines: list[str] = [
        f"# Startup Founder Package: {startup_name}",
        "",
        f"> **Overall Confidence Score: {overall_confidence}/100**  ",
        f"> **Recommendation: {recommendation}**  ",
        f"> **Recommended Next Action: {recommended_next_action}**",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        exec_summary_text,
        "",
        "## Startup Health",
        "",
        startup_health,
        "",
        "## Key Scores",
        "",
        "| Metric | Score |",
        "|---|---|",
        f"| Startup Score | {startup_score}/100 |",
        f"| Investment Readiness | {inv_score}/100 |",
        f"| Overall Confidence | {overall_confidence}/100 |",
        "",
    ]

    if strengths_to_show:
        lines += ["## Top Strengths", ""] + [f"- {s}" for s in strengths_to_show] + [""]

    if risks_to_show:
        lines += ["## Top Risks", ""] + [f"- {r}" for r in risks_to_show] + [""]

    lines += ["## Phase Summaries", ""]
    for phase_key, label in [
        ("phase1_research_summary", "Market Research"),
        ("phase1_risk_summary", "Risk Assessment"),
        ("phase2_product_summary", "Product / MVP"),
        ("phase2_finance_summary", "Financial Model"),
        ("phase3_advocate_summary", "Devil's Advocate"),
        ("phase3_investor_summary", "Investor Verdict"),
        ("phase4_growth_summary", "Growth Strategy"),
    ]:
        content = ctx.state.get(phase_key, "")
        if content:
            lines += [f"### {label}", "", f"```json\n{content[:1500]}\n```", ""]

    # Pitch deck
    pitch_summary = ctx.state.get("phase4_pitchdeck_summary", "")
    if pitch_summary:
        try:
            deck_md = json.loads(pitch_summary).get("markdown_deck", "")
            if deck_md:
                lines += ["## Pitch Deck", "", deck_md, ""]
        except (json.JSONDecodeError, AttributeError):
            pass

    # Orchestrator decision log
    gate3_log = ctx.state.get("orchestrator_gate3_log", "")
    gate4_log = ctx.state.get("orchestrator_gate4_log", "")
    if gate3_log or gate4_log:
        lines += ["## Orchestrator Decision Log", ""]
        if gate3_log:
            lines += [f"### Gate 3 (Pre-HITL)\n```json\n{gate3_log}\n```", ""]
        if gate4_log:
            lines += [f"### Gate 4 (Pre-Security)\n```json\n{gate4_log}\n```", ""]

    fields: dict[str, Any] = {
        "startup_name": startup_name,
        "startup_score": startup_score,
        "inv_score": inv_score,
        "exec_summary_text": exec_summary_text,
        "startup_health": startup_health,
        "recommendation": recommendation,
        "recommended_next_action": recommended_next_action,
        "overall_confidence_score": overall_confidence_score,
        "overall_confidence": overall_confidence,
        "gate3_log": gate3_log,
        "gate4_log": gate4_log,
    }
    return "\n".join(lines), fields


# ─────────────────────────────────────────────────────────────────────────────
# MCP Write Node (SQLite + Markdown report + PDF)
# ─────────────────────────────────────────────────────────────────────────────
async def _run_mcp_client(
    filename: str, md_content: str, fields: dict[str, Any]
) -> None:
    """Open an MCP client session and invoke all three write tools."""
    server_params = StdioServerParameters(
        command=sys.executable, args=["app/mcp_server.py"]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            res_md = await session.call_tool(
                "write_report_file",
                arguments={"filename": filename, "content": md_content},
            )
            logger.info("[mcp_write_node] %s", res_md.content[0].text)

            res_pdf = await session.call_tool(
                "generate_pdf_report",
                arguments={"markdown_path": f"./outputs/{filename}"},
            )
            logger.info("[mcp_write_node] %s", res_pdf.content[0].text)

            res_db = await session.call_tool(
                "write_runs_db",
                arguments={
                    "session_id": fields["session_id"],
                    "startup_name": fields["startup_name"],
                    "startup_score": int(fields["startup_score"]),
                    "investment_readiness_score": int(fields["inv_score"]),
                    "overall_confidence_score": int(fields["overall_confidence_score"]),
                    "recommendation": fields["recommendation"],
                    "executive_summary": fields["exec_summary_text"],
                    "startup_health": fields["startup_health"],
                    "recommended_next_action": fields["recommended_next_action"],
                    "overall_confidence": int(fields["overall_confidence"]),
                    "report_markdown": md_content,
                    "gate3_log": fields["gate3_log"] or "",
                    "gate4_log": fields["gate4_log"] or "",
                },
            )
            logger.info("[mcp_write_node] %s", res_db.content[0].text)


def mcp_write_node(ctx: Context, node_input: Any) -> dict[str, Any]:
    """Persist the final report to Markdown, generate a PDF, and write to SQLite.

    Receives ExecutiveSummaryOutput from the preceding agent.
    All other data is read from ctx.state (populated by the StateWriters).
    """
    md_content, fields = _build_markdown_report(ctx, node_input)
    fields["session_id"] = ctx.session.id

    startup_name = fields["startup_name"]
    filename = f"{startup_name.lower().replace(' ', '_')}_report.md"
    report_path = f"./outputs/{filename}"

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        nest_asyncio.apply()
        loop.run_until_complete(_run_mcp_client(filename, md_content, fields))
    else:
        asyncio.run(_run_mcp_client(filename, md_content, fields))

    return {"status": "success", "report_path": report_path}


# ─────────────────────────────────────────────────────────────────────────────
# Join Nodes
# ─────────────────────────────────────────────────────────────────────────────
join1 = JoinNode(name="join1")
join2 = JoinNode(name="join2")
join3 = JoinNode(name="join3")
join4 = JoinNode(name="join4")


# ─────────────────────────────────────────────────────────────────────────────
# Graph Edges
# ─────────────────────────────────────────────────────────────────────────────
edges = [
    # Phase 1
    ("START", extract_name_node),
    (extract_name_node, (research_agent, risk_agent)),
    ((research_agent, risk_agent), join1),
    (join1, state_writer_phase1),
    # Phase 2
    (state_writer_phase1, (product_agent, finance_agent)),
    ((product_agent, finance_agent), join2),
    (join2, state_writer_phase2),
    # Phase 3
    (state_writer_phase2, (advocate_agent, investor_agent)),
    ((advocate_agent, investor_agent), join3),
    (join3, state_writer_phase3),
    (state_writer_phase3, orchestrator_phase3_gate),
    (orchestrator_phase3_gate, hitl_review_node),
    # HITL routing
    (
        hitl_review_node,
        {
            "minor_revision": product_agent,
            "major_revision": research_agent,
            "approved": (growth_agent, simulator_agent, pitchdeck_agent),
        },
    ),
    # Phase 4
    ((growth_agent, simulator_agent, pitchdeck_agent), join4),
    (join4, state_writer_phase4),
    (state_writer_phase4, orchestrator_phase4_gate),
    (orchestrator_phase4_gate, security_agent),
    (security_agent, state_writer_security),
    (state_writer_security, pre_exec_summary_node),
    (pre_exec_summary_node, executive_summary_agent),
    (executive_summary_agent, mcp_write_node),
]

# ─────────────────────────────────────────────────────────────────────────────
# Root Agent + App
# ─────────────────────────────────────────────────────────────────────────────
root_agent = Workflow(
    name="startup_copilot",
    edges=edges,
    input_schema=StartupIdea,
)

app = App(
    root_agent=root_agent,
    name="startup_copilot_app",
)
