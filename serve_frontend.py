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
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.resolve()
DB_PATH = Path(os.environ.get("STARTUP_COPILOT_DB", PROJECT_ROOT / "startup_copilot.db"))
OUTPUTS_DIR = Path(
    os.environ.get("STARTUP_COPILOT_OUTPUTS_DIR", PROJECT_ROOT / "outputs")
)
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


class StartupInput(BaseModel):
    name: str
    industry: str
    description: str
    estimated_pricing: str
    target_customer: str
    funding_stage: str


def _normalise_report_slug(value: str) -> str:
    return re.sub(r"[\s_-]+", "_", value.strip().lower()).strip("_")


def _startup_slug_from_report_filename(filename: str) -> str:
    stem = Path(filename).stem
    if stem.endswith("_report"):
        stem = stem[: -len("_report")]
    return _normalise_report_slug(stem)


def _report_filename_for_startup(startup_name: str, suffix: str) -> str:
    return f"{startup_name.lower().replace(' ', '_')}_report{suffix}"


def _safe_report_path(filename: str) -> Path:
    safe_name = Path(filename).name
    safe_path = (OUTPUTS_DIR / safe_name).resolve()
    outputs_root = OUTPUTS_DIR.resolve()
    if safe_path.suffix not in {".md", ".pdf"} or not str(safe_path).startswith(
        str(outputs_root)
    ):
        raise HTTPException(status_code=404, detail="File not found.")
    return safe_path


def _runs_table_columns(conn: sqlite3.Connection) -> set[str]:
    try:
        return {row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
    except sqlite3.Error:
        return set()


def _row_value(row: sqlite3.Row, key: str, default: Any = "") -> Any:
    return row[key] if key in row.keys() and row[key] is not None else default


def _gate_log(conn: sqlite3.Connection, session_id: str, gate_names: tuple[str, ...]) -> str:
    if not session_id:
        return ""
    placeholders = ",".join("?" for _ in gate_names)
    try:
        row = conn.execute(
            f"""
            SELECT log_json FROM orchestrator_logs
            WHERE session_id = ? AND gate IN ({placeholders})
            ORDER BY id DESC LIMIT 1
            """,
            (session_id, *gate_names),
        ).fetchone()
    except sqlite3.Error:
        return ""
    return row["log_json"] if row and row["log_json"] else ""


def _fallback_markdown_from_run(conn: sqlite3.Connection, row: sqlite3.Row) -> str:
    startup_name = _row_value(row, "startup_name", "Unknown Startup")
    startup_score = _row_value(row, "startup_score", 0)
    investment_score = _row_value(row, "investment_readiness_score", 0)
    overall_confidence = _row_value(
        row,
        "overall_confidence",
        _row_value(row, "overall_confidence_score", 0),
    )
    recommendation = _row_value(row, "recommendation", "Unknown")
    executive_summary = _row_value(row, "executive_summary")
    startup_health = _row_value(row, "startup_health", executive_summary)
    recommended_next_action = _row_value(
        row, "recommended_next_action", recommendation
    )
    session_id = _row_value(row, "session_id")

    lines = [
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
        executive_summary,
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
        f"| Investment Readiness | {investment_score}/100 |",
        f"| Overall Confidence | {overall_confidence}/100 |",
        "",
    ]

    gate3_log = _gate_log(conn, session_id, ("gate3", "phase3"))
    gate4_log = _gate_log(conn, session_id, ("gate4", "phase4"))
    if gate3_log or gate4_log:
        lines += ["## Orchestrator Decision Log", ""]
        if gate3_log:
            lines += [f"### Gate 3 (Pre-HITL)\n```json\n{gate3_log}\n```", ""]
        if gate4_log:
            lines += [f"### Gate 4 (Pre-Security)\n```json\n{gate4_log}\n```", ""]

    return "\n".join(str(line) for line in lines)


def _find_run_for_report(filename: str) -> tuple[sqlite3.Connection, sqlite3.Row] | None:
    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        target_slug = _startup_slug_from_report_filename(filename)
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
        for row in rows:
            startup_name = _row_value(row, "startup_name")
            if _normalise_report_slug(startup_name) == target_slug:
                return conn, row
    except sqlite3.Error:
        conn.close()
        raise

    conn.close()
    return None


def _markdown_for_report(filename: str) -> str | None:
    found = _find_run_for_report(filename)
    if not found:
        return None

    conn, row = found
    try:
        columns = _runs_table_columns(conn)
        if "report_markdown" in columns:
            report_markdown = _row_value(row, "report_markdown")
            if report_markdown:
                return str(report_markdown)
        return _fallback_markdown_from_run(conn, row)
    finally:
        conn.close()


def _hydrate_markdown_file(filename: str, target_path: Path) -> bool:
    markdown = _markdown_for_report(filename)
    if not markdown:
        return False
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    target_path.write_text(markdown, encoding="utf-8")
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
        rows = conn.execute("SELECT startup_name FROM runs ORDER BY id DESC").fetchall()
        conn.close()
    except sqlite3.Error:
        return set()

    filenames: set[str] = set()
    for row in rows:
        startup_name = _row_value(row, "startup_name")
        if startup_name:
            filenames.add(_report_filename_for_startup(startup_name, ".md"))
            filenames.add(_report_filename_for_startup(startup_name, ".pdf"))
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
