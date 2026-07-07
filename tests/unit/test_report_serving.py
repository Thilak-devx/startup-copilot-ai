import sqlite3
import uuid
from pathlib import Path

import serve_frontend


def _workspace_test_dir() -> Path:
    test_dir = Path("artifacts") / "report_serving_tests" / uuid.uuid4().hex
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


def _create_runs_db(db_path: Path, report_markdown: str) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            startup_name TEXT,
            startup_score INTEGER,
            investment_readiness_score INTEGER,
            overall_confidence_score INTEGER,
            recommendation TEXT,
            executive_summary TEXT,
            startup_health TEXT,
            recommended_next_action TEXT,
            overall_confidence INTEGER,
            report_markdown TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT INTO runs (
            session_id, startup_name, startup_score, investment_readiness_score,
            overall_confidence_score, recommendation, executive_summary,
            startup_health, recommended_next_action, overall_confidence,
            report_markdown
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "test-session",
            "Solarex",
            81,
            76,
            79,
            "Conditional Invest",
            "Solarex has strong fundamentals.",
            "Healthy early traction.",
            "Validate CAC.",
            79,
            report_markdown,
        ),
    )
    conn.commit()
    conn.close()


def test_markdown_report_is_hydrated_from_completed_run(monkeypatch) -> None:
    test_dir = _workspace_test_dir()
    db_path = test_dir / "startup_copilot.db"
    outputs_dir = test_dir / "outputs"
    report_markdown = "# Startup Founder Package: Solarex\n\n## Executive Summary\n\nReady."
    _create_runs_db(db_path, report_markdown)

    monkeypatch.setattr(serve_frontend, "DB_PATH", db_path)
    monkeypatch.setattr(serve_frontend, "OUTPUTS_DIR", outputs_dir)

    response = serve_frontend.get_report_file("solarex_report.md")

    hydrated_path = Path(response.path)
    assert hydrated_path.exists()
    assert hydrated_path.read_text(encoding="utf-8") == report_markdown


def test_pdf_report_is_generated_from_hydrated_markdown(monkeypatch) -> None:
    test_dir = _workspace_test_dir()
    db_path = test_dir / "startup_copilot.db"
    outputs_dir = test_dir / "outputs"
    _create_runs_db(
        db_path,
        "# Startup Founder Package: Solarex\n\n| Metric | Score |\n|---|---|\n| Startup Score | 81/100 |",
    )

    monkeypatch.setattr(serve_frontend, "DB_PATH", db_path)
    monkeypatch.setattr(serve_frontend, "OUTPUTS_DIR", outputs_dir)

    response = serve_frontend.get_report_file("solarex_report.pdf")

    pdf_path = Path(response.path)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
    assert pdf_path.with_suffix(".md").exists()


def test_report_list_includes_completed_runs_without_output_files(monkeypatch) -> None:
    test_dir = _workspace_test_dir()
    db_path = test_dir / "startup_copilot.db"
    _create_runs_db(db_path, "# Startup Founder Package: Solarex")

    monkeypatch.setattr(serve_frontend, "DB_PATH", db_path)
    monkeypatch.setattr(serve_frontend, "OUTPUTS_DIR", test_dir / "missing-outputs")

    assert serve_frontend.list_reports() == [
        "solarex_report.md",
        "solarex_report.pdf",
    ]
