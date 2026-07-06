"""
Startup Copilot — Eval Trace Generator
=======================================
Runs the mock workflow (no credentials required) for each of the 10 eval
startup ideas and emits a structured JSON-Lines trace file at:

    tests/eval/traces/traces.jsonl

Each line = one trace with:
  - eval_case_id / startup_name
  - node_execution_order        list[str]
  - node_outputs                dict[node -> schema dict]
  - state_snapshot              ctx.state at end of run
  - hitl_triggered              bool
  - run_duration_ms             int
  - artifacts                   {md_written, pdf_written, db_written}
  - errors                      list[str]
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ── path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Suppress credentials probing
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")
os.environ.setdefault("GOOGLE_API_KEY", "mock-eval-key")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ["PYTHONUTF8"] = "1"
import io

if (
    hasattr(sys.stdout, "buffer")
    and getattr(sys.stdout, "encoding", "").lower() != "utf-8"
):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if (
    hasattr(sys.stderr, "buffer")
    and getattr(sys.stderr, "encoding", "").lower() != "utf-8"
):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

TRACES_DIR = Path(__file__).parent / "traces"
DATASET_FILE = Path(__file__).parent / "datasets" / "startup_ideas.json"
OUTPUT_FILE = TRACES_DIR / "traces.jsonl"

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _log(msg: str, col: str = RESET) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{col}[{ts}] {msg}{RESET}", flush=True)


def _section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 66}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 66}{RESET}\n", flush=True)


# ── Load ADK + schemas ────────────────────────────────────────────────────────
_section("LOADING FRAMEWORK")
try:
    from google.adk.agents.context import Context
    from google.adk.agents.run_config import RunConfig, StreamingMode
    from google.adk.events.event import Event
    from google.adk.events.request_input import RequestInput
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.workflow import FunctionNode, JoinNode, Workflow
    from google.genai import types

    from app.schemas import (
        AdvocateOutput,
        Competitor,
        ExecutiveSummaryOutput,
        FinanceOutput,
        GrowthOutput,
        InvestorOutput,
        MarketSize,
        MVPFeature,
        PitchDeckOutput,
        PitchDeckSlide,
        ProductOutput,
        ResearchOutput,
        RiskItem,
        RiskOutput,
        SecurityCheckpointOutput,
        SimulationMonth,
        SimulatorOutput,
        StartupIdea,
    )

    _log("Framework imports OK", GREEN)
except Exception as exc:
    _log(f"Import failed: {exc}", RED)
    traceback.print_exc()
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# Per-run state container
# ═══════════════════════════════════════════════════════════════════════════════
class RunState:
    """Mutable bag carried through one eval run."""

    def __init__(self, idea: StartupIdea):
        self.idea = idea
        self.executed_nodes: list[str] = []
        self.node_outputs: dict[str, Any] = {}
        self.errors: list[str] = []
        self.hitl_triggered: bool = False
        self.final_state: dict[str, Any] = {}

    def track(self, name: str, output: Any = None) -> None:
        self.executed_nodes.append(name)
        if output is not None:
            try:
                self.node_outputs[name] = (
                    output.model_dump()
                    if hasattr(output, "model_dump")
                    else (output if isinstance(output, dict) else str(output))
                )
            except Exception:
                self.node_outputs[name] = str(output)


# ═══════════════════════════════════════════════════════════════════════════════
# Generic stub factory  (parameterised by RunState + mock outputs)
# ═══════════════════════════════════════════════════════════════════════════════
def _make_mock_outputs(idea_name: str, domain: str) -> dict[str, Any]:
    """Build domain-flavoured mock outputs for a given startup idea."""

    # ── Research ──────────────────────────────────────────────────────────────
    research = ResearchOutput(
        market_size=MarketSize(
            tam=f"$200B global {domain} market by 2030",
            sam=f"$18B addressable segment for {idea_name} in target regions",
            som="$500M capturable within 5 years at current growth rate",
        ),
        competitors=[
            Competitor(
                name="Legacy Leader Corp",
                description=f"Dominant incumbent in {domain} space",
                strengths=["Brand recognition", "Enterprise relationships"],
                weaknesses=["No AI layer", "High pricing", "Slow innovation cycle"],
            ),
            Competitor(
                name="NimbleStart",
                description=f"VC-backed startup in {domain}",
                strengths=["Modern UX", "Series B funded"],
                weaknesses=["Limited vertical depth", "No proprietary data moat"],
            ),
        ],
        market_trends=[
            f"AI adoption in {domain} growing at 38% CAGR",
            "Shift from point solutions to integrated platforms",
            "Regulatory tailwinds accelerating in target markets",
        ],
        opportunities=[
            f"First-mover advantage in AI-native {domain} tooling",
            "Underserved SMB and mid-market segment",
        ],
        confidence_score=78,
    )

    # ── Risk ──────────────────────────────────────────────────────────────────
    risk = RiskOutput(
        initial_risks=[
            RiskItem(
                category="Market",
                description="Large incumbent may pivot to compete directly",
                severity="High",
                mitigation_strategy="Sign exclusivity partnerships early; build data moat",
            ),
            RiskItem(
                category="Regulatory",
                description=f"Compliance requirements in {domain} vary by region",
                severity="Medium",
                mitigation_strategy="Hire regulatory lead in Month 1; start in most permissive market",
            ),
            RiskItem(
                category="Operational",
                description="Customer acquisition costs may exceed projections",
                severity="Medium",
                mitigation_strategy="Validate CAC assumption with 3 paid pilots before scaling",
            ),
        ],
        is_showstopper=False,
        reasoning="No existential regulatory or legal blockers identified.",
        confidence_score=74,
    )

    # ── Product ───────────────────────────────────────────────────────────────
    product = ProductOutput(
        mvp_scope=[
            MVPFeature(
                name="Core AI Engine",
                description="Primary AI prediction/optimization layer",
                priority="Must-have",
            ),
            MVPFeature(
                name="Dashboard UI",
                description="Real-time analytics and reporting portal",
                priority="Must-have",
            ),
            MVPFeature(
                name="API Integrations",
                description="Connect to 3rd-party data sources",
                priority="Should-have",
            ),
            MVPFeature(
                name="Mobile App",
                description="iOS/Android companion app",
                priority="Nice-to-have",
            ),
        ],
        user_stories=[
            f"As a {domain} operator, I want real-time AI insights so I can make faster decisions.",
            "As an admin, I want a dashboard to monitor all system KPIs in one place.",
            "As a developer, I want a REST API to integrate our existing tooling.",
        ],
        suggested_tech_stack=["FastAPI", "React", "PostgreSQL", "Vertex AI", "Redis"],
        confidence_score=80,
    )

    # ── Finance ───────────────────────────────────────────────────────────────
    finance = FinanceOutput(
        pricing_model_critique=f"Pricing is competitive for {domain}; recommend a freemium-to-paid funnel to reduce friction.",
        unit_economics={
            "CAC": "$120 blended across digital + direct channels",
            "LTV": "$1,440 (12-month average contract * 12 months)",
            "LTV:CAC": "12x — strong payback profile",
            "Payback": "3.8 months — favourable for SaaS",
            "Gross Margin": "74%",
        },
        cost_structure=[
            "Engineering team (40% of burn): $52k/month",
            "Cloud infrastructure: $6k/month",
            "Sales & Marketing: $28k/month",
            "G&A: $14k/month",
        ],
        three_year_projections={
            "Year 1": "$620K ARR — 150 paying customers at avg $4.1K ACV",
            "Year 2": "$4.1M ARR — 800 customers; enterprise tier launched",
            "Year 3": "$14.5M ARR — 2,200 customers; international expansion",
        },
        confidence_score=76,
    )

    # ── Advocate ──────────────────────────────────────────────────────────────
    advocate = AdvocateOutput(
        brutal_truth=(
            f"{idea_name}'s biggest vulnerability is CAC creep. "
            "The $120 blended CAC assumes 60% inbound, but there is no content moat yet. "
            "If outbound dominates early, CAC could spike to $340 — collapsing the LTV:CAC to 4.2x. "
            "The incumbent competitor has 10x the sales force and could respond within 18 months."
        ),
        critical_assumptions=[
            "Inbound/outbound channel mix holds at 60/40 (unvalidated)",
            "Churn rate stays below 8% annually (no historical data)",
            "Enterprise tier launches on schedule in Month 14",
        ],
        stress_test_results={
            "CAC doubles": "LTV:CAC drops to 6x; payback extends to 7.6 months; Year 2 ARR falls to $2.9M.",
            "Churn hits 15%": "LTV collapses to $720; unit economics go negative at current CAC.",
            "Competitor enters": "25% pipeline reduction estimated; pivot to niche vertical needed.",
        },
        confidence_score=85,
    )

    # ── Investor ──────────────────────────────────────────────────────────────
    investor = InvestorOutput(
        investment_readiness_score=72,
        strengths=[
            "LTV:CAC of 12x with 3.8-month payback — top-quartile SaaS metrics",
            f"Large and growing {domain} market with regulatory tailwinds",
            "No direct AI-native competitor identified at scale",
        ],
        concerns=[
            "CAC assumption unvalidated — inbound channel mix assumed, not proven",
            "Enterprise tier roadmap creates execution risk in Year 2",
            "Regulatory complexity varies by region — team capacity to manage unclear",
        ],
        investment_recommendation="Conditional Invest",
        confidence_score=74,
    )

    # ── Growth ────────────────────────────────────────────────────────────────
    growth = GrowthOutput(
        channels=[
            "Content Marketing + SEO",
            "Direct Sales Outreach",
            "Partner / Reseller Network",
        ],
        acquisition_strategy=(
            f"Launch with 5 design-partner customers in {domain} to validate CAC. "
            "Month 1: hire SDR; build content playbook. "
            "Month 2: automate lead scoring with AI. "
            "Month 3: launch partner program targeting 3 system integrators."
        ),
        startup_score=74,
        execution_roadmap_90_days={
            "Month 1": [
                "Hire 1 SDR; establish ICP definition",
                "Launch content blog targeting 5 primary keywords",
                "Close 3 design-partner pilots (validates CAC assumption)",
            ],
            "Month 2": [
                "Onboard 15 paying customers; measure NPS",
                "Deploy AI lead-scoring dashboard",
                "File for data-processing compliance in primary market",
            ],
            "Month 3": [
                "Hit $50K MRR milestone gate",
                "Publish first customer case study",
                "Begin Series A deck and investor outreach",
            ],
        },
        confidence_score=77,
    )

    # ── Simulator ─────────────────────────────────────────────────────────────
    simulator = SimulatorOutput(
        simulation_log=[
            SimulationMonth(
                month=1,
                active_users=15,
                monthly_recurring_revenue=4500.0,
                burn_rate=100000.0,
                cash_balance=895000.0,
                milestones=["3 pilots signed"],
            ),
            SimulationMonth(
                month=2,
                active_users=45,
                monthly_recurring_revenue=13500.0,
                burn_rate=95000.0,
                cash_balance=813500.0,
                milestones=["CAC validated at $118"],
            ),
            SimulationMonth(
                month=3,
                active_users=110,
                monthly_recurring_revenue=33000.0,
                burn_rate=92000.0,
                cash_balance=754500.0,
                milestones=["$50K MRR hit"],
            ),
            SimulationMonth(
                month=6,
                active_users=320,
                monthly_recurring_revenue=96000.0,
                burn_rate=110000.0,
                cash_balance=538500.0,
                milestones=["Partner network active"],
            ),
            SimulationMonth(
                month=9,
                active_users=580,
                monthly_recurring_revenue=174000.0,
                burn_rate=130000.0,
                cash_balance=320500.0,
                milestones=["Enterprise tier beta"],
            ),
            SimulationMonth(
                month=12,
                active_users=1050,
                monthly_recurring_revenue=315000.0,
                burn_rate=160000.0,
                cash_balance=600000.0,
                milestones=["$3.78M ARR run rate", "Series A term sheet received"],
            ),
        ],
        success_scenario=(
            "Month 12: 1,050 active customers, $315K MRR. "
            "CAC holds at $118. Churn at 6.5%. Series A closed at $9M."
        ),
        failure_scenario=(
            "Month 9: inbound channel dries up; CAC spikes to $310. "
            "MRR growth stalls at $174K. Pivot to vertical SaaS required. "
            "Runway extends 8 months with bridge round."
        ),
        confidence_score=72,
    )

    # ── Pitch Deck ────────────────────────────────────────────────────────────
    pitch = PitchDeckOutput(
        markdown_deck=f"""# {idea_name} — Seed Round Pitch Deck

## Slide 1: Title
**{idea_name}** | *AI-powered {domain} platform*

## Slide 2: Problem
{domain} operators lose 20-35% efficiency from fragmented, non-AI tooling.

## Slide 3: Solution
{idea_name} delivers a unified AI platform — 10x faster decisions, 30% cost reduction.

## Slide 4: Market Size
- **TAM**: $200B global {domain} market by 2030
- **SAM**: $18B addressable segment
- **SOM**: $500M in 5 years

## Slide 5: Product & MVP
Core AI Engine + Dashboard + API Integrations
Stack: FastAPI | React | PostgreSQL | Vertex AI

## Slide 6: Business Model
LTV:CAC = 12x | Payback: 3.8 months | Gross Margin: 74%
Year 1: $620K ARR | Year 2: $4.1M ARR | Year 3: $14.5M ARR

## Slide 7: Competition
| Competitor | Weakness | Our Edge |
|---|---|---|
| Legacy Leader Corp | No AI layer | AI-native from day 1 |
| NimbleStart | No data moat | Proprietary training data |

## Slide 8: Go-To-Market
Design partners → Content + SEO → Partner network
Month 1: 3 pilots | Month 2: 15 customers | Month 3: $50K MRR

## Slide 9: Financial Projections
| Year | ARR |
|---|---|
| Year 1 | $620K |
| Year 2 | $4.1M |
| Year 3 | $14.5M |

## Slide 10: The Ask
Raising **$1.8M Seed**
- Engineering 45% | Sales 30% | Compliance 15% | Ops 10%
""",
        slides=[
            PitchDeckSlide(slide_number=i, title=t, content=[c])
            for i, (t, c) in enumerate(
                [
                    ("Title", f"{idea_name} — Seed Round"),
                    ("Problem", "Fragmented non-AI tooling"),
                    ("Solution", "Unified AI platform"),
                    ("Market", "$200B TAM / $18B SAM"),
                    ("Product", "Core AI Engine + Dashboard"),
                    ("Biz Model", "LTV:CAC=12x, 3.8mo payback"),
                    ("Competition", "No AI-native competitor"),
                    ("GTM", "Design partners → scale"),
                    ("Financials", "$620K / $4.1M / $14.5M"),
                    ("The Ask", "$1.8M Seed"),
                ],
                start=1,
            )
        ],
        confidence_score=80,
    )

    # ── Security ──────────────────────────────────────────────────────────────
    security = SecurityCheckpointOutput(
        is_safe=True,
        issues=[],
        sanitized_report=f"{idea_name} operates in a regulated but legal market. No PII violations, no illicit model found.",
        confidence_score=92,
    )

    # ── Executive Summary ─────────────────────────────────────────────────────
    exec_summary = ExecutiveSummaryOutput(
        executive_summary=(
            f"{idea_name} presents a compelling Seed opportunity in the {domain} space. "
            "Strong unit economics (LTV:CAC 12x) and a clear market gap support the thesis. "
            "The primary risk — unvalidated CAC — is addressable through 3 design-partner pilots in Month 1."
        ),
        top_strengths=[
            "LTV:CAC of 12x — top-quartile SaaS benchmark",
            f"No AI-native competitor at scale in {domain}",
            "Regulatory tailwinds reduce adoption friction",
        ],
        top_risks=[
            "CAC assumption (unvalidated) — single largest model risk",
            "Enterprise tier execution risk in Year 2",
            "Incumbent competitor could respond within 18 months",
        ],
        recommendation="Conditional Invest",
        overall_confidence_score=78,
        startup_health=(
            f"{idea_name} is in healthy early-stage position with strong economics, clear differentiation, "
            "and a near-term validation path via design partners."
        ),
        biggest_strengths=[
            "LTV:CAC 12x",
            "Large addressable market",
            "AI-native product differentiation",
        ],
        biggest_risks=[
            "Unvalidated CAC",
            "Enterprise roadmap execution",
            "Competitive response",
        ],
        recommended_next_action="Sign 3 design-partner pilots to validate CAC before Series A.",
        overall_confidence=78,
    )

    return {
        "research_agent": research,
        "risk_agent": risk,
        "product_agent": product,
        "finance_agent": finance,
        "advocate_agent": advocate,
        "investor_agent": investor,
        "growth_agent": growth,
        "simulator_agent": simulator,
        "pitchdeck_agent": pitch,
        "security_agent": security,
        "executive_summary_agent": exec_summary,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow builder (per-run, with injected RunState)
# ═══════════════════════════════════════════════════════════════════════════════
def _build_workflow(rs: RunState, mocks: dict[str, Any]):
    """Build a fresh mock Workflow for a single eval run."""

    def _node(name: str, out_key: str | None = None):
        """Return a sync stub function that records execution and returns the mock output."""
        mock_output = mocks.get(name) if out_key is None else mocks.get(out_key or name)

        def _fn(ctx: Context, node_input: Any):
            rs.track(name, mock_output)
            return Event(output=mock_output)

        _fn.__name__ = name
        return _fn

    # ── State writer factories ─────────────────────────────────────────────
    def _sw_phase1(ctx: Context, node_input: Any):
        rs.track("state_writer_phase1")
        state = {
            "phase1_research_summary": json.dumps(mocks["research_agent"].model_dump()),
            "phase1_risk_summary": json.dumps(mocks["risk_agent"].model_dump()),
            "phase1_research_confidence": mocks["research_agent"].confidence_score,
            "phase1_risk_confidence": mocks["risk_agent"].confidence_score,
        }
        return Event(output=node_input, state=state)

    def _sw_phase2(ctx: Context, node_input: Any):
        rs.track("state_writer_phase2")
        state = {
            "phase2_product_summary": json.dumps(mocks["product_agent"].model_dump()),
            "phase2_finance_summary": json.dumps(mocks["finance_agent"].model_dump()),
            "phase2_product_confidence": mocks["product_agent"].confidence_score,
            "phase2_finance_confidence": mocks["finance_agent"].confidence_score,
        }
        return Event(output=node_input, state=state)

    def _sw_phase3(ctx: Context, node_input: Any):
        rs.track("state_writer_phase3")
        state = {
            "phase3_advocate_summary": json.dumps(mocks["advocate_agent"].model_dump()),
            "phase3_investor_summary": json.dumps(mocks["investor_agent"].model_dump()),
            "phase3_advocate_confidence": mocks["advocate_agent"].confidence_score,
            "phase3_investor_confidence": mocks["investor_agent"].confidence_score,
            "investment_readiness_score": mocks[
                "investor_agent"
            ].investment_readiness_score,
            "investor_recommendation": mocks[
                "investor_agent"
            ].investment_recommendation,
        }
        return Event(output=node_input, state=state)

    def _gate3(ctx: Context, node_input: Any):
        rs.track("orchestrator_phase3_gate")
        avg = round(
            sum(
                [
                    ctx.state.get("phase1_research_confidence", 75),
                    ctx.state.get("phase1_risk_confidence", 75),
                    ctx.state.get("phase2_product_confidence", 75),
                    ctx.state.get("phase2_finance_confidence", 75),
                    ctx.state.get("phase3_advocate_confidence", 75),
                    ctx.state.get("phase3_investor_confidence", 75),
                ]
            )
            / 6,
            1,
        )
        inv_score = ctx.state.get("investment_readiness_score", 0)
        inv_reco = ctx.state.get("investor_recommendation", "Unknown")
        decision = f"Gate3: '{inv_reco}' ({inv_score}/100). Avg confidence: {avg}/100."
        return Event(
            output=node_input,
            state={
                "orchestrator_gate3_log": json.dumps(
                    {"gate": "phase3", "avg": avg, "decision": decision}
                ),
                "orchestrator_avg_confidence_p1_p3": avg,
            },
        )

    async def _hitl(ctx: Context, node_input: Any):
        rs.hitl_triggered = True
        rs.track("hitl_review_node")
        if not ctx.resume_inputs or "founder_review" not in ctx.resume_inputs:
            yield RequestInput(
                interrupt_id="founder_review", message="=== HITL: approve? ==="
            )
            return
        response_text = ctx.resume_inputs["founder_review"]
        status = "approved"
        if "major_revision" in response_text.lower():
            status = "major_revision"
        elif "minor_revision" in response_text.lower():
            status = "minor_revision"
        yield Event(
            output={"status": status, "comments": response_text},
            route=status,
            state={
                "founder_feedback": response_text,
                "hitl_revision_requested": status != "approved",
            },
        )

    def _sw_phase4(ctx: Context, node_input: Any):
        rs.track("state_writer_phase4")
        state = {
            "phase4_growth_summary": json.dumps(mocks["growth_agent"].model_dump()),
            "phase4_simulator_summary": json.dumps(
                mocks["simulator_agent"].model_dump()
            ),
            "phase4_pitchdeck_summary": json.dumps(
                mocks["pitchdeck_agent"].model_dump()
            ),
            "phase4_growth_confidence": mocks["growth_agent"].confidence_score,
            "phase4_simulator_confidence": mocks["simulator_agent"].confidence_score,
            "phase4_pitchdeck_confidence": mocks["pitchdeck_agent"].confidence_score,
            "startup_score": mocks["growth_agent"].startup_score,
        }
        return Event(output=node_input, state=state)

    def _gate4(ctx: Context, node_input: Any):
        rs.track("orchestrator_phase4_gate")
        scores = [
            ctx.state.get(k, 75)
            for k in [
                "phase1_research_confidence",
                "phase1_risk_confidence",
                "phase2_product_confidence",
                "phase2_finance_confidence",
                "phase3_advocate_confidence",
                "phase3_investor_confidence",
                "phase4_growth_confidence",
                "phase4_simulator_confidence",
                "phase4_pitchdeck_confidence",
            ]
        ]
        avg = round(sum(scores) / len(scores), 1)
        startup_score = ctx.state.get("startup_score", 74)
        inv_score = ctx.state.get("investment_readiness_score", 72)
        decision = (
            f"Gate4: overall avg={avg}/100 startup={startup_score} invest={inv_score}."
        )
        return Event(
            output=node_input,
            state={
                "orchestrator_gate4_log": json.dumps(
                    {"gate": "phase4", "avg": avg, "decision": decision}
                ),
                "orchestrator_avg_confidence_all": avg,
            },
        )

    def _sw_security(ctx: Context, node_input: Any):
        rs.track("state_writer_security")
        state = {
            "phase4_security_summary": json.dumps(mocks["security_agent"].model_dump()),
            "phase4_security_confidence": mocks["security_agent"].confidence_score,
            "is_safe": mocks["security_agent"].is_safe,
            "sanitized_report": mocks["security_agent"].sanitized_report,
        }
        return Event(output=node_input, state=state)

    def _pre_exec(ctx: Context, node_input: Any):
        rs.track("pre_exec_summary_node")
        is_safe = ctx.state.get("is_safe", True)
        trigger = f"Security {'PASSED' if is_safe else 'FAILED'}. All summaries available. Produce executive summary."
        return Event(output=trigger, state={})

    def _exec_summary(ctx: Context, node_input: Any):
        out = mocks["executive_summary_agent"]
        rs.track("executive_summary_agent", out)
        return Event(output=out)

    def _mcp_write(ctx: Context, node_input: Any):
        rs.track("mcp_write_node")
        rs.final_state = dict(ctx.state)
        return Event(output={"status": "ok"}, state={})

    def _extract_name(ctx: Context, node_input: StartupIdea):
        rs.track("extract_name_node")
        return Event(output=node_input, state={"startup_name": node_input.name})

    # ── Assign names ──────────────────────────────────────────────────────
    _sw_phase1.__name__ = "state_writer_phase1"
    _sw_phase2.__name__ = "state_writer_phase2"
    _sw_phase3.__name__ = "state_writer_phase3"
    _gate3.__name__ = "orchestrator_phase3_gate"
    _hitl.__name__ = "hitl_review_node"
    _sw_phase4.__name__ = "state_writer_phase4"
    _gate4.__name__ = "orchestrator_phase4_gate"
    _sw_security.__name__ = "state_writer_security"
    _pre_exec.__name__ = "pre_exec_summary_node"
    _exec_summary.__name__ = "executive_summary_agent"
    _mcp_write.__name__ = "mcp_write_node"
    _extract_name.__name__ = "extract_name_node"

    # Named stubs for each agent
    stubs = {
        k: _node(k)
        for k in [
            "research_agent",
            "risk_agent",
            "product_agent",
            "finance_agent",
            "advocate_agent",
            "investor_agent",
            "growth_agent",
            "simulator_agent",
            "pitchdeck_agent",
            "security_agent",
        ]
    }

    join1 = JoinNode(name="join1")
    join2 = JoinNode(name="join2")
    join3 = JoinNode(name="join3")
    join4 = JoinNode(name="join4")

    hitl_node = FunctionNode(func=_hitl, rerun_on_resume=True, name="hitl_review_node")

    r = stubs["research_agent"]
    k = stubs["risk_agent"]
    pr = stubs["product_agent"]
    fi = stubs["finance_agent"]
    ad = stubs["advocate_agent"]
    iv = stubs["investor_agent"]
    gr = stubs["growth_agent"]
    si = stubs["simulator_agent"]
    pd = stubs["pitchdeck_agent"]
    sc = stubs["security_agent"]

    edges = [
        ("START", _extract_name),
        (_extract_name, (r, k)),
        ((r, k), join1),
        (join1, _sw_phase1),
        (_sw_phase1, (pr, fi)),
        ((pr, fi), join2),
        (join2, _sw_phase2),
        (_sw_phase2, (ad, iv)),
        ((ad, iv), join3),
        (join3, _sw_phase3),
        (_sw_phase3, _gate3),
        (_gate3, hitl_node),
        (
            hitl_node,
            {
                "minor_revision": pr,
                "major_revision": r,
                "approved": (gr, si, pd),
            },
        ),
        ((gr, si, pd), join4),
        (join4, _sw_phase4),
        (_sw_phase4, _gate4),
        (_gate4, sc),
        (sc, _sw_security),
        (_sw_security, _pre_exec),
        (_pre_exec, _exec_summary),
        (_exec_summary, _mcp_write),
    ]

    return Workflow(name="startup_copilot_eval", edges=edges, input_schema=StartupIdea)


# ═══════════════════════════════════════════════════════════════════════════════
# Single-case runner
# ═══════════════════════════════════════════════════════════════════════════════
def run_case(case: dict) -> dict:
    """Run one eval case and return a trace dict."""
    idea_name = case["startup_name"]
    domain = case["domain"]
    _log(f"  Running: {idea_name} ({domain})", CYAN)

    # Parse prompt text as StartupIdea
    prompt_text = case["prompt"]["parts"][0]["text"]
    try:
        idea = StartupIdea.model_validate_json(prompt_text)
    except Exception as exc:
        return {
            "eval_case_id": case["eval_case_id"],
            "error": f"Bad prompt: {exc}",
            "errors": [str(exc)],
        }

    mocks = _make_mock_outputs(idea_name, domain)
    rs = RunState(case)

    t0 = time.monotonic()
    errors: list[str] = []

    try:
        workflow = _build_workflow(rs, mocks)
        session_service = InMemorySessionService()
        session = asyncio.run(
            session_service.create_session(
                user_id="eval_user", app_name="startup_copilot_eval"
            )
        )
        runner = Runner(
            agent=workflow,
            session_service=session_service,
            app_name="startup_copilot_eval",
        )
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=idea.model_dump_json())],
        )

        # ── Phase 1: run to HITL ──────────────────────────────────────────
        for event in runner.run(
            new_message=message,
            user_id="eval_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            if "RequestInput" in type(event).__name__:
                break

        # ── Phase 2: resume (auto-approve) ────────────────────────────────
        resume_msg = types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id="founder_review",
                        name="adk_request_input",
                        response={
                            "result": "status: approved\ncomments: Auto-approved by eval harness."
                        },
                    )
                )
            ],
        )
        for _ in runner.run(
            new_message=resume_msg,
            user_id="eval_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            pass

    except Exception as exc:
        errors.append(str(exc))
        _log(f"  ERROR in {idea_name}: {exc}", RED)

    run_ms = round((time.monotonic() - t0) * 1000)

    # Collect node outputs into serialisable form
    node_outputs_serial: dict[str, Any] = {}
    for node_name, output in rs.node_outputs.items():
        if hasattr(output, "model_dump"):
            node_outputs_serial[node_name] = output.model_dump()
        elif isinstance(output, dict):
            node_outputs_serial[node_name] = output
        else:
            node_outputs_serial[node_name] = str(output)

    # Get exec summary fields
    exec_out = mocks.get("executive_summary_agent")
    growth_out = mocks.get("growth_agent")
    investor_out = mocks.get("investor_agent")

    trace = {
        "eval_case_id": case["eval_case_id"],
        "startup_name": idea_name,
        "domain": domain,
        "run_timestamp": datetime.now(UTC).isoformat(),
        "run_duration_ms": run_ms,
        "node_execution_order": rs.executed_nodes,
        "node_outputs": node_outputs_serial,
        "state_snapshot": rs.final_state,
        "hitl_triggered": rs.hitl_triggered,
        "final_metrics": {
            "startup_score": growth_out.startup_score if growth_out else 0,
            "investment_score": investor_out.investment_readiness_score
            if investor_out
            else 0,
            "recommendation": exec_out.recommendation if exec_out else "Unknown",
            "overall_confidence": exec_out.overall_confidence_score if exec_out else 0,
        },
        "expected_routing": case.get("expected_routing", []),
        "ground_truth": case.get("ground_truth", {}),
        "errors": errors + rs.errors,
    }

    status = "✓ OK" if not errors else "✗ ERR"
    col = GREEN if not errors else RED
    _log(
        f"  {status}  {idea_name} — {run_ms}ms  score={trace['final_metrics']['startup_score']}  invest={trace['final_metrics']['investment_score']}",
        col,
    )
    return trace


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    TRACES_DIR.mkdir(parents=True, exist_ok=True)

    _section("LOADING EVAL DATASET")
    dataset = json.loads(DATASET_FILE.read_text(encoding="utf-8"))
    cases = dataset["eval_cases"]
    _log(f"Loaded {len(cases)} eval cases", GREEN)

    _section("GENERATING TRACES")
    traces = []
    for i, case in enumerate(cases, 1):
        _log(f"\n[{i}/{len(cases)}] {case['startup_name']}", BOLD)
        trace = run_case(case)
        traces.append(trace)

    _section("WRITING TRACE FILE")
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for trace in traces:
            f.write(json.dumps(trace, ensure_ascii=False) + "\n")
    _log(f"Wrote {len(traces)} traces → {OUTPUT_FILE}", GREEN)

    errors_total = sum(len(t.get("errors", [])) for t in traces)
    _section("TRACE GENERATION SUMMARY")
    _log(f"Total cases   : {len(traces)}", BOLD)
    _log(
        f"Successful    : {len(traces) - sum(1 for t in traces if t.get('errors'))}",
        GREEN,
    )
    _log(
        f"With errors   : {sum(1 for t in traces if t.get('errors'))}",
        RED if errors_total else GREEN,
    )
    _log(f"Total errors  : {errors_total}", RED if errors_total else GREEN)
    _log(f"Output file   : {OUTPUT_FILE}", CYAN)
    return 0 if errors_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
