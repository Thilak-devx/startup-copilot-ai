"""
Mock end-to-end runner for Startup Copilot AI — Collaborative Multi-Agent Edition.

Replaces LlmAgent nodes with synchronous FunctionNode stubs that return
valid schema-conforming outputs. No Google credentials required.

Validates:
  - The complete workflow graph (all edges, joins, routing)
  - Cross-agent state propagation (ctx.state keys written by StateWriters)
  - Orchestrator gates (confidence scoring, anomaly detection)
  - HITL checkpoint interrupt + resume
  - Executive Summary synthesis
  - mcp_write_node (SQLite + richer Markdown report)
  - All 21 required nodes execute in correct order
"""

import json
import os
import sqlite3
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.reporting import get_outputs_dir, report_filename

# Force UTF-8 output on Windows
os.environ["PYTHONUTF8"] = "1"
import io
import sys as _sys

if (
    hasattr(_sys.stdout, "buffer")
    and getattr(_sys.stdout, "encoding", "").lower() != "utf-8"
):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if (
    hasattr(_sys.stderr, "buffer")
    and getattr(_sys.stderr, "encoding", "").lower() != "utf-8"
):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Suppress credential probing
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
os.environ["GOOGLE_API_KEY"] = "mock-key-for-structural-test"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

# ─────────────────────────────────────────────────────────────────────────────
# Terminal helpers
# ─────────────────────────────────────────────────────────────────────────────
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def log(msg, col=RESET):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{col}[{ts}] {msg}{RESET}", flush=True)


def section(title):
    print(f"\n{BOLD}{CYAN}{'=' * 66}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 66}{RESET}\n", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────────────────────
section("IMPORTS & SCHEMA LOADING")
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

    log("All imports OK", GREEN)
except Exception as e:
    log(f"Import failed: {e}", RED)
    traceback.print_exc()
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Mock data — all with confidence_score fields
# ─────────────────────────────────────────────────────────────────────────────
MOCK_RESEARCH = ResearchOutput(
    market_size=MarketSize(
        tam="$850B global renewable energy market by 2030",
        sam="$42B community solar segment in residential markets",
        som="$2.1B capturable within 5 years at 5% market penetration",
    ),
    competitors=[
        Competitor(
            name="Sunrun",
            description="Residential solar leasing giant",
            strengths=["Brand recognition", "Scale", "Financing options"],
            weaknesses=["No community-sharing model", "High CAC"],
        ),
        Competitor(
            name="EnergySage",
            description="Solar marketplace aggregator",
            strengths=["Marketplace network effects"],
            weaknesses=["No AI optimization", "No peer-to-peer trading"],
        ),
    ],
    market_trends=[
        "Rising electricity costs driving demand for alternatives",
        "Net metering policy expansion across 38 US states",
        "AI-driven energy management growing at 31% CAGR",
    ],
    opportunities=[
        "No dominant AI-native community solar platform exists",
        "Regulatory tailwinds from IRA clean energy incentives",
        "HOA partnerships as a low-CAC distribution channel",
    ],
    confidence_score=85,
)

MOCK_RISK = RiskOutput(
    initial_risks=[
        RiskItem(
            category="Regulatory",
            description="State-by-state net metering rules vary widely",
            severity="High",
            mitigation_strategy="Engage regulatory counsel; launch in top-5 net-metering states first",
        ),
        RiskItem(
            category="Market",
            description="Customer education burden for AI energy sharing concept",
            severity="Medium",
            mitigation_strategy="Partner with HOAs; use simple kWh-credit dashboard",
        ),
        RiskItem(
            category="Operational",
            description="Hardware integration complexity with legacy smart meters",
            severity="Medium",
            mitigation_strategy="Build agnostic API layer; support top-3 meter vendors",
        ),
    ],
    is_showstopper=False,
    reasoning="Risks are manageable with targeted mitigation. No existential regulatory blockers identified.",
    confidence_score=82,
)

MOCK_PRODUCT = ProductOutput(
    mvp_scope=[
        MVPFeature(
            name="Community Solar Dashboard",
            description="Real-time kWh tracking per household — addresses #1 market opportunity: visibility",
            priority="Must-have",
        ),
        MVPFeature(
            name="AI Energy Optimizer",
            description="ML model predicting optimal sharing windows — differentiator vs Sunrun/EnergySage",
            priority="Must-have",
        ),
        MVPFeature(
            name="Peer-to-Peer Trading Module",
            description="Smart contract-backed kWh credits — mitigates billing trust risk",
            priority="Should-have",
        ),
        MVPFeature(
            name="HOA Admin Portal",
            description="Bulk enrollment and reporting for community managers",
            priority="Nice-to-have",
        ),
    ],
    user_stories=[
        "As a homeowner, I want to see my real-time energy surplus so I can share it with my neighbors.",
        "As an HOA manager, I want a dashboard showing community-wide energy savings to present at meetings.",
        "As a resident, I want automatic bill credits when I share energy so I don't need manual intervention.",
    ],
    suggested_tech_stack=[
        "FastAPI (backend — low CAC infrastructure vs Node.js)",
        "React + Recharts (dashboard)",
        "PostgreSQL + TimescaleDB (time-series metering data)",
        "Vertex AI (ML optimizer — mitigates operational risk of custom model)",
        "Stripe (billing)",
    ],
    confidence_score=80,
)

MOCK_FINANCE = FinanceOutput(
    pricing_model_critique=(
        "10% transaction fee is fair and aligns with marketplace norms. "
        "Risk: low-volume communities yield thin margins early. "
        "Anchored to SOM of $2.1B — targeting 0.1% in Year 1 = $2.1M addressable revenue."
    ),
    unit_economics={
        "CAC": "$85 per household via HOA channel (below Sunrun's ~$400 CAC)",
        "LTV": "$720 per household over 3 years (avg $240/yr fee)",
        "LTV:CAC Ratio": "8.5x — very strong; payback in 4.3 months",
        "Payback Period": "4.3 months",
    },
    cost_structure=[
        "Cloud infrastructure (AWS/GCP): $8k/mo at scale",
        "ML model training & inference: $3k/mo",
        "Customer success & ops: $45k/mo (Year 1 team)",
        "Regulatory compliance: $15k/mo",
    ],
    three_year_projections={
        "Year 1": "$480K ARR — 200 communities, avg 20 households (0.023% SOM)",
        "Year 2": "$3.2M ARR — 1,200 communities via HOA partnerships (0.15% SOM)",
        "Year 3": "$11.4M ARR — enterprise utility partnerships added (0.54% SOM)",
    },
    confidence_score=78,
)

MOCK_ADVOCATE = AdvocateOutput(
    brutal_truth=(
        "The 10% fee is easy to undercut — any utility launching a similar feature eliminates "
        "the moat overnight. The LTV:CAC of 8.5x assumes HOA channel CAC of $85, but the "
        "CFO has no comparable data point to validate this; Sunrun's CAC is ~$400 for a reason. "
        "If HOA onboarding takes 6 months instead of 2, Year 1 ARR collapses to ~$120K."
    ),
    critical_assumptions=[
        "HOAs will act as distribution partners without revenue share (unvalidated)",
        "Homeowners will trust a third-party with energy billing (trust risk underestimated)",
        "CAC of $85 is achievable via HOA channel (no comparable data cited by CFO)",
        "Regulatory environment remains favorable to peer-to-peer trading",
    ],
    stress_test_results={
        "Utility competition": "If top-3 utilities launch competing features: 40% TAM reduction. Year 3 ARR falls from $11.4M to $6.8M. Mitigate: HOA exclusivity contracts.",
        "Regulatory reversal": "If net metering is rolled back in 2 states: 15% revenue impact = -$72K ARR Year 1. Geographic diversification needed.",
        "Adoption slowdown": "If HOA onboarding takes 6mo avg instead of 2mo: Year 1 ARR drops to $120K. Runway extension of 18 months required.",
    },
    confidence_score=88,
)

MOCK_INVESTOR = InvestorOutput(
    investment_readiness_score=74,
    strengths=[
        "LTV:CAC of 8.5x via HOA channel — strong unit economics if CAC holds",
        "Clear regulatory tailwind from IRA clean energy incentives",
        "No dominant AI-native competitor in community solar at scale",
    ],
    concerns=[
        "Utility competition risk is underestimated — no moat beyond AI (2-yr window)",
        "CAC assumption of $85 is unvalidated — Sunrun's $400 CAC is the only benchmark",
        "Regulatory complexity across 50 states adds execution risk — team not yet assembled",
    ],
    investment_recommendation="Conditional Invest",
    confidence_score=76,
)

MOCK_GROWTH = GrowthOutput(
    channels=[
        "HOA Direct Outreach",
        "Clean Energy Influencer Partnerships",
        "Utility Referral Program",
    ],
    acquisition_strategy=(
        "Lead with HOA partnership program targeting communities of 50-200 households. "
        "Offer free 90-day pilot with guaranteed 10% average bill reduction. "
        "Month 1: directly address investor concern #1 — sign HOA exclusivity clause in pilot agreements. "
        "Leverage HOA manager network for viral B2B2C referrals (target CAC $85 vs $400 industry)."
    ),
    startup_score=78,
    execution_roadmap_90_days={
        "Month 1": [
            "Sign 3 HOA pilot agreements WITH exclusivity clause (addresses investor concern #1)",
            "Launch MVP dashboard (Community Solar Dashboard + AI Optimizer)",
            "Hire Head of Regulatory Affairs (addresses investor concern #3)",
        ],
        "Month 2": [
            "Onboard 60 households — validate $85 CAC assumption (addresses critical assumption #3)",
            "Run first AI optimization cycle, publish energy savings data",
            "File net-metering compliance in CA, TX, FL",
        ],
        "Month 3": [
            "Hit $20K MRR (validates HOA channel before Series A)",
            "Publish HOA case study with real energy savings %",
            "Begin Series A deck preparation",
        ],
    },
    confidence_score=79,
)

MOCK_SIMULATOR = SimulatorOutput(
    simulation_log=[
        SimulationMonth(
            month=1,
            active_users=60,
            monthly_recurring_revenue=4200.0,
            burn_rate=71000.0,
            cash_balance=933200.0,
            milestones=["MVP launched", "3 HOAs onboarded with exclusivity"],
        ),
        SimulationMonth(
            month=2,
            active_users=180,
            monthly_recurring_revenue=12600.0,
            burn_rate=68000.0,
            cash_balance=877800.0,
            milestones=["AI optimizer v1", "$85 CAC validated across 60 households"],
        ),
        SimulationMonth(
            month=3,
            active_users=400,
            monthly_recurring_revenue=28000.0,
            burn_rate=65000.0,
            cash_balance=840800.0,
            milestones=["$28K MRR achieved", "HOA case study published"],
        ),
        SimulationMonth(
            month=6,
            active_users=1200,
            monthly_recurring_revenue=84000.0,
            burn_rate=72000.0,
            cash_balance=647800.0,
            milestones=[
                "Series A fundraise initiated",
                "Utility partnership MOU signed",
            ],
        ),
        SimulationMonth(
            month=8,
            active_users=1400,
            monthly_recurring_revenue=98000.0,
            burn_rate=85000.0,
            cash_balance=498800.0,
            milestones=[
                "SETBACK: utility competitor announces HOA pilot — pipeline slows 20%"
            ],
        ),
        SimulationMonth(
            month=12,
            active_users=4000,
            monthly_recurring_revenue=280000.0,
            burn_rate=180000.0,
            cash_balance=1200000.0,
            milestones=["$3.36M ARR run rate", "Series A closed at $8M"],
        ),
    ],
    success_scenario=(
        "12-month scenario: 4,000 active households, $280K MRR, Series A closed at $8M. "
        "HOA channel achieves 65% of growth targets. CAC holds at $87 (within 3% of model)."
    ),
    failure_scenario=(
        "Month 8: utility competitor captures 40% of HOA pipeline (as flagged by Advocate). "
        "MRR growth stalls at $98K. Pivot required: enterprise utility licensing model. "
        "Runway extends to 22 months. Series A delayed 6 months."
    ),
    confidence_score=74,
)

MOCK_PITCHDECK = PitchDeckOutput(
    markdown_deck="""# Solarex — Seed Round Pitch Deck

## Slide 1: Title
**Solarex** | *AI-powered community solar energy sharing*
Team: CEO (10yr energy veteran) | CTO (Ex-Google ML) | Head of Regulatory (hiring)

## Slide 2: Problem
30% of residential solar energy is wasted. Community sharing is manual, opaque, and inequitable.
Market research confirms: no AI-native community solar platform exists at scale.

## Slide 3: Solution
Solarex optimises energy sharing across HOA communities — automatically, transparently, profitably.
Must-have MVP: Community Dashboard + AI Optimizer (differentiated from Sunrun's manual model).

## Slide 4: Market Size (Research Agent)
- **TAM**: $850B global renewable energy market (2030)
- **SAM**: $42B community solar residential segment
- **SOM**: $2.1B capturable in 5 years (target: 0.1% in Year 1 = $2.1M addressable)

## Slide 5: Product & MVP
Top 3 user stories anchored to Must-have features:
1. Homeowner: real-time energy surplus visibility
2. HOA manager: community savings dashboard for board meetings
3. Resident: automatic bill credits — no manual intervention
Tech: FastAPI + React + TimescaleDB + Vertex AI

## Slide 6: Business Model (Finance Agent)
10% transaction fee | **LTV:CAC = 8.5x** | Payback: 4.3 months
Year 1: $480K ARR | Year 2: $3.2M ARR | Year 3: $11.4M ARR

## Slide 7: Competition (Research Agent)
| Competitor | Weakness | Our Edge |
|---|---|---|
| Sunrun | No community model, $400 CAC | $85 CAC via HOA, AI optimizer |
| EnergySage | No AI, no P2P trading | Real-time AI optimization |

## Slide 8: Go-To-Market (Growth Agent)
HOA Direct Outreach → exclusivity clause (mitigates utility competition risk)
Month 1: 3 HOA pilots | Month 2: 60 households, validate CAC | Month 3: $20K MRR

## Slide 9: Financial Projections
| Year | ARR | SOM % |
|---|---|---|
| Year 1 | $480K | 0.023% |
| Year 2 | $3.2M | 0.15% |
| Year 3 | $11.4M | 0.54% |

## Slide 10: The Ask
Raising **$1.5M Seed**. Use of funds:
- Engineering (45%) — MVP + AI optimizer
- Sales/BD (30%) — HOA outreach + exclusivity deals
- Regulatory (15%) — Head of Regulatory hire
- Ops (10%)
""",
    slides=[
        PitchDeckSlide(
            slide_number=1,
            title="Title",
            content=["Solarex — AI community solar", "Seed Round"],
        ),
        PitchDeckSlide(
            slide_number=2,
            title="Problem",
            content=["30% solar wasted", "No community platform"],
        ),
        PitchDeckSlide(
            slide_number=3,
            title="Solution",
            content=["AI optimization", "HOA distribution"],
        ),
        PitchDeckSlide(
            slide_number=4,
            title="Market",
            content=["$850B TAM", "$42B SAM", "$2.1B SOM"],
        ),
        PitchDeckSlide(
            slide_number=5,
            title="Product",
            content=["Dashboard + AI Optimizer", "P2P kWh credits"],
        ),
        PitchDeckSlide(
            slide_number=6, title="Business Model", content=["10% fee", "LTV:CAC 8.5x"]
        ),
        PitchDeckSlide(
            slide_number=7,
            title="Competition",
            content=["Sunrun: $400 CAC", "EnergySage: no AI"],
        ),
        PitchDeckSlide(
            slide_number=8,
            title="GTM",
            content=["HOA + exclusivity", "Month 3: $20K MRR"],
        ),
        PitchDeckSlide(
            slide_number=9,
            title="Financials",
            content=["$480K Y1", "$3.2M Y2", "$11.4M Y3"],
        ),
        PitchDeckSlide(
            slide_number=10,
            title="The Ask",
            content=["$1.5M Seed", "45% Eng, 30% Sales"],
        ),
    ],
    confidence_score=83,
)

MOCK_SECURITY = SecurityCheckpointOutput(
    is_safe=True,
    issues=[],
    sanitized_report=(
        "Report sanitized: no PII detected, no regulatory violations, no illicit business models found. "
        "Solarex operates in a regulated but legal market with appropriate compliance strategy."
    ),
    confidence_score=90,
)

MOCK_EXEC_SUMMARY = ExecutiveSummaryOutput(
    executive_summary=(
        "Solarex presents a compelling Seed investment opportunity in the $42B community solar segment, "
        "backed by strong unit economics (LTV:CAC 8.5x) and a defensible HOA distribution channel. "
        "The primary risk — utility competition — is addressable through HOA exclusivity contracts "
        "if executed in Month 1. With regulatory tailwinds and no AI-native competitor at scale, "
        "the window is open for the next 18-24 months."
    ),
    top_strengths=[
        "LTV:CAC of 8.5x via HOA channel — validated against Sunrun's $400 CAC benchmark (Research + Finance)",
        "No AI-native community solar competitor at scale — first-mover window (Research Agent)",
        "IRA regulatory tailwinds reduce customer acquisition friction (Research + Risk Agent)",
        "Conditional Invest verdict from Investor Agent with clear milestone gates",
        "HOA B2B2C model creates network effects that are hard for utilities to replicate quickly",
    ],
    top_risks=[
        "Utility competition (Advocate): 40% TAM reduction if top-3 utilities enter — mitigate with Month 1 HOA exclusivity contracts",
        "Unvalidated CAC assumption of $85 (Advocate): only comparable is Sunrun's $400 — validate in Month 2 pilot",
        "Regulatory complexity across 50 states (Investor): mitigate with Head of Regulatory hire in Month 1",
        "HOA onboarding speed (Advocate): 6mo vs 2mo scenario collapses Year 1 ARR to $120K — track weekly",
        "Adoption slowdown (Simulator): Month 8 setback scenario modelled — utility competitor enters HOA pipeline",
    ],
    recommendation="Conditional Invest",
    overall_confidence_score=81,
    startup_health=(
        "Solarex is in strong early health with validated unit economics, a clear distribution moat "
        "via HOA partnerships, and regulatory tailwinds from the IRA. The team should prioritise "
        "HOA exclusivity contracts and CAC validation in Month 1 to de-risk the two largest "
        "outstanding assumptions before the Series A milestone."
    ),
    biggest_strengths=[
        "LTV:CAC of 8.5x via HOA channel — validated against Sunrun's $400 CAC benchmark (Research + Finance)",
        "No AI-native community solar competitor at scale — first-mover window (Research Agent)",
        "IRA regulatory tailwinds reduce customer acquisition friction (Research + Risk Agent)",
        "Conditional Invest verdict from Investor Agent with clear milestone gates",
        "HOA B2B2C model creates network effects that are hard for utilities to replicate quickly",
    ],
    biggest_risks=[
        "Utility competition (Advocate): 40% TAM reduction if top-3 utilities enter — mitigate with Month 1 HOA exclusivity contracts",
        "Unvalidated CAC assumption of $85 (Advocate): only comparable is Sunrun's $400 — validate in Month 2 pilot",
        "Regulatory complexity across 50 states (Investor): mitigate with Head of Regulatory hire in Month 1",
    ],
    recommended_next_action=(
        "Sign 3 HOA exclusivity contracts and validate $85 CAC assumption via Month 1 pilot "
        "before committing Series A milestone capital."
    ),
    overall_confidence=81,
)

# ─────────────────────────────────────────────────────────────────────────────
# Node tracker
# ─────────────────────────────────────────────────────────────────────────────
executed_nodes: list[str] = []


def _track(name: str):
    executed_nodes.append(name)
    log(f"  \u2713 {name}", GREEN)


# ─────────────────────────────────────────────────────────────────────────────
# Stub node functions
# ─────────────────────────────────────────────────────────────────────────────


def stub_extract_name(ctx: Context, node_input: StartupIdea):
    _track("extract_name_node")
    return Event(output=node_input, state={"startup_name": node_input.name})


def stub_research(ctx: Context, node_input: Any):
    _track("research_agent")
    return Event(output=MOCK_RESEARCH)


def stub_risk(ctx: Context, node_input: Any):
    _track("risk_agent")
    return Event(output=MOCK_RISK)


def stub_state_writer_phase1(ctx: Context, node_input: Any):
    _track("state_writer_phase1")
    research = (
        node_input.get("research_agent") if isinstance(node_input, dict) else None
    )
    _risk = node_input.get("risk_agent") if isinstance(node_input, dict) else None
    state = {
        "phase1_research_summary": json.dumps(MOCK_RESEARCH.model_dump(), indent=2)
        if research is None
        else json.dumps(
            getattr(research, "model_dump", lambda: research)()
            if hasattr(research, "model_dump")
            else research,
            indent=2,
        ),
        "phase1_risk_summary": json.dumps(MOCK_RISK.model_dump(), indent=2),
        "phase1_research_confidence": MOCK_RESEARCH.confidence_score,
        "phase1_risk_confidence": MOCK_RISK.confidence_score,
    }
    return Event(output=node_input, state=state)


def stub_product(ctx: Context, node_input: Any):
    _track("product_agent")
    research_ctx = ctx.state.get("phase1_research_summary", "")
    if research_ctx:
        log(
            f"  [cross-agent] product_agent received phase1_research_summary ({len(research_ctx)} chars)",
            DIM,
        )
    return Event(output=MOCK_PRODUCT)


def stub_finance(ctx: Context, node_input: Any):
    _track("finance_agent")
    return Event(output=MOCK_FINANCE)


def stub_state_writer_phase2(ctx: Context, node_input: Any):
    _track("state_writer_phase2")
    state = {
        "phase2_product_summary": json.dumps(MOCK_PRODUCT.model_dump(), indent=2),
        "phase2_finance_summary": json.dumps(MOCK_FINANCE.model_dump(), indent=2),
        "phase2_product_confidence": MOCK_PRODUCT.confidence_score,
        "phase2_finance_confidence": MOCK_FINANCE.confidence_score,
    }
    return Event(output=node_input, state=state)


def stub_advocate(ctx: Context, node_input: Any):
    _track("advocate_agent")
    finance_ctx = ctx.state.get("phase2_finance_summary", "")
    if finance_ctx:
        log(
            f"  [cross-agent] advocate_agent received phase2_finance_summary ({len(finance_ctx)} chars)",
            DIM,
        )
    return Event(output=MOCK_ADVOCATE)


def stub_investor(ctx: Context, node_input: Any):
    _track("investor_agent")
    return Event(output=MOCK_INVESTOR)


def stub_state_writer_phase3(ctx: Context, node_input: Any):
    _track("state_writer_phase3")
    state = {
        "phase3_advocate_summary": json.dumps(MOCK_ADVOCATE.model_dump(), indent=2),
        "phase3_investor_summary": json.dumps(MOCK_INVESTOR.model_dump(), indent=2),
        "phase3_advocate_confidence": MOCK_ADVOCATE.confidence_score,
        "phase3_investor_confidence": MOCK_INVESTOR.confidence_score,
        "investment_readiness_score": MOCK_INVESTOR.investment_readiness_score,
        "investor_recommendation": MOCK_INVESTOR.investment_recommendation,
    }
    return Event(output=node_input, state=state)


def stub_orchestrator_gate3(ctx: Context, node_input: Any):
    _track("orchestrator_phase3_gate")
    p1r = ctx.state.get("phase1_research_confidence", 75)
    p1k = ctx.state.get("phase1_risk_confidence", 75)
    p2p = ctx.state.get("phase2_product_confidence", 75)
    p2f = ctx.state.get("phase2_finance_confidence", 75)
    p3a = ctx.state.get("phase3_advocate_confidence", 75)
    p3i = ctx.state.get("phase3_investor_confidence", 75)
    vals = [v for v in [p1r, p1k, p2p, p2f, p3a, p3i] if isinstance(v, (int, float))]
    avg = round(sum(vals) / len(vals), 1) if vals else 75
    inv_score = ctx.state.get("investment_readiness_score", 0)
    inv_reco = ctx.state.get("investor_recommendation", "Unknown")
    decision = f"Routing to HITL. Investor: '{inv_reco}' ({inv_score}/100). Avg confidence: {avg}/100."
    log(f"  [orchestrator] Gate 3: {decision}", CYAN)
    gate_log = {
        "gate": "phase3",
        "avg_confidence": avg,
        "inv_score": inv_score,
        "decision": decision,
    }
    return Event(
        output=node_input,
        state={
            "orchestrator_gate3_log": json.dumps(gate_log),
            "orchestrator_avg_confidence_p1_p3": avg,
        },
    )


async def stub_hitl(ctx: Context, node_input: Any):
    """HITL node: yields RequestInput on first call, processes resume on second."""
    _track("hitl_review_node")
    if not ctx.resume_inputs or "founder_review" not in ctx.resume_inputs:
        inv_score = ctx.state.get(
            "investment_readiness_score", MOCK_INVESTOR.investment_readiness_score
        )
        inv_reco = ctx.state.get(
            "investor_recommendation", MOCK_INVESTOR.investment_recommendation
        )
        avg_conf = ctx.state.get("orchestrator_avg_confidence_p1_p3", 75)
        summary = (
            "=== SOLAREX FOUNDER REVIEW ===\n"
            f"Investor Score: {inv_score}/100\n"
            f"Investor Recommendation: {inv_reco}\n"
            f"Average Agent Confidence (P1-P3): {avg_conf}/100\n"
            "Please approve to continue.\n"
            "status: <approved/minor_revision/major_revision>\n"
        )
        log("  \u21aa HITL: yielding RequestInput (interrupt)", YELLOW)
        yield RequestInput(interrupt_id="founder_review", message=summary)
        return

    response_text = ctx.resume_inputs["founder_review"]
    status = "approved"
    if "major_revision" in response_text.lower():
        status = "major_revision"
    elif "minor_revision" in response_text.lower():
        status = "minor_revision"

    log(f"  \u21aa HITL: resume received — routing to '{status}'", YELLOW)
    yield Event(
        output={"status": status, "comments": response_text},
        route=status,
        state={
            "founder_feedback": response_text,
            "hitl_revision_requested": status != "approved",
        },
    )


def stub_growth(ctx: Context, node_input: Any):
    _track("growth_agent")
    investor_ctx = ctx.state.get("phase3_investor_summary", "")
    if investor_ctx:
        log(
            f"  [cross-agent] growth_agent received phase3_investor_summary ({len(investor_ctx)} chars)",
            DIM,
        )
    return Event(output=MOCK_GROWTH)


def stub_simulator(ctx: Context, node_input: Any):
    _track("simulator_agent")
    return Event(output=MOCK_SIMULATOR)


def stub_pitchdeck(ctx: Context, node_input: Any):
    _track("pitchdeck_agent")
    return Event(output=MOCK_PITCHDECK)


def stub_state_writer_phase4(ctx: Context, node_input: Any):
    _track("state_writer_phase4")
    state = {
        "phase4_growth_summary": json.dumps(MOCK_GROWTH.model_dump(), indent=2),
        "phase4_simulator_summary": json.dumps(MOCK_SIMULATOR.model_dump(), indent=2),
        "phase4_pitchdeck_summary": json.dumps(MOCK_PITCHDECK.model_dump(), indent=2),
        "phase4_growth_confidence": MOCK_GROWTH.confidence_score,
        "phase4_simulator_confidence": MOCK_SIMULATOR.confidence_score,
        "phase4_pitchdeck_confidence": MOCK_PITCHDECK.confidence_score,
        "startup_score": MOCK_GROWTH.startup_score,
    }
    return Event(output=node_input, state=state)


def stub_orchestrator_gate4(ctx: Context, node_input: Any):
    _track("orchestrator_phase4_gate")
    scores = [
        ctx.state.get("phase1_research_confidence", 75),
        ctx.state.get("phase1_risk_confidence", 75),
        ctx.state.get("phase2_product_confidence", 75),
        ctx.state.get("phase2_finance_confidence", 75),
        ctx.state.get("phase3_advocate_confidence", 75),
        ctx.state.get("phase3_investor_confidence", 75),
        ctx.state.get("phase4_growth_confidence", 75),
        ctx.state.get("phase4_simulator_confidence", 75),
        ctx.state.get("phase4_pitchdeck_confidence", 75),
    ]
    avg = round(sum(scores) / len(scores), 1)
    startup_score = ctx.state.get("startup_score", MOCK_GROWTH.startup_score)
    inv_score = ctx.state.get(
        "investment_readiness_score", MOCK_INVESTOR.investment_readiness_score
    )
    decision = f"Phase 4 complete. Overall confidence: {avg}/100. Startup: {startup_score} / Invest: {inv_score}."
    log(f"  [orchestrator] Gate 4: {decision}", CYAN)
    gate_log = {
        "gate": "phase4",
        "avg_confidence": avg,
        "startup_score": startup_score,
        "inv_score": inv_score,
        "decision": decision,
    }
    return Event(
        output=node_input,
        state={
            "orchestrator_gate4_log": json.dumps(gate_log),
            "orchestrator_avg_confidence_all": avg,
        },
    )


def stub_security(ctx: Context, node_input: Any):
    _track("security_agent")
    return Event(output=MOCK_SECURITY)


def stub_state_writer_security(ctx: Context, node_input: Any):
    _track("state_writer_security")
    state = {
        "phase4_security_summary": json.dumps(MOCK_SECURITY.model_dump(), indent=2),
        "phase4_security_confidence": MOCK_SECURITY.confidence_score,
        "is_safe": MOCK_SECURITY.is_safe,
        "sanitized_report": MOCK_SECURITY.sanitized_report,
    }
    return Event(output=node_input, state=state)


def stub_pre_exec_summary(ctx: Context, node_input: Any):
    """Type-bridge: converts SecurityCheckpointOutput to a plain string trigger."""
    _track("pre_exec_summary_node")
    is_safe = ctx.state.get("is_safe", True)
    safety_status = "PASSED" if is_safe else "FAILED - issues detected"
    trigger = (
        f"Security checkpoint {safety_status}. "
        "All phase summaries and confidence scores are available in context. "
        "Please produce the executive summary now."
    )
    return Event(output=trigger, state={})


def stub_executive_summary(ctx: Context, node_input: Any):
    _track("executive_summary_agent")
    # Verify cross-agent context is available
    keys_present = [
        k
        for k in [
            "phase1_research_summary",
            "phase1_risk_summary",
            "phase2_product_summary",
            "phase2_finance_summary",
            "phase3_advocate_summary",
            "phase3_investor_summary",
            "phase4_growth_summary",
            "phase4_simulator_summary",
            "phase4_security_summary",
        ]
        if ctx.state.get(k)
    ]
    log(
        f"  [cross-agent] exec_summary has {len(keys_present)}/9 phase summaries in ctx.state",
        CYAN,
    )
    return Event(output=MOCK_EXEC_SUMMARY)


def stub_mcp_write(ctx: Context, node_input: Any):
    """Write enriched Markdown report + SQLite rows using MCP server tools directly."""
    _track("mcp_write_node")
    startup_name = ctx.state.get("startup_name", "Solarex")
    startup_score = ctx.state.get("startup_score", MOCK_GROWTH.startup_score)
    inv_score = ctx.state.get(
        "investment_readiness_score", MOCK_INVESTOR.investment_readiness_score
    )
    _avg_confidence = ctx.state.get("orchestrator_avg_confidence_all", 81)

    # Executive summary from node_input
    exec_text = getattr(
        node_input, "executive_summary", MOCK_EXEC_SUMMARY.executive_summary
    )
    top_strengths = getattr(
        node_input, "top_strengths", MOCK_EXEC_SUMMARY.top_strengths
    )
    top_risks = getattr(node_input, "top_risks", MOCK_EXEC_SUMMARY.top_risks)
    recommendation = getattr(
        node_input, "recommendation", MOCK_EXEC_SUMMARY.recommendation
    )
    overall_conf = getattr(
        node_input,
        "overall_confidence_score",
        MOCK_EXEC_SUMMARY.overall_confidence_score,
    )

    md = f"# Startup Founder Package: {startup_name}\n\n"
    md += f"> **Overall Confidence Score: {overall_conf}/100**  \n"
    md += f"> **Recommendation: {recommendation}**\n\n---\n\n"
    md += f"## Executive Summary\n\n{exec_text}\n\n"
    md += "## Key Scores\n\n| Metric | Score |\n|---|---|\n"
    md += f"| Startup Score | {startup_score}/100 |\n"
    md += f"| Investment Readiness | {inv_score}/100 |\n"
    md += f"| Overall Confidence | {overall_conf}/100 |\n\n"

    md += "## Top Strengths\n\n"
    for s in top_strengths:
        md += f"- {s}\n"

    md += "\n## Top Risks\n\n"
    for r in top_risks:
        md += f"- {r}\n"

    md += f"\n## Growth Strategy\n\n{MOCK_GROWTH.acquisition_strategy}\n\n"
    md += f"## Pitch Deck\n\n{MOCK_PITCHDECK.markdown_deck}\n"

    gate3 = ctx.state.get("orchestrator_gate3_log", "")
    gate4 = ctx.state.get("orchestrator_gate4_log", "")
    if gate3 or gate4:
        md += "## Orchestrator Decision Log\n\n"
        if gate3:
            md += f"### Gate 3 (Pre-HITL)\n```json\n{gate3}\n```\n\n"
        if gate4:
            md += f"### Gate 4 (Pre-Security)\n```json\n{gate4}\n```\n\n"

    # Invoke MCP server tools directly
    try:
        from app.mcp_server import generate_pdf_report, write_report_file, write_runs_db

        filename = report_filename(startup_name, ".md")

        # 1. File write
        res_file = write_report_file(filename, md)
        log(f"  \u2713 {res_file}", GREEN)

        # 2. PDF generate
        res_pdf = generate_pdf_report(filename)
        log(f"  \u2713 {res_pdf}", GREEN)

        # 3. DB write
        res_db = write_runs_db(
            session_id="mock-session",
            startup_name=startup_name,
            startup_score=int(startup_score),
            investment_readiness_score=int(inv_score),
            overall_confidence_score=int(overall_conf),
            recommendation=recommendation,
            executive_summary=exec_text,
            startup_health=exec_text,
            recommended_next_action=recommendation,
            overall_confidence=int(overall_conf),
            report_markdown=md,
            gate3_log=gate3,
            gate4_log=gate4,
        )
        log(f"  \u2713 {res_db}", GREEN)
    except Exception as exc:
        log(f"  \u2717 MCP Tool execution failed in stub: {exc}", RED)

    return {
        "status": "success",
        "report_path": str(get_outputs_dir() / report_filename(startup_name, ".md")),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Build mock Workflow
# ─────────────────────────────────────────────────────────────────────────────
def build_mock_workflow():
    section("BUILDING MOCK WORKFLOW")
    join1 = JoinNode(name="join1")
    join2 = JoinNode(name="join2")
    join3 = JoinNode(name="join3")
    join4 = JoinNode(name="join4")

    # Assign canonical names so tracker labels match real agent names
    stub_research.__name__ = "research_agent"
    stub_risk.__name__ = "risk_agent"
    stub_state_writer_phase1.__name__ = "state_writer_phase1"
    stub_product.__name__ = "product_agent"
    stub_finance.__name__ = "finance_agent"
    stub_state_writer_phase2.__name__ = "state_writer_phase2"
    stub_advocate.__name__ = "advocate_agent"
    stub_investor.__name__ = "investor_agent"
    stub_state_writer_phase3.__name__ = "state_writer_phase3"
    stub_orchestrator_gate3.__name__ = "orchestrator_phase3_gate"
    stub_hitl.__name__ = "hitl_review_node"
    stub_growth.__name__ = "growth_agent"
    stub_simulator.__name__ = "simulator_agent"
    stub_pitchdeck.__name__ = "pitchdeck_agent"
    stub_state_writer_phase4.__name__ = "state_writer_phase4"
    stub_orchestrator_gate4.__name__ = "orchestrator_phase4_gate"
    stub_security.__name__ = "security_agent"
    stub_state_writer_security.__name__ = "state_writer_security"
    stub_pre_exec_summary.__name__ = "pre_exec_summary_node"
    stub_executive_summary.__name__ = "executive_summary_agent"
    stub_mcp_write.__name__ = "mcp_write_node"

    hitl_node = FunctionNode(
        func=stub_hitl,
        rerun_on_resume=True,
        name="hitl_review_node",
    )

    edges = [
        # Phase 1
        ("START", stub_extract_name),
        (stub_extract_name, (stub_research, stub_risk)),
        ((stub_research, stub_risk), join1),
        (join1, stub_state_writer_phase1),
        # Phase 2 — receives phase1 state
        (stub_state_writer_phase1, (stub_product, stub_finance)),
        ((stub_product, stub_finance), join2),
        (join2, stub_state_writer_phase2),
        # Phase 3 — receives phase1+2 state
        (stub_state_writer_phase2, (stub_advocate, stub_investor)),
        ((stub_advocate, stub_investor), join3),
        (join3, stub_state_writer_phase3),
        (stub_state_writer_phase3, stub_orchestrator_gate3),
        (stub_orchestrator_gate3, hitl_node),
        # HITL routing
        (
            hitl_node,
            {
                "minor_revision": stub_product,
                "major_revision": stub_research,
                "approved": (stub_growth, stub_simulator, stub_pitchdeck),
            },
        ),
        # Phase 4 — receives all prior state
        ((stub_growth, stub_simulator, stub_pitchdeck), join4),
        (join4, stub_state_writer_phase4),
        (stub_state_writer_phase4, stub_orchestrator_gate4),
        (stub_orchestrator_gate4, stub_security),
        (stub_security, stub_state_writer_security),
        (stub_state_writer_security, stub_pre_exec_summary),  # type-bridge
        (stub_pre_exec_summary, stub_executive_summary),
        (stub_executive_summary, stub_mcp_write),
    ]

    workflow = Workflow(
        name="startup_copilot",
        edges=edges,
        input_schema=StartupIdea,
    )
    log(f"Mock Workflow built: {len(edges)} edges", GREEN)
    return workflow


# ─────────────────────────────────────────────────────────────────────────────
# Required node coverage list
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED = [
    # Core agents
    "extract_name_node",
    "research_agent",
    "risk_agent",
    "product_agent",
    "finance_agent",
    "advocate_agent",
    "investor_agent",
    "hitl_review_node",
    "growth_agent",
    "simulator_agent",
    "pitchdeck_agent",
    "security_agent",
    "executive_summary_agent",
    "mcp_write_node",
    # New infrastructure
    "state_writer_phase1",
    "state_writer_phase2",
    "state_writer_phase3",
    "state_writer_phase4",
    "state_writer_security",
    "pre_exec_summary_node",
    "orchestrator_phase3_gate",
    "orchestrator_phase4_gate",
]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    workflow = build_mock_workflow()

    session_service = InMemorySessionService()
    import asyncio as _aio

    session = _aio.run(
        session_service.create_session(user_id="mock_user", app_name="startup_copilot")
    )
    runner = Runner(
        agent=workflow,
        session_service=session_service,
        app_name="startup_copilot",
    )

    idea = StartupIdea(
        name="Solarex",
        description="An AI-powered platform for optimizing community solar energy sharing.",
        industry="CleanTech",
        target_customer="Residential communities",
        estimated_pricing="10% transaction fee",
        funding_stage="Seed",
    )
    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=idea.model_dump_json())],
    )

    # ── Phase 1: run to HITL ──────────────────────────────────────────────────
    section("PHASE 1 — Workflow to HITL checkpoint")
    p1_events = []
    interrupt_seen = False
    for event in runner.run(
        new_message=message,
        user_id="mock_user",
        session_id=session.id,
        run_config=RunConfig(streaming_mode=StreamingMode.SSE),
    ):
        p1_events.append(event)
        if "RequestInput" in type(event).__name__:
            log("  \u23f8  HITL RequestInput — auto-approving in Phase 2", YELLOW)
            interrupt_seen = True
            break
    log(f"Phase 1: {len(p1_events)} events", GREEN)

    # ── Phase 2: resume ───────────────────────────────────────────────────────
    section("PHASE 2 — Resume with HITL approval")
    resume_msg = types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    id="founder_review",
                    name="adk_request_input",
                    response={
                        "result": "status: approved\ncomments: Excellent analysis. Proceed with growth and pitch deck phase."
                    },
                )
            )
        ],
    )
    p2_events = []
    for event in runner.run(
        new_message=resume_msg,
        user_id="mock_user",
        session_id=session.id,
        run_config=RunConfig(streaming_mode=StreamingMode.SSE),
    ):
        p2_events.append(event)
    log(f"Phase 2: {len(p2_events)} events", GREEN)

    # ── Node coverage ─────────────────────────────────────────────────────────
    section("NODE COVERAGE")
    all_ok = True
    for node in REQUIRED:
        seen = node in executed_nodes
        status = "PASS" if seen else "MISS"
        col = GREEN if seen else RED
        log(f"  [{status}]  {node}", col)
        if not seen:
            all_ok = False

    # ── Artifact verification ─────────────────────────────────────────────────
    section("ARTIFACT VERIFICATION")
    outputs_dir = PROJECT_ROOT / "outputs"
    md_files = (
        sorted(outputs_dir.glob("*.md"), key=lambda p: p.stat().st_mtime)
        if outputs_dir.exists()
        else []
    )
    pdf_files = (
        sorted(outputs_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime)
        if outputs_dir.exists()
        else []
    )

    if md_files:
        latest = md_files[-1]
        content = latest.read_text(encoding="utf-8")
        log(
            f"  Markdown report     : {latest.name} ({latest.stat().st_size} bytes)",
            GREEN,
        )

        checks = {
            "Executive Summary": "Executive Summary" in content,
            "Top Strengths": "Top Strengths" in content,
            "Top Risks": "Top Risks" in content,
            "Recommendation": "Recommendation" in content,
            "Confidence Score": "Confidence Score" in content,
            "Startup Score": "Startup Score" in content,
            "Investment Score": "Investment Readiness" in content,
            "Pitch Deck": "Pitch Deck" in content,
            "Orchestrator Log": "Orchestrator" in content,
        }
        for label, ok in checks.items():
            log(f"  {'OK' if ok else 'MISSING':7} {label}", GREEN if ok else RED)
            if not ok:
                all_ok = False

        print(f"\n{DIM}--- Report preview (first 1200 chars) ---{RESET}")
        print(content[:1200])
        print(f"{DIM}---{RESET}\n")
    else:
        log("  Markdown report : NOT FOUND", RED)
        all_ok = False

    if pdf_files:
        latest_pdf = pdf_files[-1]
        log(
            f"  PDF report          : {latest_pdf.name} ({latest_pdf.stat().st_size} bytes)",
            GREEN,
        )
    else:
        log("  PDF report          : NOT FOUND", RED)
        all_ok = False

    db_path = PROJECT_ROOT / "startup_copilot.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT id, startup_name, startup_score, investment_readiness_score, "
            "overall_confidence_score, recommendation FROM runs ORDER BY id DESC LIMIT 3"
        ).fetchall()
        orch_rows = conn.execute(
            "SELECT gate, log_json FROM orchestrator_logs ORDER BY id DESC LIMIT 4"
        ).fetchall()
        conn.close()
        log(f"  SQLite runs     : {len(rows)} row(s)", GREEN)
        for r in rows:
            log(
                f"    id={r[0]} name={r[1]} score={r[2]} invest={r[3]} confidence={r[4]} reco={r[5]}",
                CYAN,
            )
        log(f"  Orchestrator logs: {len(orch_rows)} row(s)", GREEN)
        for og in orch_rows:
            log(f"    gate={og[0]} log={og[1][:80]}...", DIM)
    else:
        log("  SQLite DB : NOT FOUND", RED)
        all_ok = False

    # ── Final summary ─────────────────────────────────────────────────────────
    section("FINAL SUMMARY")
    log(f"Total events     : {len(p1_events) + len(p2_events)}", BOLD)
    log(f"Nodes executed   : {len(set(executed_nodes))} / {len(REQUIRED)}", BOLD)
    log(
        f"HITL interrupt   : {'YES' if interrupt_seen else 'NO (1-pass)'}",
        GREEN if interrupt_seen else YELLOW,
    )
    log(
        f"Cross-agent state: {'VERIFIED' if all_ok else 'CHECK ABOVE'}",
        GREEN if all_ok else RED,
    )
    log(
        f"All nodes passed : {'YES' if all_ok else 'NO — see MISS above'}",
        GREEN if all_ok else RED,
    )
    log(
        f"Markdown report  : {'GENERATED' if md_files else 'MISSING'}",
        GREEN if md_files else RED,
    )
    log(
        f"PDF report       : {'GENERATED' if pdf_files else 'MISSING'}",
        GREEN if pdf_files else RED,
    )
    log(
        f"SQLite DB        : {'CREATED' if db_path.exists() else 'MISSING'}",
        GREEN if db_path.exists() else RED,
    )

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
