"""
End-to-end runner for the Startup Copilot AI workflow.

Drives the full graph:
  START -> extract_name -> [research, risk] -> join1
        -> [product, finance] -> join2
        -> [advocate, investor] -> join3
        -> HITL (auto-approved)
        -> [growth, simulator, pitchdeck] -> join4
        -> security -> mcp_write
"""

import json
import os
import sqlite3
import sys
import traceback
from datetime import datetime
from pathlib import Path

# ── Ensure project root is on sys.path ────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Force Vertex AI + suppress credential noise ────────────────────────────────
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# ─────────────────────────────────────────────────────────────────────────────
# Colour helpers for terminal output
# ─────────────────────────────────────────────────────────────────────────────
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log(msg, colour=RESET):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{colour}[{ts}] {msg}{RESET}", flush=True)


def section(title):
    print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 60}{RESET}\n", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Node tracker
# ─────────────────────────────────────────────────────────────────────────────
NODE_LABELS = {
    "extract_name_node": "Name Extractor",
    "research_agent": "Research",
    "risk_agent": "Risk",
    "product_agent": "Product",
    "finance_agent": "Finance",
    "advocate_agent": "Devil's Advocate",
    "investor_agent": "Investor",
    "hitl_review_node": "HITL Review",
    "growth_agent": "Growth",
    "simulator_agent": "Simulator",
    "pitchdeck_agent": "Pitch Deck",
    "security_agent": "Security",
    "mcp_write_node": "SQLite Writer",
    "join1": "Join-1 (research+risk)",
    "join2": "Join-2 (product+finance)",
    "join3": "Join-3 (advocate+investor)",
    "join4": "Join-4 (growth+sim+pitch)",
    "startup_copilot": "Workflow Root",
}

REQUIRED_NODES = [
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
    "mcp_write_node",
]

executed_nodes = set()
event_log = []


def record_event(event):
    """Extract node name from any ADK event object."""
    name = None
    for attr in ("author", "node_name", "agent_name", "name", "source"):
        val = getattr(event, attr, None)
        if val and isinstance(val, str):
            name = val
            break

    payload_preview = ""
    for attr in ("content", "output", "text"):
        val = getattr(event, attr, None)
        if val:
            payload_preview = str(val)[:200]
            break

    label = NODE_LABELS.get(name, name) if name else "unknown"
    event_log.append({"node": name, "label": label, "preview": payload_preview})

    if name:
        was_new = name not in executed_nodes
        executed_nodes.add(name)
        status = "NEW " if was_new else "    "
        log(f"  {status}Event from: {GREEN}{label}{RESET} ({name})")
    return name


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — run until HITL interrupt
# ─────────────────────────────────────────────────────────────────────────────
def run_phase1(runner, session, message):
    section("PHASE 1 — Running to HITL checkpoint")
    events = []
    interrupt_event = None

    for event in runner.run(
        new_message=message,
        user_id="e2e_user",
        session_id=session.id,
        run_config=RunConfig(streaming_mode=StreamingMode.SSE),
    ):
        record_event(event)
        events.append(event)

        # Detect HITL interrupt via multiple possible attributes
        if (
            getattr(event, "interrupt_ids", None)
            or "RequestInput" in type(event).__name__
        ):
            interrupt_event = event
            log("  HITL checkpoint reached — will auto-approve in Phase 2", YELLOW)
            break

    log(
        f"Phase 1 complete: {len(events)} events, {len(executed_nodes)} nodes seen",
        GREEN,
    )
    return events, interrupt_event


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — resume with "approved"
# ─────────────────────────────────────────────────────────────────────────────
def run_phase2(runner, session):
    section("PHASE 2 — Resuming with HITL approval")

    review_response = "status: approved\ncomments: Looks great! Proceed to growth and pitch deck phase."
    resume_message = types.Content(
        role="user", parts=[types.Part.from_text(text=review_response)]
    )

    events = []
    for event in runner.run(
        new_message=resume_message,
        user_id="e2e_user",
        session_id=session.id,
        run_config=RunConfig(streaming_mode=StreamingMode.SSE),
    ):
        record_event(event)
        events.append(event)

    log(f"Phase 2 complete: {len(events)} additional events", GREEN)
    return events


# ─────────────────────────────────────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────────────────────────────────────
def verify_artifacts():
    section("VERIFICATION — Checking generated artifacts")
    results = {}

    # Markdown report
    outputs_dir = PROJECT_ROOT / "outputs"
    md_files = list(outputs_dir.glob("*.md")) if outputs_dir.exists() else []
    if md_files:
        latest = max(md_files, key=lambda p: p.stat().st_mtime)
        size = latest.stat().st_size
        content = latest.read_text(encoding="utf-8")
        log(f"  Markdown report: {latest.name} ({size} bytes)", GREEN)
        results["markdown_report"] = {
            "path": str(latest),
            "size": size,
            "has_pitch_deck": "Pitch Deck" in content,
            "has_startup_score": "Startup Score" in content,
            "has_investment_score": "Investment Readiness" in content,
        }
        log(
            f"    Startup score present    : {'YES' if results['markdown_report']['has_startup_score'] else 'NO'}",
            GREEN if results["markdown_report"]["has_startup_score"] else YELLOW,
        )
        log(
            f"    Investment score present : {'YES' if results['markdown_report']['has_investment_score'] else 'NO'}",
            GREEN if results["markdown_report"]["has_investment_score"] else YELLOW,
        )
        log(
            f"    Pitch deck present       : {'YES' if results['markdown_report']['has_pitch_deck'] else 'NO'}",
            GREEN if results["markdown_report"]["has_pitch_deck"] else YELLOW,
        )
        print("\n--- Report preview (first 800 chars) ---")
        print(content[:800])
        print("---\n", flush=True)
    else:
        log("  No markdown report found in outputs/", RED)
        results["markdown_report"] = None

    # SQLite DB
    db_path = PROJECT_ROOT / "startup_copilot.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 5")
            rows = cursor.fetchall()
            conn.close()
            log(f"  SQLite DB: {db_path.name} — {len(rows)} run(s)", GREEN)
            for row in rows:
                log(f"    Row: {row}", CYAN)
            results["sqlite_db"] = {"path": str(db_path), "rows": rows}
        except Exception as e:
            log(f"  SQLite DB error: {e}", RED)
            results["sqlite_db"] = {"error": str(e)}
    else:
        log("  SQLite DB not found", RED)
        results["sqlite_db"] = None

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Node coverage report
# ─────────────────────────────────────────────────────────────────────────────
def node_coverage_report():
    section("NODE COVERAGE")
    all_ok = True
    for node_id in REQUIRED_NODES:
        label = NODE_LABELS.get(node_id, node_id)
        if node_id in executed_nodes:
            log(f"  PASS  {label}", GREEN)
        else:
            log(f"  MISS  {label}  <- NOT SEEN", RED)
            all_ok = False
    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    section("STARTUP COPILOT — End-to-End Runner")

    log("Importing root_agent from app.agent ...", CYAN)
    try:
        from app.agent import root_agent

        log(f"  root_agent type : {type(root_agent).__name__}", GREEN)
        log(f"  root_agent name : {root_agent.name}", GREEN)
    except Exception as e:
        log(f"  FAIL: Could not import root_agent: {e}", RED)
        traceback.print_exc()
        sys.exit(1)

    # Build runner
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(
        user_id="e2e_user", app_name="startup_copilot"
    )
    runner = Runner(
        agent=root_agent, session_service=session_service, app_name="startup_copilot"
    )
    log(f"Session ID: {session.id}", CYAN)

    # Input
    idea = {
        "name": "Solarex",
        "description": "An AI-powered platform for optimizing community solar energy sharing.",
        "industry": "CleanTech",
        "target_customer": "Residential communities",
        "estimated_pricing": "10% transaction fee",
        "funding_stage": "Seed",
    }
    message = types.Content(
        role="user", parts=[types.Part.from_text(text=json.dumps(idea))]
    )
    log(f"Input startup: {idea['name']} ({idea['industry']})", CYAN)

    # Phase 1
    phase1_events, interrupt_event = run_phase1(runner, session, message)

    # Phase 2 (resume past HITL if needed)
    if interrupt_event is not None or "hitl_review_node" in executed_nodes:
        phase2_events = run_phase2(runner, session)
    else:
        log(
            "No HITL interrupt detected — workflow may have completed in one pass",
            YELLOW,
        )
        phase2_events = []

    # Node coverage
    all_nodes_seen = node_coverage_report()

    # Artifacts
    artifacts = verify_artifacts()

    # Final summary
    section("FINAL SUMMARY")
    total_events = len(phase1_events) + len(phase2_events)
    log(f"Total events processed : {total_events}", BOLD)
    log(f"Unique nodes seen      : {len(executed_nodes)}", BOLD)
    log(
        f"Required nodes covered : {'ALL OK' if all_nodes_seen else 'SOME MISSING'}",
        GREEN if all_nodes_seen else RED,
    )
    log(
        f"Markdown report        : {'OK' if artifacts.get('markdown_report') else 'MISSING'}",
        GREEN if artifacts.get("markdown_report") else RED,
    )
    log(
        f"SQLite DB              : {'OK' if artifacts.get('sqlite_db') and not (artifacts['sqlite_db'] or {}).get('error') else 'MISSING'}",
        GREEN if artifacts.get("sqlite_db") else RED,
    )

    if not all_nodes_seen:
        missing = [
            NODE_LABELS.get(n, n) for n in REQUIRED_NODES if n not in executed_nodes
        ]
        log(f"Missing nodes: {', '.join(missing)}", RED)

    print(flush=True)
    rc = (
        0
        if (
            all_nodes_seen
            and artifacts.get("markdown_report")
            and artifacts.get("sqlite_db")
        )
        else 1
    )
    return rc


if __name__ == "__main__":
    sys.exit(main())
