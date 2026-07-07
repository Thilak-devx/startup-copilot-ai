# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Premium FastAPI Frontend Server for Startup Copilot AI.

Serves static frontend dashboard assets and exposes API endpoints for:
  - Reading runs from SQLite db (/api/runs)
  - Reading generated Markdown/PDF files (/api/reports)
  - Launching analysis runs asynchronously (/api/analyze)
"""

from __future__ import annotations

import logging
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.reporting import (
    get_db_path,
    get_outputs_dir,
    report_filename,
    report_slug,
    safe_report_path,
    startup_slug_from_report_filename,
    write_text_if_changed,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.resolve()
DB_PATH = get_db_path()
OUTPUTS_DIR = get_outputs_dir()
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(
    title="Startup Copilot AI Dashboard API",
    description="Backend API serving premium frontend dashboard and SQLite metrics.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _seed_demo_data_on_startup() -> None:
    """Seed DB + outputs/ with a Solarex demo run on first startup.

    Render's ephemeral filesystem means the DB and output files are lost
    after each deploy.  This handler ensures a completed analysis always
    exists so the Reports page, Markdown export, and PDF export work
    without manual intervention.
    """
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(DB_PATH))
            count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            conn.close()
            if count > 0:
                logger.info(
                    "Seed skipped: DB already has %d run(s).", count
                )
                return
        except (sqlite3.Error, IndexError, TypeError):
            pass

    logger.info("Seeding Solarex demo run into DB and outputs/ ...")
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    startup_name = "Solarex"
    recommendation = "Conditional Invest"
    exec_summary = (
        "Solarex presents a compelling Seed investment opportunity in "
        "the $42B community solar segment, backed by strong unit "
        "economics (LTV:CAC 8.5x) and a defensible HOA distribution "
        "channel. The primary risk \u2014 utility competition \u2014 is "
        "addressable through HOA exclusivity contracts if executed in "
        "Month 1. With regulatory tailwinds and no AI-native competitor "
        "at scale, the window is open for the next 18\u201324 months."
    )
    startup_health = (
        "Solarex is in strong early health with validated unit "
        "economics, a clear distribution moat via HOA partnerships, "
        "and regulatory tailwinds from the IRA."
    )
    next_action = (
        "Sign 3 HOA exclusivity contracts and validate $85 CAC "
        "assumption via Month 1 pilot before committing Series A "
        "milestone capital."
    )

    md = (
        f"# Startup Founder Package: {startup_name}\n\n"
        f"> **Overall Confidence Score: 81/100**  \n"
        f"> **Recommendation: {recommendation}**  \n"
        f"> **Recommended Next Action: {next_action}**\n\n"
        "---\n\n"
        "## Executive Summary\n\n"
        f"{exec_summary}\n\n"
        "## Startup Health\n\n"
        f"{startup_health}\n\n"
        "## Key Scores\n\n"
        "| Metric | Score |\n"
        "|---|---|\n"
        "| Startup Score | 78/100 |\n"
        "| Investment Readiness | 74/100 |\n"
        "| Overall Confidence | 81/100 |\n\n"
        "## Top Strengths\n\n"
        "- LTV:CAC of 8.5x via HOA channel \u2014 validated against "
        "Sunrun's $400 CAC benchmark\n"
        "- No AI-native community solar competitor at scale \u2014 "
        "first-mover window\n"
        "- IRA regulatory tailwinds reduce customer acquisition "
        "friction\n\n"
        "## Top Risks\n\n"
        "- Utility competition: 40% TAM reduction if top-3 utilities "
        "enter \u2014 mitigate with HOA exclusivity\n"
        "- Unvalidated CAC assumption of $85 \u2014 only comparable is "
        "Sunrun's $400\n"
        "- Regulatory complexity across 50 states \u2014 mitigate with "
        "Head of Regulatory hire\n\n"
        "## Pitch Deck\n\n"
        "# Solarex \u2014 Seed Round Pitch Deck\n\n"
        "## Slide 1: Title\n"
        "**Solarex** | *AI-powered community solar energy sharing*\n"
        "Team: CEO (10yr energy veteran) | CTO (Ex-Google ML) | "
        "Head of Regulatory (hiring)\n\n"
        "## Slide 2: Problem\n"
        "30% of residential solar energy is wasted. Community sharing "
        "is manual, opaque, and inequitable.\n\n"
        "## Slide 3: Solution\n"
        "Solarex optimises energy sharing across HOA communities \u2014 "
        "automatically, transparently, profitably.\n\n"
        "## Slide 4: Market Size\n"
        "- **TAM**: $850B global renewable energy market (2030)\n"
        "- **SAM**: $42B community solar residential segment\n"
        "- **SOM**: $2.1B capturable in 5 years\n\n"
        "## Slide 5: Product & MVP\n"
        "1. Homeowner: real-time energy surplus visibility\n"
        "2. HOA manager: community savings dashboard\n"
        "3. Resident: automatic bill credits\n\n"
        "## Slide 6: Business Model\n"
        "10% transaction fee | LTV:CAC = 8.5x | Payback: 4.3 months\n"
        "Year 1: $480K ARR | Year 2: $3.2M ARR | "
        "Year 3: $11.4M ARR\n\n"
        "## Slide 7: Competition\n"
        "| Competitor | Weakness | Our Edge |\n"
        "|---|---|---|\n"
        "| Sunrun | No community model, $400 CAC | "
        "$85 CAC via HOA, AI optimizer |\n"
        "| EnergySage | No AI, no P2P trading | "
        "Real-time AI optimization |\n\n"
        "## Slide 8: Go-To-Market\n"
        "HOA Direct Outreach \u2192 exclusivity clause\n"
        "Month 1: 3 HOA pilots | Month 2: 60 households | "
        "Month 3: $20K MRR\n\n"
        "## Slide 9: Financial Projections\n"
        "| Year | ARR |\n"
        "|---|---|\n"
        "| Year 1 | $480K |\n"
        "| Year 2 | $3.2M |\n"
        "| Year 3 | $11.4M |\n\n"
        "## Slide 10: The Ask\n"
        "Raising $1.5M Seed. Use of funds: Engineering (45%), "
        "Sales/BD (30%), Regulatory (15%), Ops (10%)\n"
    )

    try:
        from app.mcp_server import (
            generate_pdf_report,
            write_report_file,
            write_runs_db,
        )

        filename = report_filename(startup_name, ".md")

        res_file = write_report_file(filename, md)
        logger.info("Seed: %s", res_file)

        res_pdf = generate_pdf_report(filename)
        logger.info("Seed: %s", res_pdf)

        res_db = write_runs_db(
            session_id="seed-session",
            startup_name=startup_name,
            startup_score=78,
            investment_readiness_score=74,
            overall_confidence_score=81,
            recommendation=recommendation,
            executive_summary=exec_summary,
            startup_health=startup_health,
            recommended_next_action=next_action,
            overall_confidence=81,
            report_markdown=md,
        )
        logger.info("Seed: %s", res_db)
        logger.info("Solarex demo seed complete.")
    except Exception as exc:
        logger.error("Seed failed: %s", exc)


class StartupInput(BaseModel):
    name: str
    industry: str
    description: str
    estimated_pricing: str
    target_customer: str
    funding_stage: str


def _safe_report_path(filename: str) -> Path:
    try:
        return safe_report_path(OUTPUTS_DIR, filename)
    except ValueError:
        raise HTTPException(status_code=404, detail="File not found.")


def _runs_table_columns(conn: sqlite3.Connection) -> set[str]:
    try:
        return {row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
    except sqlite3.Error:
        return set()


def _row_value(row: sqlite3.Row, key: str, default: Any = "") -> Any:
    return row[key] if key in row.keys() and row[key] is not None else default


def _report_markdown_from_db(filename: str) -> str | None:
    if not DB_PATH.exists():
        return None

    target_slug = startup_slug_from_report_filename(filename)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if "report_markdown" not in _runs_table_columns(conn):
            return None
        rows = conn.execute(
            """
            SELECT startup_name, report_markdown
            FROM runs
            WHERE report_markdown IS NOT NULL AND report_markdown != ''
            ORDER BY id DESC
            """
        ).fetchall()
        for row in rows:
            if report_slug(_row_value(row, "startup_name")) == target_slug:
                return str(row["report_markdown"])
        return None
    finally:
        conn.close()


def _hydrate_markdown_file(filename: str, target_path: Path) -> bool:
    markdown = _report_markdown_from_db(filename)
    if not markdown:
        return False
    write_text_if_changed(target_path, markdown)
    return True


def _ensure_report_file(filename: str) -> Path:
    safe_path = _safe_report_path(filename)
    if safe_path.exists():
        return safe_path

    if safe_path.suffix == ".md":
        if _hydrate_markdown_file(safe_path.name, safe_path):
            return safe_path
        raise HTTPException(status_code=404, detail="File not found.")

    markdown_path = safe_path.with_suffix(".md")
    if not markdown_path.exists() and not _hydrate_markdown_file(
        markdown_path.name, markdown_path
    ):
        raise HTTPException(status_code=404, detail="File not found.")

    from app.mcp_server import generate_pdf_report

    result = generate_pdf_report(str(markdown_path))
    if safe_path.exists():
        return safe_path

    logger.error("PDF generation failed for %s: %s", markdown_path, result)
    raise HTTPException(status_code=500, detail="PDF generation failed.")


def _report_filenames_from_db() -> set[str]:
    if not DB_PATH.exists():
        return set()

    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        if "report_markdown" not in _runs_table_columns(conn):
            conn.close()
            return set()
        rows = conn.execute(
            """
            SELECT startup_name FROM runs
            WHERE report_markdown IS NOT NULL AND report_markdown != ''
            ORDER BY id DESC
            """
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return set()

    filenames: set[str] = set()
    for row in rows:
        startup_name = _row_value(row, "startup_name")
        if startup_name:
            filenames.add(report_filename(startup_name, ".md"))
            filenames.add(report_filename(startup_name, ".pdf"))
    return filenames


@app.get("/api/runs")
def get_runs() -> list[dict[str, Any]]:
    """Query SQLite database for historical startup runs."""
    if not DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, session_id, startup_name, startup_score,
                   investment_readiness_score, overall_confidence_score,
                   recommendation, executive_summary, startup_health,
                   recommended_next_action, overall_confidence,
                   (SELECT log_json FROM orchestrator_logs WHERE orchestrator_logs.session_id = runs.session_id AND gate = 'phase3' LIMIT 1) AS gate3_log,
                   (SELECT log_json FROM orchestrator_logs WHERE orchestrator_logs.session_id = runs.session_id AND gate = 'phase4' LIMIT 1) AS gate4_log,
                   timestamp
            FROM runs ORDER BY id DESC
            """
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error("get_runs database query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Database query error: {e}") from e


@app.get("/api/reports")
def list_reports() -> list[str]:
    """List Markdown and PDF filenames inside outputs/ directory."""
    files = _report_filenames_from_db()
    if not OUTPUTS_DIR.exists():
        return sorted(files)
    for file_path in OUTPUTS_DIR.iterdir():
        if file_path.is_file() and file_path.suffix in (".md", ".pdf"):
            files.add(file_path.name)
    return sorted(files)


@app.get("/api/reports/{filename}")
def get_report_file(filename: str) -> FileResponse:
    """Serve a Markdown or PDF report from outputs/ directory safely."""
    safe_path = _ensure_report_file(filename)
    media_type = "application/pdf" if filename.endswith(".pdf") else "text/markdown"
    return FileResponse(path=safe_path, filename=filename, media_type=media_type)


@app.post("/api/analyze")
async def trigger_analysis(
    input_data: StartupInput, mode: str = "mock"
) -> dict[str, str]:
    """Trigger the multi-agent analysis graph execution.

    mode: 'mock' (runs mock workflow setup), 'real' (runs full Vertex AI pipeline)
    """
    logger.info("Triggering %s analysis pipeline for: %s", mode, input_data.name)

    script = "run_e2e_mock.py" if mode == "mock" else "run_e2e.py"
    cmd = [sys.executable, str(PROJECT_ROOT / script)]

    try:
        subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {
            "status": "success",
            "message": f"Pipeline started successfully via {script}.",
        }
    except Exception as e:
        logger.error("Failed to spawn run subprocess: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to start analysis run: {e}"
        ) from e


@app.get("/")
def serve_index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/styles.css")
def serve_styles() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")


@app.get("/app.js")
def serve_app() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")


@app.get("/analytics")
def serve_analytics() -> FileResponse:
    """Serve the standalone Recharts analytics dashboard page."""
    return FileResponse(FRONTEND_DIR / "analytics.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)
