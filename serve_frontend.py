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

# ── Setup Logging ────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
DB_PATH = PROJECT_ROOT / "startup_copilot.db"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Startup Copilot AI Dashboard API",
    description="Backend API serving premium frontend dashboard and SQLite metrics.",
    version="2.0.0",
)

# Enable CORS for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Request Models ──────────────────────────────────────────────────
class StartupInput(BaseModel):
    name: str
    industry: str
    description: str
    estimated_pricing: str
    target_customer: str
    funding_stage: str


# ── API Endpoints ─────────────────────────────────────────────────────────────


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
    if not OUTPUTS_DIR.exists():
        return []
    files = []
    for f in OUTPUTS_DIR.iterdir():
        if f.is_file() and f.suffix in (".md", ".pdf"):
            files.append(f.name)
    return sorted(files)


@app.get("/api/reports/{filename}")
def get_report_file(filename: str) -> FileResponse:
    """Serve a Markdown or PDF report from outputs/ directory safely."""
    safe_path = (OUTPUTS_DIR / Path(filename).name).resolve()
    if not safe_path.exists() or not str(safe_path).startswith(
        str(OUTPUTS_DIR.resolve())
    ):
        raise HTTPException(status_code=404, detail="File not found.")

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

    # We trigger the run via run_e2e_mock.py or run_e2e.py subprocess
    script = "run_e2e_mock.py" if mode == "mock" else "run_e2e.py"
    cmd = [sys.executable, str(PROJECT_ROOT / script)]

    try:
        # Run process asynchronously in the background so API stays fully responsive
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


# ── Static Frontend Routing ──────────────────────────────────────────────────


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

    # Start on port 8080 by default
    uvicorn.run(app, host="127.0.0.1", port=8080)
