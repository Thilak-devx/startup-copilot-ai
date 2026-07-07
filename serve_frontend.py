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
